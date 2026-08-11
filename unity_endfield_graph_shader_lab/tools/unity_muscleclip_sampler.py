#!/usr/bin/env python3
"""Decode Unity streamed/dense/constant AnimationClip data into qvvf-like samples.

Endfield uses two independent transform-animation storage paths.  ACL clips are
handled by the repository's ACL sampler.  This file handles the stock Unity
``m_MuscleClip.m_Clip`` path used by a smaller set of character clips:

* ``m_StreamedClip`` stores sparse cubic polynomial segments.
* ``m_DenseClip`` stores frame-major scalar samples.
* ``m_ConstantClip`` stores one value per remaining scalar curve.

Unity's generic bindings describe *vector curves*, while the three storage
ranges address scalar components.  Transform position/scale/euler bindings
therefore consume three scalar indices and quaternion bindings consume four.
The ranges are concatenated in streamed, dense, constant order.

The emitted frame shape matches the qvvf JSON consumed by the character lab.
Animator muscle/root curves are decoded as scalar evidence but are deliberately
not baked into transform tracks by this generic sampler. The exact
muscle-to-Avatar-local GetZYRoll stage, TwistSolve redistribution, hierarchy
propagation, compact-to-physical TRS copy, and later component-wise generic
overlay are recovered. Source-derived semantic pose baking is therefore
reproducible, but it is not an observed retail-f5 numeric runtime oracle. The
clip's runtime root-motion policy remains separate.
"""

from __future__ import annotations

import argparse
import base64
import bisect
import json
import math
import struct
import sys
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_DIMENSIONS = {1: 3, 2: 4, 3: 3, 4: 3}
TRANSFORM_CHANNELS = {1: "translation", 2: "rotation", 3: "scale", 4: "euler"}
COMPONENT_NAMES = ("x", "y", "z", "w")
GAME_OBJECT_ACTIVE_ATTRIBUTE = 2086281974  # Unity CRC32("m_IsActive")

# Endfield's source-modified Unity runtime extends the stock humanoid ABI from
# 95 muscle slots to 101.  The six additions are inserted into the two leg
# ranges rather than appended to the table.  The names and ordering below come
# directly from the installed UnityPlayer.dll muscle-name table.  We expose the
# recovered semantics, exact Avatar selector records, native FromAxes
# quaternion construction, TwistSolve's ordered human-local correction, and
# the downstream physical/component write order. Production-equivalence claims
# remain blocked on an observed retail-f5 numeric output fixture.
HUMANOID_MUSCLE_ATTRIBUTE_START = 42
UNITY_HUMANOID_MUSCLE_COUNT = 95
ENDFIELD_HUMANOID_MUSCLE_COUNT = 101
ENDFIELD_EXTENSION_MUSCLE_NAMES = {
    28: "Left Foot Twist Roll",
    30: "Left Toes Left-Right",
    31: "Left Toes Twist Roll",
    39: "Right Foot Twist Roll",
    41: "Right Toes Left-Right",
    42: "Right Toes Twist Roll",
}
ENDFIELD_EXTENSION_MUSCLE_BINDINGS = {
    28: {
        "human_bone": "LeftFoot",
        "human_bone_index": 5,
        "selector": 0,
        "default_min_radians": -math.radians(20.0),
        "default_max_radians": math.radians(20.0),
    },
    30: {
        "human_bone": "LeftToes",
        "human_bone_index": 20,
        "selector": 1,
        "default_min_radians": -math.radians(50.0),
        "default_max_radians": math.radians(50.0),
    },
    31: {
        "human_bone": "LeftToes",
        "human_bone_index": 20,
        "selector": 0,
        "default_min_radians": -math.radians(40.0),
        "default_max_radians": math.radians(40.0),
    },
    39: {
        "human_bone": "RightFoot",
        "human_bone_index": 6,
        "selector": 0,
        "default_min_radians": -math.radians(20.0),
        "default_max_radians": math.radians(20.0),
    },
    41: {
        "human_bone": "RightToes",
        "human_bone_index": 21,
        "selector": 1,
        "default_min_radians": -math.radians(50.0),
        "default_max_radians": math.radians(50.0),
    },
    42: {
        "human_bone": "RightToes",
        "human_bone_index": 21,
        "selector": 0,
        "default_min_radians": -math.radians(40.0),
        "default_max_radians": math.radians(40.0),
    },
}
# Installed f5 ``UnityPlayer.dll`` RVA 0x1DDE010.  Each row is indexed by
# HumanBodyBones 0..24 and stored in selector order 2, 1, 0.  A -1 lane is an
# absent degree of freedom.  The table contains every one of the 61 non-finger
# body muscles exactly once; the two 20-value hand blocks are gathered by the
# separate RVA 0xB25300 path below.
ENDFIELD_BODY_BONE_AXIS_TO_MUSCLE = (
    (-1, -1, -1),
    (21, 22, 23),
    (32, 33, 34),
    (24, -1, 25),
    (35, -1, 36),
    (26, 27, 28),
    (37, 38, 39),
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (9, 10, 11),
    (12, 13, 14),
    (43, 44, -1),
    (52, 53, -1),
    (45, 46, 47),
    (54, 55, 56),
    (48, -1, 49),
    (57, -1, 58),
    (50, 51, -1),
    (59, 60, -1),
    (29, 30, 31),
    (40, 41, 42),
    (15, 16, -1),
    (17, 18, -1),
    (19, 20, -1),
)
ENDFIELD_BODY_HUMAN_BONE_BEGIN = 1
ENDFIELD_BODY_HUMAN_BONE_END = 25
ENDFIELD_BODY_MUSCLE_COUNT = 61
ENDFIELD_FINGER_COUNT = 5
ENDFIELD_FINGER_MUSCLES_PER_FINGER = 4
ENDFIELD_FINGER_PHALANGES = 3
ENDFIELD_TWIST_SOLVE_PAIRS = (
    {
        "parent": "LeftLowerArm",
        "parent_human_bone_index": 16,
        "child": "LeftHand",
        "child_human_bone_index": 18,
        "factor": "m_ForeArmTwist",
        "factor_offset": "AvatarHuman+0x120",
    },
    {
        "parent": "LeftUpperArm",
        "parent_human_bone_index": 14,
        "child": "LeftLowerArm",
        "child_human_bone_index": 16,
        "factor": "m_ArmTwist",
        "factor_offset": "AvatarHuman+0x11C",
    },
    {
        "parent": "RightLowerArm",
        "parent_human_bone_index": 17,
        "child": "RightHand",
        "child_human_bone_index": 19,
        "factor": "m_ForeArmTwist",
        "factor_offset": "AvatarHuman+0x120",
    },
    {
        "parent": "RightUpperArm",
        "parent_human_bone_index": 15,
        "child": "RightLowerArm",
        "child_human_bone_index": 17,
        "factor": "m_ArmTwist",
        "factor_offset": "AvatarHuman+0x11C",
    },
    {
        "parent": "LeftLowerLeg",
        "parent_human_bone_index": 3,
        "child": "LeftFoot",
        "child_human_bone_index": 5,
        "factor": "m_LegTwist",
        "factor_offset": "AvatarHuman+0x128",
    },
    {
        "parent": "LeftUpperLeg",
        "parent_human_bone_index": 1,
        "child": "LeftLowerLeg",
        "child_human_bone_index": 3,
        "factor": "m_UpperLegTwist",
        "factor_offset": "AvatarHuman+0x124",
    },
    {
        "parent": "RightLowerLeg",
        "parent_human_bone_index": 4,
        "child": "RightFoot",
        "child_human_bone_index": 6,
        "factor": "m_LegTwist",
        "factor_offset": "AvatarHuman+0x128",
    },
    {
        "parent": "RightUpperLeg",
        "parent_human_bone_index": 2,
        "child": "RightLowerLeg",
        "child_human_bone_index": 4,
        "factor": "m_UpperLegTwist",
        "factor_offset": "AvatarHuman+0x124",
    },
)
ENDFIELD_EXTENSION_MUSCLE_SLOTS = tuple(ENDFIELD_EXTENSION_MUSCLE_NAMES)
ENDFIELD_HUMANOID_ATTRIBUTE_END = (
    HUMANOID_MUSCLE_ATTRIBUTE_START + ENDFIELD_HUMANOID_MUSCLE_COUNT
)
ENDFIELD_HUMANOID_INDEX_ARRAY_COUNT = 206
NATIVE_ZYROLL_PI = 3.1415927410125732
NATIVE_ZYROLL_TWO_PI = 6.2831854820251465
NATIVE_ZYROLL_HALF_ANGLE_LIMIT = 1.5707954168319702
ENDFIELD_HUMANOID_NATIVE_EVIDENCE = {
    "unityplayer_sha256": "B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2",
    "muscle_count_rva": "0x153340",
    "public_2021_3_34f1_baseline": {
        "version": "2021.3.34f1",
        "changeset": "25266724e7bd",
        "unityplayer_sha256": (
            "F64218029F1B56FB67128BBC270C693EDEC402F2359583B8B456DF83172442C9"
        ),
        "human_trait_muscle_count": 95,
        "human_trait_bone_count": 55,
        "extension_names_present": 0,
        "muscle_count_rva": "0x12CFD0",
        "direct_muscle_to_bone_table_rva": "0x17E70C0",
        "body_bone_axis_to_muscle_table_rva": "0x17E6D90",
        "endfield_direct_muscle_to_bone_table_rva": "0x1DDE340",
        "endfield_body_bone_axis_to_muscle_table_rva": "0x1DDE010",
        "relationship": (
            "exact_stock_tables_after_removing_endfield_slots_28_30_31_39_41_42_"
            "and_clearing_their_six_selector_holes"
        ),
        "physical_transform_output_oracle": False,
        "synthetic_numeric_fixture": {
            "path": "scratch/unity_2021_3_34f1_oracle/evidence/stock_pose_probe.json",
            "sha256": "AB302D1A63C0B224C62513033EAA660DED467170A806E0D66A448E3E6FE18442",
            "human_bones": 23,
            "mapped_direct_muscles": 49,
            "omitted_eye_jaw_finger_muscles": 46,
            "max_set_get_roundtrip_error": 0.0011557042598724365,
            "max_quaternion_norm_error": 4.1019507235340313e-07,
            "force_text_avatar_path": (
                "scratch/unity_2021_3_34f1_oracle/Assets/SyntheticStockAvatar.asset"
            ),
            "force_text_avatar_sha256": (
                "52324FEBD7E6BE12F2FC13FE943A79D1B493989CF42563992A6CC8AFA5D28430"
            ),
            "ruri_compared_body_bones": 21,
            "ruri_max_angular_error_degrees": 3.423621675895667e-05,
            "scope": "public_stock_numeric_validation_not_endfield_f5_output",
        },
    },
    "internal_get_zyroll_thunk_rva": "0x14C020",
    "internal_get_zyroll_core_rva": "0xA795C0",
    "production_axes_converter": {
        "status": "instruction_level_semantic_counterpart_proven_no_f5_equation_delta",
        "endfield_inner_range": "0xB34260..0xB34908",
        "endfield_inner_sha256": (
            "C8976822F3AD5933B9A97F3F546C02597A0FBEA72104C99F6F643AB2FEC48D1C"
        ),
        "public_inner_range": "0x95B8B0..0x95C12C",
        "public_inner_sha256": (
            "95067AEC0C95BD326C6813FF1DB421D1C82EEF03BEC7812966006DDE9DDB91C5"
        ),
        "dispatch_field": "AxesInfo+0x54",
        "dispatch_cases": [1, 2, 4, "default"],
        "humanoid_zyroll_case": 1,
        "endfield_tangent_helper_rva": "0xA7B990",
        "public_tangent_helper_rva": "0x90D3E0",
        "endfield_avatar_sandwich": "inlined_at_0xB347E5",
        "public_avatar_sandwich": "leaf_0x908540",
        "difference_class": (
            "compiler_inlining_register_allocation_spills_and_pdata_partitioning"
        ),
        "proof_artifact": (
            "scratch/character_recovery/humanoid_2021_baseline/"
            "axes_converter_semantic_proof.json"
        ),
    },
    "from_axes_formula": (
        "normalize(tx,ty+tx*tz,tz-tx*ty,1); tx_y_z=tan(selector_angle/2)"
    ),
    "absolute_local_formula": "preQ*FromAxes_ZYRoll(selector_angles)*inverse(postQ)",
    "angle_to_avatar_local_helper": (
        "unity_muscleclip_sampler.avatar_local_rotation_from_selector_angles"
    ),
    "muscle_input_scaling_status": (
        "no_clamp_in_get_zyroll_setinternal_staging_or_b25910_conversion"
    ),
    "angle_range_reduction_status": (
        "recovered_mod_2pi_then_half_angle_clamp_1_5707954168"
    ),
    "tangent_status": "semantic_math_tan_native_rational_minimax_not_bit_exact",
    "human_pose_to_skeleton_core_rva": "0xB314D0",
    "human_pose_to_skeleton_core_status": (
        "shared_core_proven_from_set_internal_human_pose_and_three_native_callers"
    ),
    "human_pose_to_skeleton_call_sites": [
        "0xA20FD3",
        "0xA5B115",
        "0xAAB7BE",
        "0xB13713",
    ],
    "human_pose_to_skeleton_caller_roles": {
        "0xA20FD3": "HumanPoseHandler.SetInternalHumanPose",
        "0xA5B115": "AnimationClip.SampleAnimation_worker_0xA5AD60",
        "0xAAB7BE": "AnimationStream_lazy_pose_materialization_0xAAB6E0",
        "0xB13713": "shared_humanoid_pose_apply_reset_stage_0xB13620",
    },
    "normal_animator_update_consumer_status": (
        "scheduled_pose_materialization_through_0xB314D0_and_post_stage_"
        "twist_solve_closed"
    ),
    "normal_animator_update_chain": [
        "0x177AB0_Animator.Update_thunk",
        "0xA68080_core",
        "0xA64610_scheduler",
        "0xA5AD10_scheduled_callback",
        "0xA5AC30_adapter",
        "0xB13620_humanoid_apply_reset",
        "0xB314D0_pose_to_skeleton",
        "0xB17DB0_per_side_foot_goal_rebuild_conditional_fixture_skipped",
        "0xA56280_post_conversion_callback",
        "0xB132D0_to_0xB13240",
        "0xB323F0_twist_solve",
    ],
    "normal_animator_update_gates": [
        "Animator+0x24A_nonzero",
        "qword_Animator+0x260_nonzero",
        "Animator+0x713_zero",
    ],
    "normal_animator_update_job_record_stride": "0x98",
    "normal_animator_grouped_apply_chain": [
        "0xA69700_grouped_callback",
        "0xA69BC0_worker",
        "0xB13620_humanoid_apply_reset",
        "0xB314D0_pose_to_skeleton",
        "0xB17DB0_left_and_right_foot_goal_rebuild_conditional_fixture_skipped",
        "0xB13240_post_apply",
        "0xB323F0_twist_solve",
    ],
    "sample_animation_worker_boundary": (
        "0xA5AD60_is_AnimationClip.SampleAnimation_only_not_normal_update"
    ),
    "human_pose_input_staging": "61_body_plus_20_left_finger_plus_20_right_finger",
    "translation_dof_helper_rva": "0xB31D10",
    "translation_dof_helper_status": (
        "21_non_hips_core_bones_position_only_proven_not_twist_solve"
    ),
    "translation_dof_runtime_gate_offset": "Avatar+0x13A",
    "translation_dof_playable_avatar_audit": {
        "postmodel_animators": 34,
        "unique_avatars": 33,
        "enabled_avatars": 0,
    },
    "muscle_production_chain": {
        "body_bone_loop_rva": "0xB25830",
        "per_bone_reader_rva": "0xB25910",
        "finger_reader_rva": "0xB25300",
        "human_dof_table_rva": "0x1DDE010",
        "human_dof_table_sha256": (
            "B9A06EAC7CBB3D4BFB9A54EB388F62A86D85FA7F61703D76575F37453E455CF3"
        ),
        "get_zyroll_bridge": "0xB38B10_to_0xB34260",
        "extension_table_rows": {
            "LeftFoot": [26, 27, 28],
            "RightFoot": [37, 38, 39],
            "LeftToes": [29, 30, 31],
            "RightToes": [40, 41, 42],
        },
        "table_triplet_storage_order": ["selector2", "selector1", "selector0"],
        "converter_gather_order": ["selector0", "selector1", "selector2"],
        "body_loop_range": [1, 25],
        "body_missing_lane_value": 0.0,
        "body_mapping_skip_condition": "compact_bone_index_equals_minus_one",
        "finger_split": (
            "five_fingers_times_four_muscles_to_three_phalanges_per_hand"
        ),
        "finger_selector_lanes": [
            [0, "spread", "phalanx1_stretched"],
            [0, 0, "phalanx2_stretched"],
            [0, 0, "phalanx3_stretched"],
        ],
        "finger_mapping_skip_condition": "compact_bone_index_is_negative",
        "maintained_gather_helpers": [
            "gather_endfield_body_selector_muscles",
            "iter_endfield_body_muscle_gather",
            "gather_endfield_finger_selector_muscles",
            "iter_endfield_finger_muscle_gather",
        ],
        "input": "raw_pose_floats_at_pose_plus_0x2F0",
        "clamp": "none_in_recovered_production_chain",
    },
    "twist_solve_rva": "0xB323F0",
    "human_fix_twist_rva": "0xB27930",
    "twist_solve_call_sites": {
        "0xA20FF0": "SetInternalHumanPose_after_0xB314D0",
        "0xB132A5": (
            "shared_post_conversion_0xB13240_reached_after_0xB314D0_"
            "by_normal_Animator.Update"
        ),
    },
    "twist_solve_pairs": [dict(item) for item in ENDFIELD_TWIST_SOLVE_PAIRS],
    "twist_solve_semantics": (
        "scale_parent_selector0_reconstruct_parent_then_compensate_child_"
        "to_preserve_child_world_orientation_in_order"
    ),
    "twist_solve_write_boundary": (
        "mapped_compact_human_parent_and_child_trs_copied_to_exact_physical_nodes_"
        "named_twist_side_branch_local_tracks_untouched"
    ),
    "twist_solve_physical_mapping": {
        "status": "closed_for_current_playable_avatars",
        "postmodel_animators": 34,
        "unique_avatars": 33,
        "pair_observations": 272,
        "compact_intermediate_nodes": 0,
        "physical_intermediate_nodes": 0,
        "mapping": (
            "HumanBone_to_m_HumanBoneIndex_to_m_HumanSkeletonIndexArray_"
            "to_m_AvatarSkeleton"
        ),
        "physical_copy_chain": "0xB06170_to_0xB33BD0_48_byte_TRS_records",
        "named_twist_bones": (
            "direct_side_branches_preserve_generic_local_curves_and_inherit_parent_delta"
        ),
        "semantic_bake_formula": (
            "delta=inverse(parentBefore)*parentAfter;"
            "childAfter=inverse(delta)*childBefore"
        ),
    },
    "post_conversion_pose_bake": {
        "status": "instruction_and_pinned_native_numeric_oracle_closed",
        "post_stage_range": "0xB13240..0xB132D0",
        "post_stage_order": [
            "0xB33B50_compact_pose_copy",
            "0xB323F0_eight_pair_twist_solve",
            "0xB06170_to_0xB33BD0_compact_to_physical_TRS_copy",
        ],
        "physical_record_stride_bytes": 48,
        "physical_record_components": ["translation", "rotation", "scale"],
        "generic_component_overlay": {
            "retail_rva": "0xB06330",
            "public_2021_3_34f1_rva": "0x9327D0",
            "semantics": (
                "start_from_base_physical_TRS_then_replace_only_mapped_"
                "translation_rotation_or_scale_components"
            ),
            "scheduler_order": [
                "0xA56280_to_0xB132D0_to_0xB13240_humanoid_job",
                "0xA6562C_complete_humanoid_job",
                "0xA69700_to_0xA69BC0_to_0xA4CE30_to_0xB06330_generic_overlay",
            ],
            "general_precedence": "generic_mapped_component_overrides_humanoid_base",
            "wulfa_fixture_authored_attributes": [1, 2],
            "wulfa_fixture_components": ["translation", "rotation"],
            "wulfa_fixture_scale_policy": "preserve_serialized_base_scale",
            "wulfa_fixture_destination_overlap": 0,
        },
        "proof_artifacts": [
            (
                "scratch/character_recovery/humanoid_2021_baseline/"
                "f5_pose_bake_semantic_proof.json"
            ),
            (
                "scratch/character_recovery/humanoid_2021_baseline/"
                "F5_POSE_BAKE_SEMANTIC_PROOF.md"
            ),
        ],
        "source_derived_world_pose_sha256": (
            "006FEBF370BA7F4201F6D66F4FDF7FBD737939800F26F02A69DF8903EE227B8A"
        ),
        "source_derived_not_observed_retail_output": True,
        "original_native_full_pose_oracle": {
            "status": "closed_for_pinned_wulfa_sprint_fixture",
            "frame_count": 33,
            "physical_node_count": 486,
            "record_stride_bytes": 48,
            "raw_size": 769824,
            "raw_sha256": (
                "3276498D97C516E83D1C0F7094754C9D7E2F3A5B448EBD8DBAFE01E1615FA115"
            ),
            "isolated_humanoid_rotations_exact": [693, 693],
            "generic_overlay_records_exact": [1914, 1914],
            "untouched_rest_records_exact": [13332, 13332],
            "frame_32_equals_frame_0": True,
            "repeat_runs_identical": True,
            "guard_failures": 0,
            "verifier": (
                "scratch/reverse_engineering/humanoid_101_full_pose_replay/"
                "verify_full_pose_replay.py"
            ),
            "payload": (
                "scratch/reverse_engineering/humanoid_101_full_pose_replay/"
                "full_pose_replay_trs.bin"
            ),
        },
    },
    "playable_twist_factor_audit": {
        "postmodel_animators": 34,
        "unique_avatars": 33,
        "all_exact": True,
        "m_ArmTwist": 1.0,
        "m_ForeArmTwist": 0.0,
        "m_UpperLegTwist": 1.0,
        "m_LegTwist": 0.0,
    },
    "extension_muscle_numeric_fixture": {
        "status": "exact_original_input_and_physical_output_oracle_closed_for_pinned_fixture",
        "current_all_ui_clip_count": 779,
        "current_all_ui_clips_mapping_extensions": 0,
        "broader_original_wulfa_loli_clip_count": 793,
        "broader_clips_mapping_all_six": 337,
        "broader_clips_animating_any_extension": 318,
        "broader_clips_animating_all_six": 76,
        "clip_name": "A_actor_loli_sprint_loop_sp_01",
        "source_chunk": "62EB15DCD74A3348E244B9B068AB9694.chk",
        "path_id": -7522027738202102101,
        "asset_map_hash": "7a75e275fdce6719",
        "source_offset": 177244052,
        "sample_count": 33,
        "sample_rate": 60.0,
        "duration": 0.533333361,
        "animated_extension_slots": [28, 30, 31, 39, 41, 42],
        "avatar": "SK_actor_wulfa_01Avatar",
        "fixture": (
            "scratch/character_recovery/humanoid_avatar_basis/"
            "extension_muscle_fixture_loli_sprint_loop_sp_01.json"
        ),
        "controller_state": {
            "controller": "AC_chr_0028_wulfa_optNew",
            "state": "Base Layer.Locomotion.Grounded.Move.SprintSP",
            "single_blend_node": True,
            "write_default_values": True,
            "speed": 1.0,
            "cycle_offset": 0.0,
            "mirror": False,
            "loop": True,
            "state_ik_on_feet": False,
            "layer_ik_pass": False,
            "layer_disable_root_motion_pass": False,
            "controller_layer_count": 9,
            "controller_state_count": 188,
            "all_layers_ik_pass_false": True,
            "all_states_ik_on_feet_false": True,
        },
        "materialization_policy": (
            "base_rest_pose_then_101_muscles_and_separate_Motion_Root_"
            "plus_nine_generic_IK_QVV_tracks_then_compact_conversion_"
            "TwistSolve_and_compact_to_physical_mapping"
        ),
        "physical_output_oracle": {
            "status": "original_2021_3_34f5_native_QTS_fixture_recovered",
            "do_not_substitute_unity_2022_lab_output": True,
            "frame_count": 33,
            "physical_node_count": 486,
            "raw_size": 769824,
            "raw_sha256": (
                "3276498D97C516E83D1C0F7094754C9D7E2F3A5B448EBD8DBAFE01E1615FA115"
            ),
            "frame_32_equals_frame_0": True,
            "guard_failures": 0,
        },
    },
    "post_apply_0xB17DB0_status": (
        "per_side_foot_goal_ik_rebuild_not_twist_solve_"
        "wulfa_SprintSP_controller_and_optimized_job_path_skip"
    ),
    "twist_solve_status": (
        "native_eight_pair_human_local_redistribution_recovered_"
        "physical_node_ownership_propagation_and_component_overlay_order_closed_"
        "numeric_original_full_frame_fixture_closed_for_pinned_wulfa_sprint"
    ),
}
ENDFIELD_ROOT_MOTION_RUNTIME_POLICY = {
    "motion_root_semantics": (
        "MotionT_Q_are_object_trajectory_RootT_Q_are_absolute_skeleton_body_reference"
    ),
    "character_info": {
        "rotation_proven": True,
        "translation_proven_absent": True,
        "formula": "worldQ=normalize(worldQ*animator.deltaRotation)",
        "single_clip_fallback": (
            "deltaQ=normalize(inverse(continuity(MotionQ_prev))*continuity(MotionQ_cur))"
        ),
        "loop_wrap_policy": "reset_without_synthesized_wrap_delta",
    },
    "gameplay": {
        "gameobject_application_proven": False,
        "animator_apply_root_motion_default": False,
        "translation_warp_formula": (
            "AngleAxis(rotationOnVelocityDegrees,worldUp)*rawDeltaPosition"
        ),
        "angular_velocity_formula": "rawAngularVelocity*angularVelocityScale",
        "consumer_path": (
            "Animator_deltas_to_RootMotionData_to_VelocityMixer_to_movement_motor"
        ),
        "pipeline_divisor_formula": (
            "(config_flag_at_0x18?1:config_sub_0x28_field_0x44)*"
            "config_field_0x20"
        ),
        "pipeline_divisor_epsilon": 0.0001,
        "animator_move_accumulation_weight_gate": 0.00001,
        "has_root_motion_accessor_weight_gate": 0.0001,
        "weight_gate_status": "distinct_native_thresholds_do_not_merge",
    },
    "sample_count_policy": "preserve_decoded_counts_never_synthesize_terminal_sample",
}


class DecodeError(ValueError):
    """Raised when serialized clip ranges are internally inconsistent."""


@dataclass(frozen=True)
class ScalarBinding:
    scalar_index: int
    binding_index: int
    component: int
    dimension: int
    path_crc: int
    attribute: int
    type_id: str
    custom_type: int
    is_pptr_curve: bool
    version: tuple[int, ...]


@dataclass(frozen=True)
class StreamKey:
    time: float
    index: int
    coeff: tuple[float, float, float, float]

    @property
    def value(self) -> float:
        return self.coeff[3]


@dataclass(frozen=True)
class StreamFrame:
    time: float
    keys: tuple[StreamKey, ...]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unity_crc32(path: str) -> int:
    try:
        payload = path.encode("ascii")
    except UnicodeEncodeError:
        payload = path.encode("utf-8")
    return zlib.crc32(payload) & 0xFFFFFFFF


def ref_path_id(value: dict[str, Any] | None) -> int:
    return int((value or {}).get("m_PathID") or 0)


def vector(value: dict[str, Any] | None, default: Sequence[float]) -> list[float]:
    value = value or {}
    return [float(value.get(axis, default[index])) for index, axis in enumerate(("X", "Y", "Z", "W")[: len(default)])]


def load_hierarchy(hierarchy_dir: Path, root_name: str) -> list[dict[str, Any]]:
    """Load the recovered postmodel hierarchy in transform traversal order."""

    by_transform_id: dict[int, dict[str, Any]] = {}
    game_object_dir = hierarchy_dir / "GameObject"
    for path in sorted(game_object_dir.glob("*.json")):
        data = load_json(path)
        components = data.get("m_Components") or []
        if not components:
            continue
        by_transform_id[ref_path_id(components[0])] = data

    root_id = next((tid for tid, data in by_transform_id.items() if data.get("m_Name") == root_name), None)
    if root_id is None:
        raise DecodeError(f"missing hierarchy root {root_name!r} under {game_object_dir}")

    result: list[dict[str, Any]] = []
    visiting: set[int] = set()

    def visit(transform_id: int, parent_path: str) -> None:
        if transform_id in visiting:
            raise DecodeError(f"cycle in hierarchy at transform {transform_id}")
        data = by_transform_id.get(transform_id)
        if data is None:
            return
        visiting.add(transform_id)
        name = str(data.get("m_Name") or "")
        path = name if not parent_path else f"{parent_path}/{name}"
        transform = data.get("m_Transform") or {}
        result.append(
            {
                "name": name,
                "path": path,
                "path_crc": unity_crc32(path),
                "local_pos": vector(transform.get("m_LocalPosition"), (0.0, 0.0, 0.0)),
                "local_rot": vector(transform.get("m_LocalRotation"), (0.0, 0.0, 0.0, 1.0)),
                "local_scale": vector(transform.get("m_LocalScale"), (1.0, 1.0, 1.0)),
            }
        )
        for child in transform.get("m_Children") or []:
            visit(ref_path_id(child), path)
        visiting.remove(transform_id)

    # Unity animation paths are relative to the Animator root, so the root
    # GameObject itself is omitted just as AnimationUtility.CalculateTransformPath
    # omits it.
    root_transform = by_transform_id[root_id].get("m_Transform") or {}
    for child in root_transform.get("m_Children") or []:
        visit(ref_path_id(child), "")
    return result


def binding_dimension(binding: dict[str, Any]) -> int:
    if str(binding.get("typeID")) != "Transform":
        return 1
    return TRANSFORM_DIMENSIONS.get(int(binding.get("attribute") or 0), 1)


def expand_bindings(bindings: Sequence[dict[str, Any]]) -> list[ScalarBinding]:
    """Expand vector GenericBindings into their serialized scalar index space."""

    result: list[ScalarBinding] = []
    scalar_index = 0
    for binding_index, binding in enumerate(bindings):
        dimension = binding_dimension(binding)
        version = tuple(int(item) for item in (binding.get("version") or []))
        for component in range(dimension):
            result.append(
                ScalarBinding(
                    scalar_index=scalar_index,
                    binding_index=binding_index,
                    component=component,
                    dimension=dimension,
                    path_crc=int(binding.get("path") or 0),
                    attribute=int(binding.get("attribute") or 0),
                    type_id=str(binding.get("typeID") or ""),
                    custom_type=int(binding.get("customType") or 0),
                    is_pptr_curve=bool(binding.get("isPPtrCurve") or False),
                    version=version,
                )
            )
            scalar_index += 1
    return result


def u32_to_float(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", int(value) & 0xFFFFFFFF))[0]


def float_to_u32(value: float) -> int:
    """Test/helper inverse of :func:`u32_to_float`."""

    return struct.unpack("<I", struct.pack("<f", float(value)))[0]


def parse_stream_frames(words: Sequence[int]) -> list[StreamFrame]:
    """Parse Unity's uint-word StreamedClip buffer without losing coefficients."""

    frames: list[StreamFrame] = []
    offset = 0
    while offset < len(words):
        if offset + 2 > len(words):
            raise DecodeError(f"truncated streamed frame header at word {offset}")
        time = u32_to_float(words[offset])
        key_count = int(words[offset + 1])
        offset += 2
        if key_count < 0:
            raise DecodeError(f"negative streamed key count {key_count}")
        required = key_count * 5
        if offset + required > len(words):
            raise DecodeError(
                f"truncated streamed frame at word {offset}: needs {required}, has {len(words) - offset}"
            )
        keys: list[StreamKey] = []
        for _ in range(key_count):
            index = int(words[offset])
            coeff = tuple(u32_to_float(words[offset + component]) for component in range(1, 5))
            keys.append(StreamKey(time=time, index=index, coeff=coeff))
            offset += 5
        frames.append(StreamFrame(time=time, keys=tuple(keys)))
    return frames


def real_stream_frames(frames: Sequence[StreamFrame]) -> list[StreamFrame]:
    """Drop Unity's -FLT_MAX slope seed and +Infinity terminator frames."""

    return [frame for frame in frames if math.isfinite(frame.time) and frame.time > -1.0e30]


def build_stream_curves(frames: Sequence[StreamFrame], curve_count: int) -> tuple[dict[int, list[StreamKey]], list[str]]:
    curves: dict[int, list[StreamKey]] = defaultdict(list)
    warnings: list[str] = []
    for frame in real_stream_frames(frames):
        for key in frame.keys:
            if key.index < 0 or key.index >= curve_count:
                warnings.append(f"stream key index {key.index} outside [0,{curve_count}) at {frame.time}")
                continue
            curves[key.index].append(key)

    for index, keys in list(curves.items()):
        keys.sort(key=lambda item: item.time)
        deduplicated: list[StreamKey] = []
        for key in keys:
            if deduplicated and abs(deduplicated[-1].time - key.time) <= 1.0e-8:
                deduplicated[-1] = key
            else:
                deduplicated.append(key)
        curves[index] = deduplicated
    missing = sorted(set(range(curve_count)) - set(curves))
    if missing:
        warnings.append(f"{len(missing)} streamed scalar curves have no finite key")
    return dict(curves), warnings


def evaluate_stream_curve(keys: Sequence[StreamKey], time: float) -> float:
    if not keys:
        raise DecodeError("cannot evaluate an empty streamed curve")
    if time <= keys[0].time:
        return keys[0].value
    if time >= keys[-1].time:
        return keys[-1].value
    times = [key.time for key in keys]
    index = bisect.bisect_right(times, time) - 1
    key = keys[max(0, index)]
    dt = max(0.0, time - key.time)
    a, b, c, d = key.coeff
    # Unity encodes a stepped segment with zero cubic/quadratic/slope terms.
    if a == 0.0 and b == 0.0 and c == 0.0:
        return d
    return ((a * dt + b) * dt + c) * dt + d


def evaluate_dense_curve(
    samples: Sequence[float],
    curve_count: int,
    frame_count: int,
    sample_rate: float,
    begin_time: float,
    curve_index: int,
    time: float,
) -> float:
    if curve_count <= 0 or frame_count <= 0 or sample_rate <= 0.0:
        raise DecodeError("invalid dense curve dimensions")
    expected = curve_count * frame_count
    if len(samples) < expected:
        raise DecodeError(f"dense sample array has {len(samples)} values; expected {expected}")
    frame = (time - begin_time) * sample_rate
    if frame <= 0.0:
        return float(samples[curve_index])
    if frame >= frame_count - 1:
        return float(samples[(frame_count - 1) * curve_count + curve_index])
    left = int(math.floor(frame))
    alpha = frame - left
    first = float(samples[left * curve_count + curve_index])
    second = float(samples[(left + 1) * curve_count + curve_index])
    return first + (second - first) * alpha


def normalize_quaternion(value: Sequence[float]) -> list[float]:
    magnitude = math.sqrt(sum(float(component) ** 2 for component in value))
    if not math.isfinite(magnitude) or magnitude <= 1.0e-12:
        return [0.0, 0.0, 0.0, 1.0]
    return [float(component) / magnitude for component in value]


def multiply_quaternions(left: Sequence[float], right: Sequence[float]) -> list[float]:
    """Hamilton product for Unity's serialized XYZW quaternion order."""

    if len(left) != 4 or len(right) != 4:
        raise DecodeError("quaternion operands must contain four XYZW values")
    lx, ly, lz, lw = (float(component) for component in left)
    rx, ry, rz, rw = (float(component) for component in right)
    return [
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    ]


def inverse_quaternion(value: Sequence[float]) -> list[float]:
    """Return the mathematical inverse of a serialized XYZW quaternion."""

    if len(value) != 4:
        raise DecodeError("quaternion must contain four XYZW values")
    x, y, z, w = (float(component) for component in value)
    squared_magnitude = x * x + y * y + z * z + w * w
    if not math.isfinite(squared_magnitude) or squared_magnitude <= 1.0e-24:
        raise DecodeError("cannot invert a zero or non-finite quaternion")
    reciprocal = 1.0 / squared_magnitude
    return [-x * reciprocal, -y * reciprocal, -z * reciprocal, w * reciprocal]


def gather_endfield_body_selector_muscles(
    body_muscles: Sequence[float],
    human_bone_index: int,
) -> tuple[float, float, float]:
    """Reproduce retail f5 RVA ``0xB25943..0xB259C8``.

    The installed table stores each triplet as selector 2/1/0.  The native
    SIMD shuffle reverses that to converter lanes 0/1/2, substitutes a bitwise
    zero for every ``-1`` table entry, and otherwise forwards the raw muscle
    float unchanged.  In particular, this stage does not clamp authored
    over-range values.
    """

    if not 0 <= int(human_bone_index) < len(ENDFIELD_BODY_BONE_AXIS_TO_MUSCLE):
        raise DecodeError(f"human body-bone index is out of range: {human_bone_index}")
    if len(body_muscles) < ENDFIELD_BODY_MUSCLE_COUNT:
        raise DecodeError(
            f"body-muscle array has {len(body_muscles)} values; "
            f"expected at least {ENDFIELD_BODY_MUSCLE_COUNT}"
        )
    stored_selector2_1_0 = ENDFIELD_BODY_BONE_AXIS_TO_MUSCLE[
        int(human_bone_index)
    ]
    return tuple(
        0.0 if muscle_index < 0 else float(body_muscles[muscle_index])
        for muscle_index in reversed(stored_selector2_1_0)
    )


def iter_endfield_body_muscle_gather(
    body_muscles: Sequence[float],
    human_bone_to_compact: Sequence[int],
):
    """Yield the mapped body work issued by retail f5 RVA ``0xB25830``.

    Hips/index zero is intentionally excluded.  Retail iterates human-bone
    indices 1 through 24 and ``B25910`` skips only the mapping sentinel -1.
    The yielded selector tuple is ready for the ``B38B10 -> B34260`` local
    quaternion converter.
    """

    if len(human_bone_to_compact) < ENDFIELD_BODY_HUMAN_BONE_END:
        raise DecodeError(
            f"human-bone map has {len(human_bone_to_compact)} values; "
            f"expected at least {ENDFIELD_BODY_HUMAN_BONE_END}"
        )
    for human_bone_index in range(
        ENDFIELD_BODY_HUMAN_BONE_BEGIN,
        ENDFIELD_BODY_HUMAN_BONE_END,
    ):
        compact_bone_index = int(human_bone_to_compact[human_bone_index])
        if compact_bone_index == -1:
            continue
        yield {
            "human_bone_index": human_bone_index,
            "compact_bone_index": compact_bone_index,
            "selector_muscles": gather_endfield_body_selector_muscles(
                body_muscles,
                human_bone_index,
            ),
        }


def gather_endfield_finger_selector_muscles(
    hand_muscles: Sequence[float],
    finger_index: int,
) -> tuple[tuple[float, float, float], ...]:
    """Reproduce one four-muscle hand group from retail RVA ``0xB25300``.

    Each side contains five contiguous groups ordered as phalanx-1 stretched,
    spread, phalanx-2 stretched, phalanx-3 stretched. The converter receives three
    phalanx vectors in selector order 0/1/2.  Constant zero lanes reproduce
    the two SIMD masks at RVAs 0x1DDFB60 and 0x1DDFB70.
    """

    expected = ENDFIELD_FINGER_COUNT * ENDFIELD_FINGER_MUSCLES_PER_FINGER
    if len(hand_muscles) < expected:
        raise DecodeError(
            f"hand-muscle array has {len(hand_muscles)} values; expected at least {expected}"
        )
    if not 0 <= int(finger_index) < ENDFIELD_FINGER_COUNT:
        raise DecodeError(f"finger index is out of range: {finger_index}")
    offset = int(finger_index) * ENDFIELD_FINGER_MUSCLES_PER_FINGER
    phalanx1_stretched = float(hand_muscles[offset])
    spread = float(hand_muscles[offset + 1])
    phalanx2_stretched = float(hand_muscles[offset + 2])
    phalanx3_stretched = float(hand_muscles[offset + 3])
    return (
        (0.0, spread, phalanx1_stretched),
        (0.0, 0.0, phalanx2_stretched),
        (0.0, 0.0, phalanx3_stretched),
    )


def iter_endfield_finger_muscle_gather(
    hand_muscles: Sequence[float],
    finger_phalanx_to_compact: Sequence[int],
):
    """Yield the mapped phalanx work issued by retail f5 RVA ``0xB25300``."""

    expected_mappings = ENDFIELD_FINGER_COUNT * ENDFIELD_FINGER_PHALANGES
    if len(finger_phalanx_to_compact) < expected_mappings:
        raise DecodeError(
            f"finger mapping has {len(finger_phalanx_to_compact)} values; "
            f"expected at least {expected_mappings}"
        )
    for finger_index in range(ENDFIELD_FINGER_COUNT):
        selector_vectors = gather_endfield_finger_selector_muscles(
            hand_muscles,
            finger_index,
        )
        for phalanx_index, selector_muscles in enumerate(selector_vectors):
            mapping_index = finger_index * ENDFIELD_FINGER_PHALANGES + phalanx_index
            compact_bone_index = int(finger_phalanx_to_compact[mapping_index])
            # B25300 uses TEST/JS rather than the body helper's CMP -1/JE.
            if compact_bone_index < 0:
                continue
            yield {
                "finger_index": finger_index,
                "phalanx_index": phalanx_index,
                "compact_bone_index": compact_bone_index,
                "selector_muscles": selector_muscles,
            }


def muscle_to_selector_angle(muscle: float, lower: float, upper: float) -> float:
    """Reproduce RVA 0xA796AB-0xA79737 for one muscle/limit lane.

    ``GetZYRoll`` selects the upper limit for a nonnegative muscle and the
    lower limit for a negative muscle. It linearly extrapolates over-range
    values and contains no ``[-1, 1]`` muscle clamp. The unusual same-side
    limit fallbacks are preserved exactly instead of assuming every Avatar
    limit straddles zero.
    """

    muscle = float(muscle)
    lower = float(lower)
    upper = float(upper)
    if muscle < 0.0:
        if lower < 0.0:
            return (-muscle) * lower
        if lower > 0.0:
            return muscle
        return 0.0
    if upper > 0.0:
        return upper * muscle
    if upper < 0.0:
        return muscle
    return 0.0


def native_zyroll_half_angle(selector_angle: float) -> float:
    """Apply GetZYRoll's modulo-2pi reduction and tan singularity guard."""

    selector_angle = float(selector_angle)
    if not math.isfinite(selector_angle):
        raise DecodeError("selector angle must be finite")
    magnitude = NATIVE_ZYROLL_PI + abs(selector_angle)
    turns = math.trunc(magnitude / NATIVE_ZYROLL_TWO_PI)
    reduced_magnitude = (
        magnitude - turns * NATIVE_ZYROLL_TWO_PI - NATIVE_ZYROLL_PI
    )
    # Native XORs the original input sign onto the signed modulo residual.
    # ``copysign(residual, input)`` would incorrectly discard the residual's
    # own sign for inputs in (pi, 2*pi), e.g. +4 radians must wrap negative.
    reduced = (
        -reduced_magnitude
        if math.copysign(1.0, selector_angle) < 0.0
        else reduced_magnitude
    )
    half_angle = 0.5 * reduced
    return max(
        -NATIVE_ZYROLL_HALF_ANGLE_LIMIT,
        min(NATIVE_ZYROLL_HALF_ANGLE_LIMIT, half_angle),
    )


def from_axes_zyroll(
    selector_angles: Sequence[float],
    selector_signs: Sequence[float] | None = None,
) -> list[float]:
    """Reproduce UnityPlayer RVA 0xA795C0 after muscle-to-angle scaling.

    ``selector_angles`` are limit-scaled radians in binary selector order
    0/1/2. Optional ``selector_signs`` reproduce the sign-bit XOR applied to
    the tangent lanes at RVA ``0xA7986D``. The native rational tangent
    approximation is represented by ``math.tan`` here, so this is semantically
    exact but not promised bit-identical at the last float bits.
    """

    if len(selector_angles) != 3:
        raise DecodeError("ZYRoll construction requires three selector angles")
    signs = selector_signs if selector_signs is not None else (1.0, 1.0, 1.0)
    if len(signs) != 3:
        raise DecodeError("ZYRoll construction requires three selector signs")
    tangents: list[float] = []
    for angle, sign in zip(selector_angles, signs):
        tangent = math.tan(native_zyroll_half_angle(float(angle)))
        if math.copysign(1.0, float(sign)) < 0.0:
            tangent = -tangent
        tangents.append(tangent)
    tx, ty, tz = tangents
    packed = [tx, ty + tx * tz, tz - tx * ty, 1.0]
    if not all(math.isfinite(component) for component in packed):
        raise DecodeError("selector angles produced a non-finite ZYRoll quaternion")
    return normalize_quaternion(packed)


def avatar_local_rotation_from_selector_angles(
    pre_q: Sequence[float],
    post_q: Sequence[float],
    selector_angles: Sequence[float],
    selector_signs: Sequence[float] | None = None,
) -> list[float]:
    """Construct the exact Avatar-local rotation from already-scaled angles."""

    axes_q = from_axes_zyroll(selector_angles, selector_signs)
    return normalize_quaternion(
        multiply_quaternions(
            multiply_quaternions(pre_q, axes_q),
            inverse_quaternion(post_q),
        )
    )


def human_fix_twist_human_local(
    parent_pre_q: Sequence[float],
    parent_post_q: Sequence[float],
    parent_selector_angles: Sequence[float],
    parent_selector_signs: Sequence[float],
    child_local_rotation: Sequence[float],
    factor: float,
) -> tuple[list[float], list[float]]:
    """Apply native ``HumanFixTwist`` in the human-local pose domain.

    Installed ``UnityPlayer.dll`` RVA ``0xB27930`` rescales only selector zero
    (roll/twist) for the pair's parent, reconstructs that parent through the
    Avatar referential, and compensates the child so its world orientation is
    unchanged. This helper implements that recovered quaternion rule. The
    downstream hierarchy propagation, compact-to-physical 48-byte TRS copy,
    and component-wise generic overlay order are now instruction-closed. This
    local helper still does not itself write a physical Transform hierarchy,
    and its output must be labelled source-derived until an observed retail-f5
    numeric fixture validates production equivalence.
    """

    if len(parent_selector_angles) != 3:
        raise DecodeError("HumanFixTwist requires three parent selector angles")
    factor = float(factor)
    if not math.isfinite(factor):
        raise DecodeError("HumanFixTwist factor must be finite")
    parent_before = avatar_local_rotation_from_selector_angles(
        parent_pre_q,
        parent_post_q,
        parent_selector_angles,
        parent_selector_signs,
    )
    scaled_angles = [float(value) for value in parent_selector_angles]
    scaled_angles[0] *= factor
    parent_after = avatar_local_rotation_from_selector_angles(
        parent_pre_q,
        parent_post_q,
        scaled_angles,
        parent_selector_signs,
    )
    parent_delta = normalize_quaternion(
        multiply_quaternions(inverse_quaternion(parent_before), parent_after)
    )
    child_after = normalize_quaternion(
        multiply_quaternions(inverse_quaternion(parent_delta), child_local_rotation)
    )
    return parent_after, child_after


def avatar_local_rotation_from_muscles(
    pre_q: Sequence[float],
    post_q: Sequence[float],
    muscles: Sequence[float],
    lower_limits: Sequence[float],
    upper_limits: Sequence[float],
    selector_signs: Sequence[float],
) -> list[float]:
    """Recover one Avatar bone's pre-TwistSolve local rotation from muscles.

    The ordered human-local redistribution is exposed separately through
    :func:`human_fix_twist_human_local`. A caller may use the recovered
    compact-to-physical and generic-component order for a source-derived
    semantic pose. It must not label that pose an observed or bit-exact retail
    runtime result until an original full-frame numeric fixture validates it.
    """

    if not all(
        len(values) == 3
        for values in (muscles, lower_limits, upper_limits, selector_signs)
    ):
        raise DecodeError("muscles, limits, and selector signs must have three lanes")
    selector_angles = [
        muscle_to_selector_angle(muscle, lower, upper)
        for muscle, lower, upper in zip(muscles, lower_limits, upper_limits)
    ]
    return avatar_local_rotation_from_selector_angles(
        pre_q,
        post_q,
        selector_angles,
        selector_signs,
    )


def quaternion_continuity(value: list[float], previous: Sequence[float] | None) -> list[float]:
    if previous is not None and sum(a * b for a, b in zip(value, previous)) < 0.0:
        return [-component for component in value]
    return value


def base64_byte_length(value: Any) -> int:
    if not value:
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        try:
            return len(base64.b64decode(value, validate=False))
        except Exception:
            return -1
    return -1


def humanoid_scalar_name(attribute: int) -> str:
    if 0 <= attribute <= 2:
        return f"MotionT.{COMPONENT_NAMES[attribute]}"
    if 3 <= attribute <= 6:
        return f"MotionQ.{COMPONENT_NAMES[attribute - 3]}"
    if 7 <= attribute <= 9:
        return f"RootT.{COMPONENT_NAMES[attribute - 7]}"
    if 10 <= attribute <= 13:
        return f"RootQ.{COMPONENT_NAMES[attribute - 10]}"
    limb_names = ("LeftFoot", "RightFoot", "LeftHand", "RightHand")
    if 14 <= attribute < 42:
        offset = attribute - 14
        limb = limb_names[offset // 7]
        component = offset % 7
        suffix = f"T.{COMPONENT_NAMES[component]}" if component < 3 else f"Q.{COMPONENT_NAMES[component - 3]}"
        return f"{limb}{suffix}"
    muscle_slot = attribute - HUMANOID_MUSCLE_ATTRIBUTE_START
    if 0 <= muscle_slot < ENDFIELD_HUMANOID_MUSCLE_COUNT:
        extension_name = ENDFIELD_EXTENSION_MUSCLE_NAMES.get(muscle_slot)
        if extension_name:
            return extension_name
        unity_slot = muscle_slot - sum(
            1 for extension_slot in ENDFIELD_EXTENSION_MUSCLE_SLOTS
            if extension_slot < muscle_slot
        )
        return f"UnityHumanoidMuscle[{unity_slot}]"
    return f"HumanoidScalar[{attribute}]"


def humanoid_scalar_metadata(attribute: int) -> dict[str, Any]:
    """Describe one Animator customType=8 attribute without guessing a retarget.

    Stock motion/root/limb-IK meanings were already decoded by this sampler.
    Muscle attributes are preserved by stable Endfield slot index.  The six
    inserted Endfield-only slots carry their binary-backed names, selectors,
    bone ownership, limits, Avatar sandwich contract, and ordered human-local
    TwistSolve rule. The exact mapped parent/child write boundary is recovered,
    but they remain unapplied until an original full-frame numeric fixture
    validates a safe physical transform-track bake.
    """

    result: dict[str, Any] = {
        "attribute": int(attribute),
        "semantic": humanoid_scalar_name(attribute),
        "applied": False,
    }
    if 0 <= attribute < 7:
        result["category"] = "motion"
    elif 7 <= attribute < 14:
        result["category"] = "root"
    elif 14 <= attribute < HUMANOID_MUSCLE_ATTRIBUTE_START:
        result["category"] = "limb_ik"
    elif HUMANOID_MUSCLE_ATTRIBUTE_START <= attribute < ENDFIELD_HUMANOID_ATTRIBUTE_END:
        muscle_slot = attribute - HUMANOID_MUSCLE_ATTRIBUTE_START
        result["muscle_slot"] = muscle_slot
        if muscle_slot in ENDFIELD_EXTENSION_MUSCLE_NAMES:
            result["category"] = "endfield_humanoid_extension"
            result.update(ENDFIELD_EXTENSION_MUSCLE_BINDINGS[muscle_slot])
            result["avatar_axis_formula"] = (
                "preQ * FromAxes_ZYRoll(selector_angles) * inverse(postQ)"
            )
            result["mapping_status"] = (
                "binary_selector_and_exact_avatar_axis_record_recovered_"
                "pinned_runtime_bake_oracle_recovered_not_integrated"
            )
        else:
            unity_slot = muscle_slot - sum(
                1 for extension_slot in ENDFIELD_EXTENSION_MUSCLE_SLOTS
                if extension_slot < muscle_slot
            )
            result["category"] = "unity_humanoid_muscle"
            result["unity_muscle_slot"] = unity_slot
            result["mapping_status"] = "shifted_slot_preserved_avatar_mapping_required"
    else:
        result["category"] = "reserved_or_unknown"
        result["mapping_status"] = "preserved_unmapped"
    return result


def analyze_humanoid_index_array(values: Sequence[Any], source_scalar_count: int) -> dict[str, Any]:
    """Preserve the complete Endfield MuscleClip index table and validate links."""

    index_array = [int(value) for value in (values or [])]
    mapped_attributes: list[dict[str, Any]] = []
    out_of_range: list[dict[str, int]] = []
    for attribute, scalar_index in enumerate(index_array):
        if scalar_index < 0:
            continue
        row = humanoid_scalar_metadata(attribute)
        row["source_scalar_index"] = scalar_index
        mapped_attributes.append(row)
        if scalar_index >= source_scalar_count:
            out_of_range.append({"attribute": attribute, "source_scalar_index": scalar_index})

    extension_slots = list(ENDFIELD_EXTENSION_MUSCLE_SLOTS)
    mapped_extension_slots = [
        int(row["muscle_slot"])
        for row in mapped_attributes
        if row.get("category") == "endfield_humanoid_extension"
    ]
    return {
        "layout": (
            "endfield_101_muscle_206_index"
            if len(index_array) == ENDFIELD_HUMANOID_INDEX_ARRAY_COUNT
            else "unexpected_index_array_length"
        ),
        "index_array_count": len(index_array),
        "expected_index_array_count": ENDFIELD_HUMANOID_INDEX_ARRAY_COUNT,
        "motion_root_limb_attribute_count": HUMANOID_MUSCLE_ATTRIBUTE_START,
        "unity_muscle_slot_count": UNITY_HUMANOID_MUSCLE_COUNT,
        "endfield_muscle_slot_count": ENDFIELD_HUMANOID_MUSCLE_COUNT,
        "endfield_extension_slots": extension_slots,
        "endfield_extension_names": {
            str(slot): ENDFIELD_EXTENSION_MUSCLE_NAMES[slot]
            for slot in extension_slots
        },
        "endfield_extension_bindings": {
            str(slot): dict(ENDFIELD_EXTENSION_MUSCLE_BINDINGS[slot])
            for slot in extension_slots
        },
        "native_evidence": dict(ENDFIELD_HUMANOID_NATIVE_EVIDENCE),
        "mapped_endfield_extension_slots": mapped_extension_slots,
        "unmapped_endfield_extension_slots": sorted(set(extension_slots) - set(mapped_extension_slots)),
        "mapped_attribute_count": len(mapped_attributes),
        "mapped_attributes": mapped_attributes,
        "mapped_source_scalar_indices": [int(row["source_scalar_index"]) for row in mapped_attributes],
        "out_of_range_source_scalar_links": out_of_range,
        "retarget_status": (
            "exact_playable_avatar_referentials_and_pinned_original_pose_oracle_"
            "recovered_runtime_transform_bake_not_integrated"
        ),
    }


def relevant_clip_settings(muscle: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "m_StartTime",
        "m_StopTime",
        "m_LoopTime",
        "m_LoopBlend",
        "m_LoopBlendOrientation",
        "m_LoopBlendPositionY",
        "m_LoopBlendPositionXZ",
        "m_StartAtOrigin",
        "m_KeepOriginalOrientation",
        "m_KeepOriginalPositionY",
        "m_KeepOriginalPositionXZ",
        "m_OrientationOffsetY",
        "m_CycleOffset",
        "m_AverageAngularSpeed",
    )
    result = {key: muscle.get(key) for key in keys}
    result["m_AverageSpeed"] = muscle.get("m_AverageSpeed")
    return result


class ClipSampler:
    def __init__(self, clip: dict[str, Any], transforms: Sequence[dict[str, Any]], sample_rate: float | None = None):
        self.clip = clip
        self.muscle = clip.get("m_MuscleClip") or {}
        self.raw_clip = self.muscle.get("m_Clip") or {}
        self.streamed = self.raw_clip.get("m_StreamedClip") or {}
        self.dense = self.raw_clip.get("m_DenseClip") or {}
        self.constant = self.raw_clip.get("m_ConstantClip") or {}
        self.bindings = (clip.get("m_ClipBindingConstant") or {}).get("genericBindings") or []
        self.scalar_bindings = expand_bindings(self.bindings)
        self.transforms = list(transforms)
        self.transforms_by_crc = {int(item["path_crc"]): item for item in transforms}

        self.stream_count = int(self.streamed.get("curveCount") or 0)
        self.dense_count = int(self.dense.get("m_CurveCount") or 0)
        self.constant_count = len(self.constant.get("data") or [])
        self.source_scalar_count = self.stream_count + self.dense_count + self.constant_count
        if len(self.scalar_bindings) != self.source_scalar_count:
            raise DecodeError(
                f"expanded binding count {len(self.scalar_bindings)} != streamed+dense+constant "
                f"{self.stream_count}+{self.dense_count}+{self.constant_count}={self.source_scalar_count}"
            )
        self.humanoid_layout = analyze_humanoid_index_array(
            self.muscle.get("m_IndexArray") or [],
            self.source_scalar_count,
        )

        frames = parse_stream_frames(self.streamed.get("data") or [])
        self.stream_frames = frames
        self.stream_curves, self.warnings = build_stream_curves(frames, self.stream_count)
        if self.humanoid_layout["layout"] != "endfield_101_muscle_206_index":
            self.warnings.append(
                "m_IndexArray has "
                f"{self.humanoid_layout['index_array_count']} entries; expected the observed Endfield 206-entry layout"
            )
        if self.humanoid_layout["out_of_range_source_scalar_links"]:
            self.warnings.append(
                f"{len(self.humanoid_layout['out_of_range_source_scalar_links'])} humanoid index links exceed "
                f"the {self.source_scalar_count} serialized scalar curves"
            )

        self.dense_frame_count = int(self.dense.get("m_FrameCount") or 0)
        self.dense_rate = float(self.dense.get("m_SampleRate") or 0.0)
        self.dense_begin = float(self.dense.get("m_BeginTime") or 0.0)
        self.dense_samples = self.dense.get("m_SampleArray") or []
        if self.dense_count and len(self.dense_samples) < self.dense_count * self.dense_frame_count:
            raise DecodeError(
                f"dense sample array has {len(self.dense_samples)} values; expected "
                f"{self.dense_count * self.dense_frame_count}"
            )

        default_rate = self.dense_rate or float(clip.get("m_SampleRate") or 60.0)
        self.sample_rate = float(sample_rate or default_rate or 60.0)
        if not math.isfinite(self.sample_rate) or self.sample_rate <= 0.0:
            raise DecodeError(f"invalid output sample rate {self.sample_rate}")

        stop_time = float(self.muscle.get("m_StopTime") or 0.0)
        dense_end = self.dense_begin
        if self.dense_frame_count > 1 and self.dense_rate > 0.0:
            dense_end += (self.dense_frame_count - 1) / self.dense_rate
        stream_end = max((frame.time for frame in real_stream_frames(frames)), default=0.0)
        self.duration = max(stop_time, dense_end, stream_end)
        if stop_time > 0.0:
            # The final streamed key is commonly one float ULP beyond StopTime.
            self.duration = stop_time

        self.track_layout, self.unmatched_transform_paths = self._build_track_layout()

    def _build_track_layout(self) -> tuple[list[dict[str, Any]], list[int]]:
        by_crc: dict[int, dict[str, Any]] = {}
        order: list[int] = []
        unmatched: set[int] = set()
        for scalar in self.scalar_bindings:
            if scalar.type_id != "Transform":
                continue
            if scalar.path_crc not in self.transforms_by_crc:
                unmatched.add(scalar.path_crc)
                continue
            if scalar.path_crc not in by_crc:
                transform = self.transforms_by_crc[scalar.path_crc]
                by_crc[scalar.path_crc] = {
                    "path_crc": scalar.path_crc,
                    "path": transform["path"],
                    "name": transform["name"],
                    "local_pos": list(transform["local_pos"]),
                    "local_rot": list(transform["local_rot"]),
                    "local_scale": list(transform["local_scale"]),
                    "channels": defaultdict(list),
                }
                order.append(scalar.path_crc)
            by_crc[scalar.path_crc]["channels"][scalar.attribute].append(scalar)
        return [by_crc[crc] for crc in order], sorted(unmatched)

    def game_object_active_bindings(self) -> list[ScalarBinding]:
        return [
            scalar
            for scalar in self.scalar_bindings
            if scalar.type_id == "GameObject"
            and scalar.attribute == GAME_OBJECT_ACTIVE_ATTRIBUTE
            and scalar.path_crc in self.transforms_by_crc
        ]

    def scalar_source(self, scalar_index: int) -> tuple[str, int]:
        if scalar_index < self.stream_count:
            return "streamed", scalar_index
        scalar_index -= self.stream_count
        if scalar_index < self.dense_count:
            return "dense", scalar_index
        scalar_index -= self.dense_count
        if scalar_index < self.constant_count:
            return "constant", scalar_index
        raise DecodeError(f"scalar index {scalar_index} outside source ranges")

    def scalar_value(self, scalar_index: int, time: float) -> float:
        source, local_index = self.scalar_source(scalar_index)
        if source == "streamed":
            keys = self.stream_curves.get(local_index)
            if not keys:
                raise DecodeError(f"streamed scalar {local_index} has no finite key")
            return evaluate_stream_curve(keys, time)
        if source == "dense":
            return evaluate_dense_curve(
                self.dense_samples,
                self.dense_count,
                self.dense_frame_count,
                self.dense_rate,
                self.dense_begin,
                local_index,
                time,
            )
        return float((self.constant.get("data") or [])[local_index])

    def sample_times(self) -> list[float]:
        if self.duration <= 0.0:
            return [0.0]
        scaled = self.duration * self.sample_rate
        nearest = round(scaled)
        count = int(nearest if abs(scaled - nearest) <= 1.0e-3 else math.ceil(scaled))
        times = [min(self.duration, frame / self.sample_rate) for frame in range(count + 1)]
        times[-1] = self.duration
        return times

    def sample(self, source_path: Path | None = None, include_frames: bool = True) -> dict[str, Any]:
        times = self.sample_times()
        channel_presence: dict[str, set[int]] = {"pos": set(), "rot": set(), "scale": set()}
        channel_values: dict[str, dict[int, list[tuple[float, ...]]]] = {
            "pos": defaultdict(list),
            "rot": defaultdict(list),
            "scale": defaultdict(list),
        }
        output_frames: list[dict[str, Any]] = []
        previous_rotations: list[list[float] | None] = [None] * len(self.track_layout)

        root_scalars = [
            scalar
            for scalar in self.scalar_bindings
            if scalar.type_id == "Animator" and scalar.custom_type == 8 and 0 <= scalar.attribute <= 13
        ]
        root_motion_frames: list[dict[str, Any]] = []

        for time in times:
            frame_tracks: list[dict[str, list[float]]] = []
            for track_index, track in enumerate(self.track_layout):
                translation = list(track["local_pos"])
                rotation = list(track["local_rot"])
                scale = list(track["local_scale"])
                channels = track["channels"]
                for attribute, target, label in (
                    (1, translation, "pos"),
                    (2, rotation, "rot"),
                    (3, scale, "scale"),
                ):
                    scalars = channels.get(attribute) or []
                    if scalars:
                        channel_presence[label].add(track_index)
                    for scalar in scalars:
                        if scalar.component < len(target):
                            target[scalar.component] = self.scalar_value(scalar.scalar_index, time)
                rotation = quaternion_continuity(normalize_quaternion(rotation), previous_rotations[track_index])
                previous_rotations[track_index] = rotation
                channel_values["pos"][track_index].append(tuple(translation))
                channel_values["rot"][track_index].append(tuple(rotation))
                channel_values["scale"][track_index].append(tuple(scale))
                if include_frames:
                    frame_tracks.append({"rotation": rotation, "translation": translation, "scale": scale})
            if include_frames:
                output_frames.append({"time": time, "tracks": frame_tracks})

            if root_scalars:
                values = {humanoid_scalar_name(item.attribute): self.scalar_value(item.scalar_index, time) for item in root_scalars}
                if include_frames:
                    root_motion_frames.append({"time": time, "values": values})

        varying: dict[str, list[int]] = {}
        for channel, tracks in channel_values.items():
            varying[channel] = sorted(
                index
                for index, values in tracks.items()
                if values and any(
                    max(abs(a - b) for a, b in zip(values[0], value)) > 1.0e-6 for value in values[1:]
                )
            )

        non_transform_summary: list[dict[str, Any]] = []
        for scalar in self.scalar_bindings:
            if scalar.type_id == "Transform":
                continue
            sampled = [self.scalar_value(scalar.scalar_index, time) for time in times]
            semantic = (
                humanoid_scalar_name(scalar.attribute)
                if scalar.type_id == "Animator" and scalar.custom_type == 8
                else f"{scalar.type_id}.attribute_{scalar.attribute}"
            )
            source, local_index = self.scalar_source(scalar.scalar_index)
            non_transform_summary.append(
                {
                    "scalar_index": scalar.scalar_index,
                    "binding_index": scalar.binding_index,
                    "type_id": scalar.type_id,
                    "custom_type": scalar.custom_type,
                    "attribute": scalar.attribute,
                    "semantic": semantic,
                    "source": source,
                    "source_local_index": local_index,
                    "minimum": min(sampled),
                    "maximum": max(sampled),
                    "first": sampled[0],
                    "last": sampled[-1],
                    "varying": max(sampled) - min(sampled) > 1.0e-6,
                    "applied": False,
                    **(
                        {"humanoid": humanoid_scalar_metadata(scalar.attribute)}
                        if scalar.type_id == "Animator" and scalar.custom_type == 8
                        else {}
                    ),
                }
            )

        game_object_active_curves: list[dict[str, Any]] = []
        for scalar in self.game_object_active_bindings():
            transform = self.transforms_by_crc[scalar.path_crc]
            game_object_active_curves.append(
                {
                    "path_crc": scalar.path_crc,
                    "path": transform["path"],
                    "name": transform["name"],
                    "property": "m_IsActive",
                    "keys": [
                        {"time": time, "value": self.scalar_value(scalar.scalar_index, time)}
                        for time in times
                    ],
                }
            )

        track_bindings = []
        euler_count = 0
        for track_index, track in enumerate(self.track_layout):
            channel_names = []
            for attribute in sorted(track["channels"]):
                name = TRANSFORM_CHANNELS.get(attribute, f"attribute_{attribute}")
                channel_names.append(name)
                if attribute == 4:
                    euler_count += 1
            track_bindings.append(
                {
                    "track_index": track_index,
                    "path": track["path"],
                    "name": track["name"],
                    "path_crc": track["path_crc"],
                    "declared_channels": channel_names,
                }
            )

        acl = self.clip.get("m_AclCompressedBuffer") or {}
        sidecar = {
            "transform_buffer_bytes": base64_byte_length(acl.get("TransformBufferData")),
            "root_motion_buffer_bytes": base64_byte_length(acl.get("RootMotionBufferData")),
            "float_buffer_bytes": base64_byte_length(acl.get("FloatBufferData")),
            "float_curve_count": int(acl.get("FloatCurveCount") or 0),
            "root_pos_index": int(acl.get("RootPosIndex") if acl.get("RootPosIndex") is not None else 65535),
            "root_rot_index": int(acl.get("RootRotIndex") if acl.get("RootRotIndex") is not None else 65535),
            "root_scale_index": int(acl.get("RootScaleIndex") if acl.get("RootScaleIndex") is not None else 65535),
            "root_track_count": int(acl.get("RootTrackCount") or 0),
        }

        source_name = str(self.clip.get("Name") or self.clip.get("m_Name") or (source_path.stem if source_path else "AnimationClip"))
        relative_source = str(source_path) if source_path else ""
        if source_path:
            try:
                relative_source = str(source_path.resolve().relative_to(REPO_ROOT))
            except ValueError:
                relative_source = str(source_path.resolve())

        limitations = [
            "Animator muscle/float curves are decoded as evidence but not applied to generic transform tracks.",
            "Endfield's 101 humanoid muscle slots are preserved in their binary table order; inserted extension slots 28/30/31/39/41/42 have binary-backed names, selectors, limits, exact Avatar axis records, recovered GetZYRoll scaling/range reduction, native eight-pair TwistSolve order, and exact mapped parent/child write ownership, but remain unapplied until an original full-frame numeric fixture validates the physical transform-track bake.",
            "Root motion is not applied: Character Info rotation-only behavior is recovered, but gameplay controller blending and movement-motor application remain incomplete.",
            "Animation events, object-reference curves, and runtime AnimatorController blending are outside this sampler.",
        ]
        if euler_count:
            limitations.append(f"{euler_count} Euler transform bindings are reported but not converted to qvvf rotations.")
        if self.unmatched_transform_paths:
            limitations.append(
                f"{len(self.unmatched_transform_paths)} transform paths do not exist in the supplied recovered hierarchy."
            )

        payload: dict[str, Any] = {
            "ok": True,
            "hash_ok": True,
            "validation_error": None,
            "clip_name": source_name,
            "buffer_name": "UnityMuscleClipStreamedDenseConstant",
            "source_json": relative_source,
            "sample_source": "unity_muscleclip_standard",
            "num_tracks": len(self.track_layout),
            "num_samples": len(times),
            "sample_rate": self.sample_rate,
            "duration": self.duration,
            "finite_duration": self.duration,
            "track_type": "qvvf",
            # These are declared/present channels, including non-bind constants.
            "animated_track_indices": {key: sorted(value) for key, value in channel_presence.items()},
            "varying_track_indices": varying,
            "track_bindings": track_bindings,
            "source_ranges": {
                "streamed": {"start": 0, "count": self.stream_count},
                "dense": {"start": self.stream_count, "count": self.dense_count},
                "constant": {"start": self.stream_count + self.dense_count, "count": self.constant_count},
                "expanded_binding_scalar_count": len(self.scalar_bindings),
            },
            "clip_settings": relevant_clip_settings(self.muscle),
            "acl_sidecar_evidence": sidecar,
            "humanoid_layout": self.humanoid_layout,
            "runtime_root_motion_policy": dict(ENDFIELD_ROOT_MOTION_RUNTIME_POLICY),
            "root_motion_evidence": {
                "status": "decoded_scalar_evidence_not_applied" if root_scalars else "no_animator_motion_bindings",
                "semantic_contract": {
                    "motion_tq": "character_object_trajectory_in_clip_space",
                    "root_tq": "absolute_body_reference_in_the_same_clip_space_not_motion_relative_delta",
                    "world_composition": "compose_motion_with_actor_start_transform",
                    "retail_object_consumer": "Animator.deltaPosition_and_deltaRotation_after_evaluation",
                    "character_info_rotation_delta": "inverse_previous_motion_q_times_current_motion_q_then_postmultiply_actor_rotation",
                    "character_info_translation": "not_consumed_by_recovered_CharUIModelMono_OnAnimatorMove",
                    "raw_root_application": "forbidden",
                    "remaining_boundary": "translation_keep_flags_loop_blending_motionless_clips_controller_blending_and_avatar_reconstruction",
                },
                "scalar_curve_count": len(root_scalars),
                "muscle_index_array_mapped_indices": self.humanoid_layout["mapped_source_scalar_indices"],
                "frames": root_motion_frames,
            },
            "unapplied_scalar_curves": non_transform_summary,
            "game_object_active_curves": game_object_active_curves,
            "validation": {
                "binding_scalar_count_matches_sources": len(self.scalar_bindings) == self.source_scalar_count,
                "stream_frame_count_including_sentinels": len(self.stream_frames),
                "stream_curve_count_with_finite_keys": len(self.stream_curves),
                "matched_transform_track_count": len(self.track_layout),
                "unmatched_transform_path_count": len(self.unmatched_transform_paths),
                "unmatched_transform_path_crcs": self.unmatched_transform_paths,
                "warnings": self.warnings,
            },
            "limitations": limitations,
            "frames": output_frames,
        }
        return payload


def has_acl_transform_buffer(clip: dict[str, Any]) -> bool:
    return base64_byte_length((clip.get("m_AclCompressedBuffer") or {}).get("TransformBufferData")) > 0


def discover_clips(clip_dir: Path) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(clip_dir.glob("*.json")):
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        name = str(data.get("Name") or data.get("m_Name") or path.stem)
        result[name].append(path)
    return dict(result)


def select_names(
    discovered: dict[str, list[Path]],
    explicit_names: Sequence[str],
    cached_animation_dir: Path | None,
    actor_token: str | None,
) -> list[str]:
    if explicit_names:
        return sorted(dict.fromkeys(explicit_names))
    if cached_animation_dir:
        return sorted(path.stem for path in cached_animation_dir.glob("*.anim"))
    names = sorted(discovered)
    if actor_token:
        token = actor_token.lower()
        names = [name for name in names if token in name.lower()]
    return names


def choose_source(paths: Sequence[Path], transform_crcs: set[int]) -> Path:
    """Resolve duplicate clip names by strongest recovered-hierarchy coverage."""

    scored: list[tuple[int, int, str, Path]] = []
    for path in paths:
        data = load_json(path)
        bindings = (data.get("m_ClipBindingConstant") or {}).get("genericBindings") or []
        paths_in_clip = {
            int(binding.get("path") or 0) for binding in bindings if str(binding.get("typeID")) == "Transform"
        }
        scored.append((len(paths_in_clip & transform_crcs), len(paths_in_clip), path.name, path))
    return max(scored, key=lambda item: (item[0], item[1], item[2]))[-1]


def compact_result(payload: dict[str, Any]) -> dict[str, Any]:
    root_scalars = [
        item
        for item in payload["unapplied_scalar_curves"]
        if item["type_id"] == "Animator" and item["custom_type"] == 8 and 0 <= item["attribute"] <= 13
    ]
    return {
        "clip_name": payload["clip_name"],
        "source_json": payload["source_json"],
        "num_tracks": payload["num_tracks"],
        "num_samples": payload["num_samples"],
        "duration": payload["duration"],
        "source_ranges": payload["source_ranges"],
        "animated_track_counts": {key: len(value) for key, value in payload["animated_track_indices"].items()},
        "varying_track_counts": {key: len(value) for key, value in payload["varying_track_indices"].items()},
        "unapplied_scalar_curve_count": len(payload["unapplied_scalar_curves"]),
        "game_object_active_curve_count": len(payload.get("game_object_active_curves") or []),
        "varying_unapplied_scalar_curve_count": sum(
            bool(item["varying"]) for item in payload["unapplied_scalar_curves"]
        ),
        "root_motion_scalar_curve_count": payload["root_motion_evidence"]["scalar_curve_count"],
        "root_motion_semantic_contract": payload["root_motion_evidence"]["semantic_contract"],
        "varying_root_motion_scalar_curve_count": sum(bool(item["varying"]) for item in root_scalars),
        "acl_sidecar_evidence": payload["acl_sidecar_evidence"],
        "humanoid_layout": {
            key: payload["humanoid_layout"][key]
            for key in (
                "layout",
                "index_array_count",
                "unity_muscle_slot_count",
                "endfield_muscle_slot_count",
                "mapped_attribute_count",
                "mapped_endfield_extension_slots",
                "out_of_range_source_scalar_links",
                "retarget_status",
            )
        },
        "validation": payload["validation"],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip-dir", type=Path, required=True, help="AnimeStudio AnimationClip JSON directory")
    parser.add_argument("--hierarchy-dir", type=Path, required=True, help="Postmodel dump containing GameObject/*.json")
    parser.add_argument("--root-name", required=True, help="Animator/postmodel root GameObject name")
    parser.add_argument("--output-dir", type=Path, help="Directory for qvvf-like sample JSON")
    parser.add_argument("--summary-json", type=Path, help="Write exact coverage summary JSON")
    parser.add_argument("--summary-only", action="store_true", help="Validate/sample without writing frame payloads")
    parser.add_argument("--cached-animation-dir", type=Path, help="Select names of cached .anim files")
    parser.add_argument("--clip-name", action="append", default=[], help="Exact clip name; repeatable")
    parser.add_argument("--actor-token", help="Select clip names containing this token")
    parser.add_argument("--sample-rate", type=float, help="Override output sampling rate")
    args = parser.parse_args(argv)

    if not args.summary_only and args.output_dir is None:
        parser.error("--output-dir is required unless --summary-only is used")

    transforms = load_hierarchy(args.hierarchy_dir.resolve(), args.root_name)
    transform_crcs = {int(item["path_crc"]) for item in transforms}
    discovered = discover_clips(args.clip_dir.resolve())
    names = select_names(discovered, args.clip_name, args.cached_animation_dir, args.actor_token)

    summary: dict[str, Any] = {
        "root_name": args.root_name,
        "hierarchy_transform_count": len(transforms),
        "selected_name_count": len(names),
        "decoded": [],
        "skipped": [],
        "errors": [],
    }

    for name in names:
        paths = discovered.get(name) or []
        if not paths:
            summary["skipped"].append({"clip_name": name, "reason": "source_json_missing"})
            continue
        source_path = choose_source(paths, transform_crcs)
        try:
            clip = load_json(source_path)
            if has_acl_transform_buffer(clip):
                summary["skipped"].append({"clip_name": name, "reason": "acl_transform_buffer_present"})
                continue
            sampler = ClipSampler(clip, transforms, sample_rate=args.sample_rate)
            if not sampler.track_layout and not sampler.game_object_active_bindings():
                summary["skipped"].append({"clip_name": name, "reason": "no_matching_transform_tracks"})
                continue
            payload = sampler.sample(source_path, include_frames=not args.summary_only)
            summary["decoded"].append(compact_result(payload))
            if not args.summary_only and args.output_dir:
                write_json(args.output_dir.resolve() / f"{name}.json", payload)
        except Exception as exc:  # keep a complete batch audit instead of losing later clips
            summary["errors"].append({"clip_name": name, "source_json": str(source_path), "error": str(exc)})

    summary["decoded_clip_count"] = len(summary["decoded"])
    summary["skipped_clip_count"] = len(summary["skipped"])
    summary["error_clip_count"] = len(summary["errors"])
    summary["totals"] = {
        "matched_transform_tracks": sum(item["num_tracks"] for item in summary["decoded"]),
        "unmatched_transform_paths": sum(
            item["validation"]["unmatched_transform_path_count"] for item in summary["decoded"]
        ),
        "unapplied_scalar_curves": sum(item["unapplied_scalar_curve_count"] for item in summary["decoded"]),
        "root_motion_scalar_curves": sum(item["root_motion_scalar_curve_count"] for item in summary["decoded"]),
    }

    if args.summary_json:
        write_json(args.summary_json.resolve(), summary)
    print(json.dumps({key: summary[key] for key in ("selected_name_count", "decoded_clip_count", "skipped_clip_count", "error_clip_count", "totals")}, indent=2))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
