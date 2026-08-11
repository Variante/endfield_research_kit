#!/usr/bin/env python3
"""Shared Unity recovery manifest builder.

This intentionally does not import the Blender reconstruction helpers.  The
manifest follows the recovered Unity prefab hierarchy and its
SkinnedMeshRenderer bindings.

The module carries Zhuangfy defaults so it can be executed directly, while
per-character entry points override paths, actor tokens, and classification
hooks before calling :func:`main`.
"""

from __future__ import annotations

import json
import math
import re
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from character_import import foot_ik_scalar_curves, grounder_profiles


REPO_ROOT = Path(__file__).resolve().parents[2]
# Character entry points override ACTOR_TOKEN so controller-summary helpers
# filter by the right actor name without forking the manifest implementation.
ACTOR_TOKEN = "zhuangfy"

# Exact original-data identities for Last Rite renderers that are not ordinary
# character surfaces.  Neither branch has a source-compatible color path in the
# recovery lab: the skill shell is authored only for the transparent depth-only
# effect shader, while the vfxpart shell depends on CharacterNPR_VFX and its
# runtime effect inputs.  Keep this allowlist deliberately actor-, mesh-, and
# material-specific; ordinary body meshes and source-owned weapon renderers must
# never be rejected by a name-only heuristic.
LASTRITE_UNSUPPORTED_WHITE_FALLBACKS: dict[
    tuple[str, int, tuple[int, ...]], dict[str, Any]
] = {
    (
        "S_actor_lastrite_skill_01_lod0",
        -6124062222282842931,
        (-2296838609362971186,),
    ): {
        "classification": "runtime_effect_depth_only_auxiliary",
        "source_material_name": "M_fx_lastrite_ztc_060",
        "source_shader_name": "HGRP/Effect/VFXTransparentDepthOnly",
        "source_shader_path_id": -299115904279896668,
        "reason": "source shader has no color pass and the authored activation/compositor is unrecovered",
    },
    (
        "S_actor_lastrite_vfxpart_01_lod0",
        8396130562534808781,
        (-7618720439349846356,),
    ): {
        "classification": "runtime_effect_character_vfx_auxiliary",
        "source_material_name": "M_fx_lastrite_toppotential_01",
        "source_shader_name": "HGRP/CharacterNPR_VFX",
        "source_shader_path_id": 1546063667905006563,
        "reason": "source color depends on unrecovered CharacterNPR_VFX textures and runtime effect state",
    },
}
HIERARCHY_DIR = REPO_ROOT / "scratch" / "zhuangfy_postmodel_hierarchy_json" / "GameObject"
MESH_DIR = REPO_ROOT / "scratch" / "zhuangfy_mesh_json" / "Mesh"
MATERIAL_DIR: Path | None = None
ALT_MESH_DIR = REPO_ROOT / "scratch" / "zhuangfy_mesh_json_de408" / "Mesh"
LEGACY_ANIMATION_CLIP_DIR = REPO_ROOT / "scratch" / "zhuangfy_animation_clip_json" / "AnimationClip"
FULL_ANIMATION_CLIP_DIR = REPO_ROOT / "scratch" / "zhuangfy_all_animation_clip_json" / "AnimationClip"
ANIMATION_CLIP_DIR = FULL_ANIMATION_CLIP_DIR if FULL_ANIMATION_CLIP_DIR.is_dir() else LEGACY_ANIMATION_CLIP_DIR
ACL_SAMPLE_DIR = REPO_ROOT / "scratch" / "zhuangfy_acl_samples_all"

EXPORT_ROOT = REPO_ROOT / "export_full" / "recovered" / "AnimeStudio-cli"
STREAMING = EXPORT_ROOT / "StreamingAssets"
PERSISTENT = EXPORT_ROOT / "Persistent"
ASSET_MAPS = [
    STREAMING / "maps" / "endfield_streamingassets_assets.json",
    PERSISTENT / "maps" / "endfield_persistent_assets.json",
]

OUTPUT = (
    REPO_ROOT
    / "unity_endfield_graph_shader_lab"
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Zhuangfy"
    / "zhuangfy_recovery_manifest.json"
)
REPORT_OUTPUT = REPO_ROOT / "scratch" / "zhuangfy_original_usage_report.json"
ROOT_POSTMODEL_NAME = "chr_0030_zhuangfy_postmodel"
MAIN_ANIMATOR_CONTROLLER = PERSISTENT / "json_by_type" / "AnimatorController" / "AnimatorController#40707.json"
ANIMATOR_CONTROLLER_DIRS = [
    STREAMING / "json_by_type" / "AnimatorController",
    PERSISTENT / "json_by_type" / "AnimatorController",
]

CONTROLLER_BOUND_ANIMATION_CLIPS = [
    "A_actor_zhuangfy_cloth_ik_l",
    "A_actor_zhuangfy_cloth_ik_r",
    "A_actor_zhuangfy_cloth_tilt_fb1",
    "A_actor_zhuangfy_cloth_tilt_fb2",
    "A_actor_zhuangfy_cloth_tilt_rl",
    "A_actor_zhuangfy_tail_d",
    "A_actor_zhuangfy_tail_u",
    "A_actor_zhuangfy_sprint_loop_additive",
    "A_actor_zhuangfy_wind_loop_additive_cloth",
]

CANDIDATE_DIALOG_ANIMATION_CLIPS = [
    "A_actor_zhuangfy_dialog_single_run_start_hold_f",
    "A_actor_zhuangfy_dialog_single_run_start_hold_m",
    "A_actor_zhuangfy_dialog_single_run_end_hold_f",
    "A_actor_zhuangfy_dialog_single_touch_high",
    "A_actor_zhuangfy_01_cs_e10m4_1_sc001",
    "A_actor_zhuangfy_dialog_single_climax_start",
    "A_actor_zhuangfy_dialog_single_climax_loop",
    "A_actor_zhuangfy_dialog_single_climax_end",
    "A_actor_zhuangfy_dialog_state_takeoutplane_start",
    "A_actor_zhuangfy_dialog_state_takeoutplane_loop",
    "A_actor_zhuangfy_dialog_state_takeoutplane_end",
]

PLAYBACK_ANIMATION_CLIPS = [
    *CONTROLLER_BOUND_ANIMATION_CLIPS,
    *CANDIDATE_DIALOG_ANIMATION_CLIPS,
]

EXPERIMENTAL_VARIANT_MESHES = [
    ("S_actor_zhuangfy_body_02_lod0", ["M_actor_zhuangfy_body_03"]),
    ("S_actor_zhuangfy_cloth_03_lod0", ["M_actor_zhuangfy_cloth_03"]),
    ("S_actor_zhuangfy_cloth_04_lod0", ["M_actor_zhuangfy_cloth_04"]),
    ("S_actor_zhuangfy_eyebrow_02_lod0", ["M_actor_zhuangfy_brow_02"]),
    ("S_actor_zhuangfy_eyeshadow_02_lod0", ["M_eyeshadow_common_05", "M_eyewhiteshadow_common_01"]),
    ("S_actor_zhuangfy_face_02_lod0", ["M_actor_zhuangfy_face_02"]),
    ("S_actor_zhuangfy_hair_02_lod0", ["M_actor_zhuangfy_hair_02", "M_actor_zhuangfy_hairt_02"]),
    ("S_actor_zhuangfy_hairshadow_02_lod0", ["M_hairshadow_common_01"]),
    ("S_actor_zhuangfy_iris_02_lod0", ["M_actor_zhuangfy_iris_02"]),
    ("S_actor_zhuangfy_tail_02_lod0", ["M_actor_zhuangfy_hair_02"]),
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_without_top_level_field(path: Path, field_name: str) -> str:
    """Read JSON up to a large top-level field without matching nested keys.

    QVVF samples place their large transform ``frames`` array last. Stock
    Unity/MuscleClip samples also retain a much smaller nested
    ``root_motion_evidence.frames`` array before it, so a plain text search for
    ``"frames"`` truncates the JSON inside the nested object. Track JSON
    nesting and only stop when the requested key belongs to the root object.
    """

    chars: list[str] = []
    stack: list[str] = []
    in_string = False
    escaped = False
    string_chars: list[str] = []
    string_start = -1
    candidate_start: int | None = None

    with path.open("r", encoding="utf-8") as handle:
        while chunk := handle.read(1024 * 1024):
            for char in chunk:
                if in_string:
                    chars.append(char)
                    if escaped:
                        escaped = False
                        string_chars.append(char)
                    elif char == "\\":
                        escaped = True
                        string_chars.append(char)
                    elif char == '"':
                        in_string = False
                        if stack == ["{"] and "".join(string_chars) == field_name:
                            candidate_start = string_start
                    else:
                        string_chars.append(char)
                    continue

                if candidate_start is not None:
                    if char.isspace():
                        chars.append(char)
                        continue
                    if char == ":":
                        text = "".join(chars[:candidate_start]).rstrip()
                        if text.endswith(","):
                            text = text[:-1].rstrip()
                        return text + "\n}"
                    candidate_start = None

                chars.append(char)
                if char == '"':
                    in_string = True
                    escaped = False
                    string_chars = []
                    string_start = len(chars) - 1
                elif char in "{[":
                    stack.append(char)
                elif char == "}" and stack and stack[-1] == "{":
                    stack.pop()
                elif char == "]" and stack and stack[-1] == "[":
                    stack.pop()

    return "".join(chars)


_ENDFIELD_EXTENSION_MUSCLE_NAMES = {
    28: "Left Foot Twist Roll",
    30: "Left Toes Left-Right",
    31: "Left Toes Twist Roll",
    39: "Right Foot Twist Roll",
    41: "Right Toes Left-Right",
    42: "Right Toes Twist Roll",
}
_ENDFIELD_EXTENSION_MUSCLE_BINDINGS = {
    28: ("LeftFoot", 5, 0, -math.radians(20.0), math.radians(20.0)),
    30: ("LeftToes", 20, 1, -math.radians(50.0), math.radians(50.0)),
    31: ("LeftToes", 20, 0, -math.radians(40.0), math.radians(40.0)),
    39: ("RightFoot", 6, 0, -math.radians(20.0), math.radians(20.0)),
    41: ("RightToes", 21, 1, -math.radians(50.0), math.radians(50.0)),
    42: ("RightToes", 21, 0, -math.radians(40.0), math.radians(40.0)),
}
_ENDFIELD_TWIST_SOLVE_PAIRS = (
    ("LeftLowerArm", 16, "LeftHand", 18, "m_ForeArmTwist", "AvatarHuman+0x120"),
    ("LeftUpperArm", 14, "LeftLowerArm", 16, "m_ArmTwist", "AvatarHuman+0x11C"),
    ("RightLowerArm", 17, "RightHand", 19, "m_ForeArmTwist", "AvatarHuman+0x120"),
    ("RightUpperArm", 15, "RightLowerArm", 17, "m_ArmTwist", "AvatarHuman+0x11C"),
    ("LeftLowerLeg", 3, "LeftFoot", 5, "m_LegTwist", "AvatarHuman+0x128"),
    ("LeftUpperLeg", 1, "LeftLowerLeg", 3, "m_UpperLegTwist", "AvatarHuman+0x124"),
    ("RightLowerLeg", 4, "RightFoot", 6, "m_LegTwist", "AvatarHuman+0x128"),
    ("RightUpperLeg", 2, "RightLowerLeg", 4, "m_UpperLegTwist", "AvatarHuman+0x124"),
)
_ENDFIELD_HUMANOID_NATIVE_EVIDENCE = {
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
    "twist_solve_pairs": [
        {
            "parent": parent,
            "parent_human_bone_index": parent_index,
            "child": child,
            "child_human_bone_index": child_index,
            "factor": factor,
            "factor_offset": factor_offset,
        }
        for parent, parent_index, child, child_index, factor, factor_offset
        in _ENDFIELD_TWIST_SOLVE_PAIRS
    ],
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

GROUNDING_RUNTIME_POLICY = {
    "status": (
        "source_closed_quality3_ordinary_and_rotated_root_aligned_base_paths_"
        "shared_prediction_and_capsule_redirects_open_not_implemented"
    ),
    "field_offsets": {
        "rotateSolver": "Grounding+0x9C",
        "isAccelerating": "Grounding+0x3D",
    },
    "rvas": {
        "grounder_on_solver_update": "0x326EB70",
        "grounding_update": "0x326D370",
        "grounding_leg_process": "0x3277FD0",
        "grounding_get_root_hit": "0x32701C0",
        "grounding_leg_raycast": "0x32028C0",
        "grounding_leg_capsule": "0x3913000",
        "grounding_pelvis_process": "0x326B180",
        "grounding_leg_final_set_ik_position": "0x326BDB0",
        "grounder_set_leg_ik": "0x326CB90",
        "grounding_get_up": "0x3269FA0",
        "grounding_get_use_root_rotation": "0x326A000",
    },
    "frame_order": [
        "restore_authored_pelvis_to_prevent_accumulation",
        "grounding_update_when_weight_gt_0_01_else_invalid_frame",
        "root_hit_then_left_right_leg_process",
        "aggregate_offsets_and_grounded_state",
        "pelvis_process",
        "final_leg_length_clamp",
        "authored_procedural_set_leg_ik_blend",
    ],
    "position_request_formula": (
        "lerp(authoredIKFootBone.position,leg.IKPosition,"
        "clamp(weight*maintianPelvisFootWeight,0,1))"
    ),
    "limb_position_weight": "footAdsorbWeight",
    "pelvis_formula": (
        "Vector3.up*heightOffset+(root.rotation*Vector3.forward)*forwardOffset"
    ),
    "rotated_root_aligned_path": {
        "status": "source_closed_base_path_runtime_not_implemented",
        "actors": ["chr_0005_chen", "chr_0032_lizhiyan"],
        "gate": "rotateSolver_at_Grounding+0x9C",
        "world_up_rejoin_epsilon_squared": 9.99999944e-11,
        "basis": {
            "up": "root.up",
            "forward": "root.rotation*Vector3.forward",
            "right": "normalize(cross(root.up,forward))",
            "vertical": "(inverse(root.rotation)*(A-B)).y",
        },
        "pelvis_formula": (
            "root.up*heightOffset+(root.rotation*Vector3.forward)*forwardOffset"
        ),
        "common_final_stages": ["FinalSetIKPosition", "SetLegIK"],
    },
    "queries": {
        "quality3_root_and_foot": "Raycast_delegate_Grounding+0x128",
        "foot_volume": "CapsuleCast_delegate_Grounding+0x130",
        "trigger_interaction": "Ignore_1",
        "delegate_installer": "Grounding_ctor_0x4407F80",
        "default_delegate_targets": {
            "raycast": "0x2F61D50",
            "capsule_cast": "0xB423C98",
            "sphere_cast": "0x3730420",
        },
        "runtime_layer_owner": (
            "CharacterAnimationComponent.OnAnimationSetup_0x37881A0_reads_"
            "DataManager.movementSetting+0x40_MovementSetting._ikLayers_"
            "and_overwrites_Grounding+0x68"
        ),
        "layer_override_rva": "0x3787330",
        "serialized_grounder_layer_mask_runtime_authoritative": False,
        "active_movement_setting_ik_layers_recovered": True,
        "active_movement_setting_ik_layers_decimal": 0x00300000,
        "active_movement_setting_ik_layers_hex": "0x00300000",
        "active_movement_setting_layers": ["Terrain", "IK"],
        "installed_settings_with_exact_mask": [
            "MovementSetting_Default",
            "MovementSetting_Aglina",
        ],
        "movement_setting_modifiers_can_override_layer_mask": False,
        "source_compatible_terrain_query_provider_recovered": False,
        "collider_acceptance": {
            "root": "valid_ECSColliderResultProxy_required",
            "foot_ray": "valid_ECS_tuple_or_resolved_live_Unity_Collider",
            "capsule": "no_independent_ECS_proxy_gate_proven",
            "ecs_collider_is_valid_rva": "0x32052C0",
        },
    },
    "missing_ground_fallback": (
        "foot_xz_from_requested_heel_y_from_leg_minus_rootYOffset_normal_rootUp"
    ),
    "unsupported_modes": [
        "quality_not_3",
        "overstepFallsDown_false",
        "full_predictive_step_state_machine",
        "exact_capsule_no_hit_correction",
    ],
    "original_component_audit": {
        "actor_count": 31,
        "quality3_count": 31,
        "nonrotated_ordinary_count": 28,
        "rotated_root_aligned_count": 3,
        "rotated_root_aligned_actors": [
            "chr_0005_chen",
            "chr_0032_lizhiyan",
            "chr_0035_liino",
        ],
        "late_recovered_grounders": [
            "chr_0032_lizhiyan",
            "chr_0033_camille",
            "chr_0035_liino",
        ],
        "all_overstep_falls_down": True,
        "all_foot_adsorb_weight": 1.0,
        "all_prediction": 0.0,
        "serialized_zero_layer_mask_actors": ["chr_0018_dapan", "chr_0024_deepfin"],
        "runtime_layer_source": "MovementSetting._ikLayers_via_OnAnimationSetup",
        "active_runtime_layer_mask": 0x00300000,
        "active_runtime_layer_names": ["Terrain", "IK"],
        "nonunit_overall_weight": {"chr_0021_whiten": 0.348},
    },
}


def _extension_muscle_binding(slot: int) -> dict[str, Any]:
    human_bone, human_bone_index, selector, minimum, maximum = (
        _ENDFIELD_EXTENSION_MUSCLE_BINDINGS[slot]
    )
    return {
        "human_bone": human_bone,
        "human_bone_index": human_bone_index,
        "selector": selector,
        "default_min_radians": minimum,
        "default_max_radians": maximum,
    }


def normalize_endfield_humanoid_layout(layout: Any) -> dict[str, Any]:
    """Upgrade cached pre-recovery 101-slot metadata without rewriting samples."""

    if not isinstance(layout, dict):
        return {}
    result = dict(layout)
    if result.get("layout") != "endfield_101_muscle_206_index":
        return result

    extension_slots = list(_ENDFIELD_EXTENSION_MUSCLE_NAMES)
    mapped_attributes: list[dict[str, Any]] = []
    for source_row in result.get("mapped_attributes") or []:
        if not isinstance(source_row, dict):
            continue
        row = dict(source_row)
        muscle_slot = row.get("muscle_slot")
        if isinstance(muscle_slot, int) and 0 <= muscle_slot < 101:
            if muscle_slot in _ENDFIELD_EXTENSION_MUSCLE_NAMES:
                row["category"] = "endfield_humanoid_extension"
                row["semantic"] = _ENDFIELD_EXTENSION_MUSCLE_NAMES[muscle_slot]
                row.update(_extension_muscle_binding(muscle_slot))
                row["avatar_axis_formula"] = (
                    "preQ * FromAxes_ZYRoll(selector_angles) * inverse(postQ)"
                )
                row["mapping_status"] = (
                    "binary_selector_and_exact_avatar_axis_record_recovered_"
                    "pinned_runtime_bake_oracle_recovered_not_integrated"
                )
                row.pop("unity_muscle_slot", None)
            else:
                unity_slot = muscle_slot - sum(
                    1 for extension_slot in extension_slots
                    if extension_slot < muscle_slot
                )
                row["category"] = "unity_humanoid_muscle"
                row["semantic"] = f"UnityHumanoidMuscle[{unity_slot}]"
                row["unity_muscle_slot"] = unity_slot
                row["mapping_status"] = "shifted_slot_preserved_avatar_mapping_required"
        mapped_attributes.append(row)

    mapped_extension_slots = sorted(
        int(row["muscle_slot"])
        for row in mapped_attributes
        if row.get("category") == "endfield_humanoid_extension"
    )
    result["endfield_extension_slots"] = extension_slots
    result["endfield_extension_names"] = {
        str(slot): _ENDFIELD_EXTENSION_MUSCLE_NAMES[slot]
        for slot in extension_slots
    }
    result["endfield_extension_bindings"] = {
        str(slot): _extension_muscle_binding(slot)
        for slot in extension_slots
    }
    result["native_evidence"] = dict(_ENDFIELD_HUMANOID_NATIVE_EVIDENCE)
    result["mapped_endfield_extension_slots"] = mapped_extension_slots
    result["unmapped_endfield_extension_slots"] = sorted(
        set(extension_slots) - set(mapped_extension_slots)
    )
    if mapped_attributes:
        result["mapped_attributes"] = mapped_attributes
    result["retarget_status"] = (
        "exact_playable_avatar_referentials_and_pinned_original_pose_oracle_"
        "recovered_runtime_transform_bake_not_integrated"
    )
    return result


def load_acl_sample_summary(path: Path) -> dict[str, Any]:
    text = _json_without_top_level_field(path, "frames").strip()
    summary = json.loads(text) if text else {}
    if "humanoid_layout" in summary:
        summary["humanoid_layout"] = normalize_endfield_humanoid_layout(
            summary.get("humanoid_layout")
        )
    return summary


def load_acl_sample_tail_metadata(path: Path) -> dict[str, Any]:
    file_size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(max(0, file_size - 65536))
        text = handle.read().decode("utf-8", errors="ignore")
    metadata: dict[str, Any] = {}
    for key in ("clip_name", "buffer_name", "source_json", "source_acl"):
        match = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"])*)"', text)
        if match:
            metadata[key] = json.loads(f'"{match.group(1)}"')
    layout_match = re.search(r'"humanoid_layout"\s*:\s*', text)
    if layout_match:
        try:
            layout, _ = json.JSONDecoder().raw_decode(text[layout_match.end() :])
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(layout, dict):
                metadata["humanoid_layout"] = normalize_endfield_humanoid_layout(layout)
    return metadata


_QVVF_TRACK_PATTERN = re.compile(
    r'\{\s*"rotation"\s*:\s*\[(?P<rotation>[^\]]*)\]\s*,\s*'
    r'"translation"\s*:\s*\[(?P<translation>[^\]]*)\]\s*,\s*'
    r'"scale"\s*:\s*\[(?P<scale>[^\]]*)\]\s*\}',
)
_QVVF_SCAN_CHUNK_SIZE = 1024 * 1024
_QVVF_MAX_PENDING_TEXT = 2 * 1024 * 1024


def _sample_vector(text: str, expected_size: int, field_name: str) -> tuple[float, ...]:
    try:
        values = tuple(float(item.strip()) for item in text.split(","))
    except ValueError as exc:
        raise ValueError(f"invalid {field_name} values in qvvf sample") from exc
    if len(values) != expected_size or not all(math.isfinite(value) for value in values):
        raise ValueError(f"invalid {field_name} vector in qvvf sample: expected {expected_size} finite values")
    return values


def iter_qvvf_sample_tracks(path: Path):
    """Yield decoded qvvf tracks without loading a potentially huge sample JSON.

    Both the native ACL sampler and ``export_actor_samples.py`` keep each track
    object in rotation/translation/scale order.  The latter pretty-prints those
    objects, so this scanner deliberately accepts whitespace and newlines.
    """

    pending = ""
    with path.open("r", encoding="utf-8") as handle:
        while True:
            chunk = handle.read(_QVVF_SCAN_CHUNK_SIZE)
            if not chunk:
                break
            pending += chunk
            consumed = 0
            for match in _QVVF_TRACK_PATTERN.finditer(pending):
                yield {
                    "rotation": _sample_vector(match.group("rotation"), 4, "rotation"),
                    "translation": _sample_vector(match.group("translation"), 3, "translation"),
                    "scale": _sample_vector(match.group("scale"), 3, "scale"),
                }
                consumed = match.end()
            if consumed:
                pending = pending[consumed:]
            if len(pending) > _QVVF_MAX_PENDING_TEXT:
                raise ValueError(f"qvvf track schema was not recognized while scanning {path}")


def _vectors_differ(
    left: tuple[float, ...] | list[float],
    right: tuple[float, ...] | list[float],
    *,
    abs_tol: float,
    rel_tol: float,
) -> bool:
    if len(left) != len(right):
        return True
    return any(
        not math.isclose(float(a), float(b), abs_tol=abs_tol, rel_tol=rel_tol)
        for a, b in zip(left, right)
    )


def _normalized_quaternion(value: tuple[float, ...] | list[float]) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise ValueError("quaternion must contain four values")
    length = math.sqrt(sum(float(item) * float(item) for item in value))
    if not math.isfinite(length) or length <= 1e-12:
        raise ValueError("qvvf sample contains an invalid zero quaternion")
    return (
        float(value[0]) / length,
        float(value[1]) / length,
        float(value[2]) / length,
        float(value[3]) / length,
    )


def _quaternions_differ(
    left: tuple[float, ...] | list[float],
    right: tuple[float, ...] | list[float],
    *,
    dot_tol: float,
) -> bool:
    left_normalized = _normalized_quaternion(left)
    right_normalized = _normalized_quaternion(right)
    dot = abs(sum(a * b for a, b in zip(left_normalized, right_normalized)))
    return 1.0 - min(1.0, dot) > dot_tol


def analyze_qvvf_sample_channels(
    path: Path,
    expected_track_count: int,
    expected_frame_count: int = 0,
) -> dict[str, Any]:
    """Measure per-track qvvf variation directly from decoded sample frames."""

    if expected_track_count <= 0:
        raise ValueError("qvvf sample has no expected transform tracks")

    tracks: list[dict[str, Any] | None] = [None] * expected_track_count
    value_count = 0
    for value in iter_qvvf_sample_tracks(path):
        track_index = value_count % expected_track_count
        track = tracks[track_index]
        if track is None:
            tracks[track_index] = {
                "first_position": value["translation"],
                "first_rotation": value["rotation"],
                "first_scale": value["scale"],
                "position_varies": False,
                "rotation_varies": False,
                "scale_varies": False,
            }
        else:
            track["position_varies"] = bool(track["position_varies"]) or _vectors_differ(
                value["translation"],
                track["first_position"],
                abs_tol=1e-7,
                rel_tol=1e-7,
            )
            track["rotation_varies"] = bool(track["rotation_varies"]) or _quaternions_differ(
                value["rotation"],
                track["first_rotation"],
                dot_tol=1e-8,
            )
            track["scale_varies"] = bool(track["scale_varies"]) or _vectors_differ(
                value["scale"],
                track["first_scale"],
                abs_tol=1e-7,
                rel_tol=1e-7,
            )
        value_count += 1

    if value_count == 0:
        raise ValueError(f"qvvf sample contains no transform frames: {path}")
    if value_count % expected_track_count != 0:
        raise ValueError(
            f"qvvf sample track count mismatch: decoded {value_count} values for "
            f"{expected_track_count} tracks"
        )
    frame_count = value_count // expected_track_count
    if expected_frame_count > 0 and frame_count != expected_frame_count:
        raise ValueError(
            f"qvvf sample frame count mismatch: decoded {frame_count}, expected {expected_frame_count}"
        )
    if any(track is None for track in tracks):
        raise ValueError("qvvf sample did not provide every transform track")

    return {
        "track_count": expected_track_count,
        "frame_count": frame_count,
        "tracks": tracks,
    }


def apply_qvvf_channel_evidence(
    info: dict[str, Any],
    channel_analysis: dict[str, Any],
    transforms_by_crc: dict[int, dict[str, Any]],
) -> None:
    """Resolve which decoded qvvf channels require curves in Unity.

    ``*_animated`` means that a curve must be emitted, not merely that the
    channel varies over time.  A constant ACL channel still needs a curve when
    its decoded value overrides the recovered hierarchy's local bind value.
    An ACL default sub-track is omitted because the debug sampler necessarily
    expands it to identity instead of Unity's per-transform hierarchy default.
    """

    bones = info.get("bones") or []
    tracks = channel_analysis.get("tracks") or []
    expected_track_count = int(info.get("transform_track_count") or 0)
    if int(channel_analysis.get("track_count") or 0) != expected_track_count:
        raise ValueError(
            "qvvf binding/sample track count mismatch: "
            f"bindings={expected_track_count}, samples={channel_analysis.get('track_count')}"
        )

    channel_specs = {
        "pos": ("position", "local_pos", False),
        "rot": ("rotation", "local_rot", True),
        "scale": ("scale", "local_scale", False),
    }
    for bone in bones:
        track_index = bone.get("track_index")
        if track_index is None or int(track_index) < 0 or int(track_index) >= len(tracks):
            raise ValueError(f"invalid qvvf track index for binding {bone.get('path_crc')}: {track_index}")
        track = tracks[int(track_index)]
        if not isinstance(track, dict):
            raise ValueError(f"missing qvvf evidence for track {track_index}")
        hierarchy_transform = transforms_by_crc.get(int(bone.get("path_crc") or 0))

        for manifest_prefix, (sample_prefix, hierarchy_key, is_rotation) in channel_specs.items():
            binding_indices = bone.get(f"_{manifest_prefix}_binding_indices") or []
            required = False
            if binding_indices:
                varies = bool(track.get(f"{sample_prefix}_varies"))
                if varies:
                    # Decoded variation is authoritative even if malformed ACL
                    # metadata also claims that every corresponding binding is
                    # a default sub-track.
                    required = True
                elif bool(bone.get(f"_{manifest_prefix}_uses_default")):
                    required = False
                elif hierarchy_transform is None:
                    # Without a recovered bind value, retaining the constant is
                    # safer than silently discarding a possible pose override.
                    required = True
                else:
                    sampled_value = track.get(f"first_{sample_prefix}")
                    hierarchy_value = hierarchy_transform.get(hierarchy_key)
                    if sampled_value is None or hierarchy_value is None:
                        required = True
                    elif is_rotation:
                        required = _quaternions_differ(
                            sampled_value,
                            hierarchy_value,
                            dot_tol=1e-8,
                        )
                    else:
                        required = _vectors_differ(
                            sampled_value,
                            hierarchy_value,
                            abs_tol=1e-5,
                            rel_tol=1e-5,
                        )
            bone[f"{manifest_prefix}_animated"] = required


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def ref_path_id(ref: dict[str, Any] | None) -> int:
    if not ref:
        return 0
    return int(ref.get("m_PathID") or 0)


def exported_json_path(directory: Path, asset_name: str, path_id: int) -> Path:
    """Resolve both legacy exact-name and current AnimeStudio path-id JSON names."""

    exact = directory / f"{asset_name}.json"
    if exact.is_file():
        return exact
    path_suffix = f"{path_id & 0xFFFFFFFFFFFFFFFF:016X}"
    path_named = directory / f"{asset_name}_p{path_suffix}.json"
    if path_named.is_file():
        return path_named
    return exact


def is_vfx_mesh_name(name: str) -> bool:
    lowered = name.lower()
    return "vfxpart" in lowered or "vfxbody" in lowered


def exact_lastrite_unsupported_white_fallback(
    mesh_name: str,
    mesh_path_id: int,
    material_path_ids: tuple[int, ...],
) -> dict[str, Any] | None:
    if ACTOR_TOKEN.casefold() != "lastrite":
        return None
    evidence = LASTRITE_UNSUPPORTED_WHITE_FALLBACKS.get(
        (mesh_name, mesh_path_id, material_path_ids)
    )
    if evidence is None:
        return None
    return {
        "name": mesh_name,
        "mesh_path_id": mesh_path_id,
        "material_path_ids": list(material_path_ids),
        "action": "excluded_from_generated_prefab_fail_closed",
        **evidence,
    }


def crc32_unity_path(path: str) -> int:
    try:
        payload = path.encode("ascii")
    except UnicodeEncodeError:
        payload = path.encode("utf-8")
    return zlib.crc32(payload) & 0xFFFFFFFF


def vec3(value: dict[str, Any] | None) -> list[float]:
    value = value or {}
    return [float(value.get(axis, 0.0)) for axis in ("X", "Y", "Z")]


def quat(value: dict[str, Any] | None) -> list[float]:
    value = value or {}
    return [
        float(value.get("X", 0.0)),
        float(value.get("Y", 0.0)),
        float(value.get("Z", 0.0)),
        float(value.get("W", 1.0)),
    ]


def color(value: dict[str, Any] | None) -> list[float] | None:
    if not value:
        return None
    return [
        float(value.get("r", 1.0)),
        float(value.get("g", 1.0)),
        float(value.get("b", 1.0)),
        float(value.get("a", 1.0)),
    ]


def transform_id(game_object: dict[str, Any]) -> int:
    components = game_object.get("m_Components") or []
    if not components:
        raise ValueError(f"GameObject has no components: {game_object.get('m_Name')}")
    return int(components[0]["m_PathID"])


def select_hierarchy_root_id(by_transform_id: dict[int, dict[str, Any]]) -> int:
    """Select the actual postmodel graph when canonical extraction contains wrappers.

    Endfield can export both the NPC and character postmodel entries into the
    same hierarchy directory.  Some entries are parentless Animator wrappers
    whose only child repeats ``ROOT_POSTMODEL_NAME``.  The graph consumed by
    this manifest has direct ``Mesh_all`` and skeleton ``Root`` children.
    Prefer that structure, then its parentless Animator-owned form, and fail
    rather than silently choosing between equally valid source graphs.
    """

    candidates = [
        (tid, data)
        for tid, data in by_transform_id.items()
        if data.get("m_Name") == ROOT_POSTMODEL_NAME
    ]
    if not candidates:
        raise SystemExit(f"missing {ROOT_POSTMODEL_NAME} in {HIERARCHY_DIR}")

    def candidate_score(data: dict[str, Any]) -> tuple[int, int, int]:
        transform = data.get("m_Transform") or {}
        child_names = {
            str(by_transform_id[child_id].get("m_Name") or "")
            for child in transform.get("m_Children") or []
            if (child_id := ref_path_id(child)) in by_transform_id
        }
        has_postmodel_children = {"Mesh_all", "Root"}.issubset(child_names)
        is_parentless = ref_path_id(transform.get("m_Father")) == 0
        owns_animator = bool(data.get("m_Animator"))
        return int(has_postmodel_children), int(is_parentless), int(owns_animator)

    scored = [(candidate_score(data), tid) for tid, data in candidates]
    best_score = max(score for score, _ in scored)
    best_ids = [tid for score, tid in scored if score == best_score]
    if len(best_ids) != 1:
        raise SystemExit(
            f"ambiguous {ROOT_POSTMODEL_NAME} hierarchy roots at score {best_score}: "
            + ", ".join(str(tid) for tid in sorted(best_ids))
        )
    return best_ids[0]


def load_hierarchy() -> tuple[list[dict[str, Any]], dict[int, str], dict[str, dict[str, Any]]]:
    by_transform_id: dict[int, dict[str, Any]] = {}
    for path in HIERARCHY_DIR.glob("*.json"):
        data = load_json(path)
        by_transform_id[transform_id(data)] = data

    root_id = select_hierarchy_root_id(by_transform_id)

    transforms: list[dict[str, Any]] = []
    id_to_path: dict[int, str] = {}
    path_to_data: dict[str, dict[str, Any]] = {}

    def visit(tid: int, parent_path: str) -> None:
        data = by_transform_id[tid]
        name = str(data.get("m_Name") or "")
        path = name if not parent_path else f"{parent_path}/{name}"
        transform = data.get("m_Transform") or {}
        item = {
            "name": name,
            "path": path,
            "parent_path": parent_path,
            "path_crc": crc32_unity_path(path),
            "path_id": tid,
            "game_object_path_id": ref_path_id(transform.get("m_GameObject")),
            "local_pos": vec3(transform.get("m_LocalPosition")),
            "local_rot": quat(transform.get("m_LocalRotation")),
            "local_scale": vec3(transform.get("m_LocalScale")),
            "has_skinned_mesh_renderer": bool(data.get("m_SkinnedMeshRenderer")),
        }
        transforms.append(item)
        id_to_path[tid] = path
        path_to_data[path] = data
        for child in transform.get("m_Children") or []:
            child_id = ref_path_id(child)
            if child_id in by_transform_id:
                visit(child_id, path)

    root_transform = by_transform_id[root_id].get("m_Transform") or {}
    for child in root_transform.get("m_Children") or []:
        child_id = ref_path_id(child)
        if child_id in by_transform_id:
            visit(child_id, "")

    if len({t["path"] for t in transforms}) != len(transforms):
        raise SystemExit("postmodel hierarchy contains duplicate relative paths")

    return transforms, id_to_path, path_to_data


def load_asset_entries() -> tuple[dict[tuple[str, int], list[dict[str, Any]]], list[dict[str, Any]]]:
    all_entries: list[dict[str, Any]] = []
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for map_path in ASSET_MAPS:
        if not map_path.is_file():
            continue
        source_root = map_path.parents[1].name
        for entry in load_json(map_path).get("AssetEntries") or []:
            entry = dict(entry)
            entry["_asset_root"] = source_root
            all_entries.append(entry)
            by_type_path_id[(str(entry.get("Type")), int(entry.get("PathID")))].append(entry)
    return by_type_path_id, all_entries


def pick_asset(by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]], asset_type: str, path_id: int) -> dict[str, Any] | None:
    candidates = by_type_path_id.get((asset_type, int(path_id)), [])
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            0 if item.get("_asset_root") == "StreamingAssets" else 1,
            0 if "_p" not in str(item.get("Name")) else 1,
            len(str(item.get("Container") or "")),
        ),
    )[0]


def find_exported_asset_file(root: Path, asset_type: str, name: str, extensions: tuple[str, ...]) -> str:
    folder = root / "convert_by_type" / asset_type
    if not folder.is_dir() or not name:
        return ""
    for ext in extensions:
        direct = folder / f"{name}{ext}"
        if direct.is_file():
            return str(direct.resolve())
    for ext in extensions:
        matches = sorted(folder.glob(f"{name}_p*{ext}"))
        if matches:
            return str(matches[0].resolve())
    return ""


def find_json_by_type(asset_type: str, name: str) -> Path | None:
    if not name:
        return None
    for root in (STREAMING, PERSISTENT):
        folder = root / "json_by_type" / asset_type
        direct = folder / f"{name}.json"
        if direct.is_file():
            return direct
        matches = sorted(folder.glob(f"{name}_p*.json"))
        if matches:
            return matches[0]
    return None


def find_json_by_type_path_id(asset_type: str, path_id: int) -> Path | None:
    """Resolve renamed/hashed AssetMap rows by AnimeStudio's stable ID suffix."""

    if path_id == 0:
        return None
    suffix = f"_p{path_id & 0xFFFFFFFFFFFFFFFF:016X}.json"
    for root in (STREAMING, PERSISTENT):
        folder = root / "json_by_type" / asset_type
        if not folder.is_dir():
            continue
        matches = sorted(folder.glob(f"*{suffix}"))
        if matches:
            return matches[0]
    return None


def texture_info(
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    tex_ref: dict[str, Any] | None,
) -> dict[str, Any] | None:
    texture_path_id = ref_path_id((tex_ref or {}).get("m_Texture"))
    if texture_path_id == 0:
        return None
    asset = pick_asset(by_type_path_id, "Texture2D", texture_path_id)
    name = str((asset or {}).get("Name") or f"Texture2D_{texture_path_id}")
    source_root = STREAMING if (asset or {}).get("_asset_root") == "StreamingAssets" else PERSISTENT
    exported = find_exported_asset_file(source_root, "Texture2D", name, (".png", ".tga", ".jpg", ".jpeg"))
    if not exported and source_root is not STREAMING:
        exported = find_exported_asset_file(STREAMING, "Texture2D", name, (".png", ".tga", ".jpg", ".jpeg"))
    if not exported and source_root is not PERSISTENT:
        exported = find_exported_asset_file(PERSISTENT, "Texture2D", name, (".png", ".tga", ".jpg", ".jpeg"))
    scale = (tex_ref or {}).get("m_Scale") or {}
    offset = (tex_ref or {}).get("m_Offset") or {}
    return {
        "name": name,
        "path_id": texture_path_id,
        "container": (asset or {}).get("Container", ""),
        "asset_root": (asset or {}).get("_asset_root", ""),
        "file": exported,
        # Texture scale/offset is part of the serialized Material input, not
        # Texture2D metadata.  Keeping it beside the recovered PPtr is needed
        # for authored high-frequency inputs such as Li Zhiyan's 40x fur noise
        # map and 1x2 refraction normal.
        "scale": [
            float(scale.get("X", scale.get("x", 1.0)) or 0.0),
            float(scale.get("Y", scale.get("y", 1.0)) or 0.0),
        ],
        "offset": [
            float(offset.get("X", offset.get("x", 0.0)) or 0.0),
            float(offset.get("Y", offset.get("y", 0.0)) or 0.0),
        ],
    }


def normalize_unity_property_map(value: Any) -> dict[str, Any]:
    """Accept both Unity/AnimeStudio maps and Force-Text single-key lists.

    RuriRipperImporter exposed a useful serialization boundary here: Unity
    Force Text commonly writes m_TexEnvs/m_Colors/m_Floats as a list of
    single-key mappings, while AnimeStudio/AssetRipper JSON may use one object.
    Treating only the latter as canonical silently drops material dependencies.
    """

    if isinstance(value, dict):
        return dict(value)
    result: dict[str, Any] = {}
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                result.update(entry)
    return result


_EXACT_MATERIAL_STATE_FIELDS = (
    "m_ShaderKeywords",
    "m_ValidKeywords",
    "m_InvalidKeywords",
    "m_LightmapFlags",
    "m_EnableInstancingVariants",
    "m_CustomRenderQueue",
    "m_StringTagMap",
    "m_DisabledShaderPasses",
)


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a JSON array")
    return [str(item) for item in value]


def original_material_state(
    data: dict[str, Any],
    *,
    require_exact: bool = False,
) -> dict[str, Any]:
    """Recover Material fields serialized outside m_SavedProperties.

    Old AnimeStudio exports omitted all of these fields. A partial set is not
    accepted because it cannot be distinguished from a stale exporter build.
    """

    present = {field for field in _EXACT_MATERIAL_STATE_FIELDS if field in data}
    if not present and not require_exact:
        return {}
    missing = sorted(set(_EXACT_MATERIAL_STATE_FIELDS) - present)
    if missing:
        raise ValueError(
            "Material exact serialized state is incomplete; missing "
            + ", ".join(missing)
        )
    tags = data["m_StringTagMap"]
    if not isinstance(tags, dict):
        raise ValueError("m_StringTagMap must be a JSON object")
    legacy_keywords = data["m_ShaderKeywords"]
    if legacy_keywords is not None and not isinstance(legacy_keywords, (str, list)):
        raise ValueError("m_ShaderKeywords must be null, a string, or an array")
    return {
        "source_serialized_state": True,
        "custom_render_queue": int(data["m_CustomRenderQueue"]),
        "valid_keywords": _string_list(data["m_ValidKeywords"], "m_ValidKeywords"),
        "invalid_keywords": _string_list(data["m_InvalidKeywords"], "m_InvalidKeywords"),
        "legacy_shader_keywords": legacy_keywords,
        "disabled_shader_passes": _string_list(
            data["m_DisabledShaderPasses"], "m_DisabledShaderPasses"
        ),
        "string_tag_map": {
            str(key): str(value) for key, value in sorted(tags.items())
        },
        "enable_instancing_variants": bool(data["m_EnableInstancingVariants"]),
        "lightmap_flags": int(data["m_LightmapFlags"]),
        "fail_closed_unknown_shader": True,
    }


_RENDERER_STATE_FIELDS: tuple[tuple[str, str, type], ...] = (
    ("enabled", "m_Enabled", bool),
    ("cast_shadows", "m_CastShadows", int),
    ("receive_shadows", "m_ReceiveShadows", int),
    ("dynamic_occludee", "m_DynamicOccludee", int),
    ("static_shadow_caster", "m_StaticShadowCaster", int),
    ("realtime_shadow_caster", "m_RealtimeShadowCaster", int),
    ("sub_mesh_render_mode", "m_SubMeshRenderMode", int),
    ("character_index", "m_CharacterIndex", int),
    ("motion_vectors", "m_MotionVectors", int),
    ("light_probe_usage", "m_LightProbeUsage", int),
    ("reflection_probe_usage", "m_ReflectionProbeUsage", int),
    ("ray_tracing_mode", "m_RayTracingMode", int),
    ("ray_trace_procedural", "m_RayTraceProcedural", int),
    ("render_foliage_occluder", "m_RenderFoliageOccluder", int),
    ("platform_specific_cast_shadows", "m_PlatformSpecificCastShadows", int),
    ("rendering_layer_mask", "m_RenderingLayerMask", int),
    ("renderer_priority", "m_RendererPriority", int),
    ("lightmap_index", "m_LightmapIndex", int),
    ("lightmap_index_dynamic", "m_LightmapIndexDynamic", int),
    ("sorting_layer_id", "m_SortingLayerID", int),
    ("sorting_layer", "m_SortingLayer", int),
    ("sorting_order", "m_SortingOrder", int),
    ("enable_character_outline", "m_EnableCharacterOutline", bool),
    ("enable_per_renderer_lighting", "m_EnablePerRendererLighting", bool),
    ("light_mode_mask", "m_LightModeMask", int),
    ("renderer_sorting_fudge", "m_RendererSortingFudge", float),
    ("skinned_quality", "m_Quality", int),
    ("update_when_offscreen", "m_UpdateWhenOffscreen", bool),
    ("skin_normals", "m_SkinNormals", bool),
)

_EXACT_RENDERER_STATE_FIELDS = tuple(
    source_name
    for _, source_name, _ in _RENDERER_STATE_FIELDS
    if not source_name.startswith("m_Quality")
    and source_name not in {"m_UpdateWhenOffscreen", "m_SkinNormals"}
) + (
    "m_LightmapTilingOffset",
    "m_LightmapTilingOffsetDynamic",
    "m_StaticBatchInfo",
    "m_SubsetIndices",
    "m_StaticBatchRoot",
    "m_ProbeAnchor",
    "m_LightProbeVolumeOverride",
    "m_ShadowProxyMesh",
    "m_PerRendererLightingOffset",
    "m_PerRendererLightingAnchor",
)

_EXACT_SKINNED_RENDERER_FIELDS = (
    "m_Quality",
    "m_UpdateWhenOffscreen",
    "m_SkinNormals",
    "m_Mesh",
    "m_Bones",
    "m_BlendShapeWeights",
    "m_RootBone",
    "m_SkinningRoot",
    "m_AABB",
    "m_DirtyAABB",
)


def _pptr_state(
    value: Any,
    *,
    field_name: str,
    hierarchy_paths: dict[int, str] | None = None,
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]] | None = None,
    asset_type: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a PPtr JSON object")
    path_id = ref_path_id(value)
    result = {
        "file_id": int(value.get("m_FileID") or 0),
        "path_id": path_id,
        "name": str(value.get("Name") or ""),
        "is_null": bool(value.get("IsNull", path_id == 0)),
    }
    if path_id == 0:
        return result
    if hierarchy_paths is not None:
        path = hierarchy_paths.get(path_id, "")
        if not path:
            raise ValueError(
                f"{field_name} PathID {path_id} is outside the recovered hierarchy"
            )
        result["path"] = path
    if asset_type is not None:
        asset = pick_asset(by_type_path_id or {}, asset_type, path_id)
        if asset is None:
            raise ValueError(
                f"{field_name} {asset_type} PathID {path_id} is absent from the exact asset map"
            )
        result.update(
            {
                "name": str(asset.get("Name") or result["name"]),
                "container": str(asset.get("Container") or ""),
                "asset_root": str(asset.get("_asset_root") or ""),
            }
        )
    return result


def original_renderer_state(
    source_renderer: dict[str, Any],
    id_to_path: dict[int, str],
    game_object_id_to_path: dict[int, str],
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    *,
    require_exact: bool = False,
) -> dict[str, Any]:
    """Recover the complete Endfield SkinnedMeshRenderer serialized state."""

    required = set(_EXACT_RENDERER_STATE_FIELDS) | set(
        _EXACT_SKINNED_RENDERER_FIELDS
    )
    present = {field for field in required if field in source_renderer}
    if not present and not require_exact:
        return {}
    missing = sorted(required - present)
    if missing:
        raise ValueError(
            "SkinnedMeshRenderer exact serialized state is incomplete; missing "
            + ", ".join(missing)
        )

    state: dict[str, Any] = {"source_serialized_state": True}
    for output_name, source_name, converter in _RENDERER_STATE_FIELDS:
        state[output_name] = converter(source_renderer[source_name])
    state["per_renderer_lighting_offset"] = vec3(
        source_renderer["m_PerRendererLightingOffset"]
    )
    state["lightmap_tiling_offset"] = vec4(
        source_renderer["m_LightmapTilingOffset"]
    )
    state["lightmap_tiling_offset_dynamic"] = vec4(
        source_renderer["m_LightmapTilingOffsetDynamic"]
    )
    state["per_renderer_lighting_anchor_path_id"] = ref_path_id(
        source_renderer["m_PerRendererLightingAnchor"]
    )
    anchor = _pptr_state(
        source_renderer["m_PerRendererLightingAnchor"],
        field_name="m_PerRendererLightingAnchor",
        hierarchy_paths=id_to_path,
    )
    state["per_renderer_lighting_anchor_path"] = str(anchor.get("path") or "")
    state["static_batch_root"] = _pptr_state(
        source_renderer["m_StaticBatchRoot"],
        field_name="m_StaticBatchRoot",
        hierarchy_paths=id_to_path,
    )
    state["probe_anchor"] = _pptr_state(
        source_renderer["m_ProbeAnchor"],
        field_name="m_ProbeAnchor",
        hierarchy_paths=id_to_path,
    )
    state["light_probe_volume_override"] = _pptr_state(
        source_renderer["m_LightProbeVolumeOverride"],
        field_name="m_LightProbeVolumeOverride",
        hierarchy_paths=game_object_id_to_path,
    )
    state["shadow_proxy_mesh"] = _pptr_state(
        source_renderer["m_ShadowProxyMesh"],
        field_name="m_ShadowProxyMesh",
        by_type_path_id=by_type_path_id,
        asset_type="Mesh",
    )
    state["skinning_root"] = _pptr_state(
        source_renderer["m_SkinningRoot"],
        field_name="m_SkinningRoot",
        hierarchy_paths=id_to_path,
    )
    static_batch = source_renderer["m_StaticBatchInfo"]
    if not isinstance(static_batch, dict):
        raise ValueError("m_StaticBatchInfo must be a JSON object")
    state["static_batch_info"] = {
        "first_sub_mesh": int(static_batch.get("firstSubMesh") or 0),
        "sub_mesh_count": int(static_batch.get("subMeshCount") or 0),
    }
    subset_indices = source_renderer["m_SubsetIndices"]
    if subset_indices is None:
        state["subset_indices"] = None
    elif isinstance(subset_indices, list):
        state["subset_indices"] = [int(value) for value in subset_indices]
    else:
        raise ValueError("m_SubsetIndices must be null or a JSON array")
    blend_shape_weights = source_renderer["m_BlendShapeWeights"]
    if not isinstance(blend_shape_weights, list):
        raise ValueError("m_BlendShapeWeights must be a JSON array")
    state["blend_shape_weights"] = [
        float(value) for value in blend_shape_weights
    ]
    state["dirty_aabb"] = bool(source_renderer["m_DirtyAABB"])
    return state


def find_material_json(name: str, path_id: int) -> Path | None:
    """Prefer the actor-scoped exact Material export over broad stale JSON."""

    if MATERIAL_DIR is not None and Path(MATERIAL_DIR).is_dir() and path_id:
        suffix = f"_p{path_id & 0xFFFFFFFFFFFFFFFF:016X}.json"
        matches = sorted(Path(MATERIAL_DIR).glob(f"*{suffix}"))
        if len(matches) > 1:
            raise ValueError(
                f"Material PathID {path_id} has multiple actor-scoped JSON files in {MATERIAL_DIR}"
            )
        if matches:
            return matches[0]
    return find_json_by_type("Material", name) or find_json_by_type_path_id(
        "Material", path_id
    )


def material_info(
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    path_id: int,
    *,
    require_exact_serialized_state: bool = False,
) -> dict[str, Any]:
    asset = pick_asset(by_type_path_id, "Material", path_id)
    name = str((asset or {}).get("Name") or f"Material_{path_id}")
    json_path = find_material_json(name, path_id)
    shader_path_id = 0
    shader_asset: dict[str, Any] | None = None
    result: dict[str, Any] = {
        "name": name,
        "path_id": int(path_id),
        "container": (asset or {}).get("Container", ""),
        "asset_root": (asset or {}).get("_asset_root", ""),
        "json": str(json_path.resolve()) if json_path else "",
        "shader_path_id": 0,
        "shader_name": "",
        "base": "",
        "normal": "",
        "color": [1.0, 1.0, 1.0, 1.0],
        "alpha": False,
        "textures": {},
        "floats": {},
        "colors": {},
    }
    if not json_path:
        if require_exact_serialized_state:
            raise ValueError(
                f"Material PathID {path_id} has no exact actor-scoped source JSON"
            )
        return result

    data = load_json(json_path)
    result.update(
        original_material_state(
            data,
            require_exact=require_exact_serialized_state,
        )
    )
    result["name"] = str(data.get("m_Name") or data.get("Name") or name)
    shader_path_id = ref_path_id(data.get("m_Shader"))
    shader_asset = pick_asset(by_type_path_id, "Shader", shader_path_id)
    result["shader_path_id"] = shader_path_id
    result["shader_name"] = str((shader_asset or {}).get("Name") or "")
    props = data.get("m_SavedProperties") or {}
    tex_envs = normalize_unity_property_map(props.get("m_TexEnvs"))
    textures: dict[str, Any] = {}
    for key in sorted(tex_envs):
        info = texture_info(by_type_path_id, tex_envs.get(key))
        if info:
            textures[key] = info
    result["textures"] = textures
    result["base"] = str((
        textures.get("_BaseMap")
        or textures.get("_MainTex")
        or textures.get("_BaseColorMap")
        or textures.get("_BaseColorTex")
        or textures.get("_Albedo")
        or textures.get("_AlbedoMap")
        or textures.get("_DiffuseMap")
        or textures.get("_Diffuse")
        or textures.get("_DiffuseTex")
        or textures.get("_ColorTex")
        or {}
    ).get("file") or "")
    result["normal"] = str((
        textures.get("_SplitNormalMap")
        or textures.get("_BumpMap")
        or textures.get("_NormalMap")
        or textures.get("_NormalTex")
        or textures.get("_Normal")
        or {}
    ).get("file") or "")

    colors = normalize_unity_property_map(props.get("m_Colors"))
    result["color"] = color(
        colors.get("_BaseColor")
        or colors.get("_Color")
        or colors.get("_MainColor")
        or colors.get("_TintColor")
    ) or result["color"]
    result["colors"] = {key: value for key, raw in sorted(colors.items()) if (value := color(raw)) is not None}

    floats = normalize_unity_property_map(props.get("m_Floats"))
    result["floats"] = {
        key: float(value)
        for key, value in sorted(floats.items())
        if isinstance(value, (int, float)) or str(value).replace(".", "", 1).replace("-", "", 1).isdigit()
    }
    result["alpha"] = bool(float(floats.get("_AlphaClip", 0.0) or 0.0) > 0.0 or float(floats.get("_BlendMode", 0.0) or 0.0) > 0.0)
    return result


def material_info_by_name(
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    all_entries: list[dict[str, Any]],
    name: str,
) -> dict[str, Any]:
    candidates = [
        entry
        for entry in all_entries
        if entry.get("Type") == "Material" and str(entry.get("Name") or "") == name
    ]
    if candidates:
        chosen = sorted(
            candidates,
            key=lambda item: (
                0 if item.get("_asset_root") == "StreamingAssets" else 1,
                0 if "_p" not in str(item.get("Name")) else 1,
                len(str(item.get("Container") or "")),
            ),
        )[0]
        return material_info(by_type_path_id, int(chosen.get("PathID") or 0))

    json_path = find_json_by_type("Material", name)
    return {
        "name": name,
        "path_id": 0,
        "container": "",
        "asset_root": "",
        "json": str(json_path.resolve()) if json_path else "",
        "shader_path_id": 0,
        "shader_name": "",
        "base": "",
        "normal": "",
        "color": [1.0, 1.0, 1.0, 1.0],
        "alpha": False,
        "textures": {},
        "floats": {},
        "colors": {},
    }


def build_mesh_manifest(
    path_to_data: dict[str, dict[str, Any]],
    id_to_path: dict[int, str],
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    materials: dict[str, dict[str, Any]] = {}
    meshes: list[dict[str, Any]] = []
    all_renderer_paths = [path for path, data in path_to_data.items() if data.get("m_SkinnedMeshRenderer")]
    lod_counts = Counter(path.split("/")[1] if path.startswith("Mesh_all/") and len(path.split("/")) > 1 else "other" for path in all_renderer_paths)
    excluded_vfx_lod0 = 0
    hidden_depth_only_auxiliary = 0
    hidden_runtime_override_placeholders = 0
    excluded_unsupported_white_fallbacks: list[dict[str, Any]] = []

    for path in all_renderer_paths:
        if not path.startswith("Mesh_all/lod0/"):
            continue
        data = path_to_data[path]
        smr = data.get("m_SkinnedMeshRenderer") or {}
        mesh_path_id = ref_path_id(smr.get("m_Mesh"))
        mesh_asset = pick_asset(by_type_path_id, "Mesh", mesh_path_id)
        mesh_name = str((mesh_asset or {}).get("Name") or data.get("m_Name") or "")
        material_path_ids = tuple(
            ref_path_id(material_ref)
            for material_ref in smr.get("m_Materials") or []
        )
        unsupported_white_fallback = exact_lastrite_unsupported_white_fallback(
            mesh_name,
            mesh_path_id,
            material_path_ids,
        )
        if unsupported_white_fallback is not None:
            if is_vfx_mesh_name(mesh_name) or is_vfx_mesh_name(path):
                excluded_vfx_lod0 += 1
            unsupported_white_fallback["renderer_path"] = path
            excluded_unsupported_white_fallbacks.append(unsupported_white_fallback)
            continue
        if is_vfx_mesh_name(mesh_name) or is_vfx_mesh_name(path):
            excluded_vfx_lod0 += 1
            continue
        mesh_json = exported_json_path(MESH_DIR, mesh_name, mesh_path_id)
        material_keys: list[str] = []
        material_names: list[str] = []
        for mat_ref in smr.get("m_Materials") or []:
            material_path_id = ref_path_id(mat_ref)
            key = f"pathid_{material_path_id}"
            if key not in materials:
                materials[key] = material_info(by_type_path_id, material_path_id)
            material_keys.append(key)
            material_names.append(materials[key]["name"])

        depth_only_auxiliary = bool(material_keys) and all(
            "VFXTransparentDepthOnly" in str(materials[key].get("shader_name") or "")
            for key in material_keys
        )
        if depth_only_auxiliary:
            hidden_depth_only_auxiliary += 1

        runtime_override_placeholder = bool(material_keys) and all(
            str(materials[key].get("name") or "") == "DefaultHGMaterial"
            for key in material_keys
        )
        if runtime_override_placeholder:
            hidden_runtime_override_placeholders += 1

        default_visible = not (depth_only_auxiliary or runtime_override_placeholder)
        if depth_only_auxiliary:
            visibility_evidence = (
                "hidden_auxiliary_depth_only_material_until_authored_state_is_recovered"
            )
        elif runtime_override_placeholder:
            visibility_evidence = (
                "hidden_default_hg_material_until_runtime_material_override_is_recovered"
            )
        else:
            visibility_evidence = "baseline_lod0_renderer"

        aabb = smr.get("m_AABB") or {}
        meshes.append(
            {
                "name": mesh_name,
                "path": path,
                "parent_path": path.rsplit("/", 1)[0],
                "mesh_json": str(mesh_json.resolve()) if mesh_json.is_file() else "",
                "mesh_path_id": mesh_path_id,
                "mesh_container": (mesh_asset or {}).get("Container", ""),
                "material_keys": material_keys,
                "material_key": material_keys[0] if material_keys else "",
                "material_names": material_names,
                "default_visible": default_visible,
                "visibility_evidence": visibility_evidence,
                "root_bone_path": id_to_path.get(ref_path_id(smr.get("m_RootBone")), ""),
                "bone_paths": [id_to_path.get(ref_path_id(ref), "") for ref in smr.get("m_Bones") or []],
                "aabb_center": vec3(aabb.get("m_Center")),
                "aabb_extent": vec3(aabb.get("m_Extent")),
            }
        )

    missing_meshes = [mesh["name"] for mesh in meshes if not mesh["mesh_json"]]
    if missing_meshes:
        raise SystemExit(f"missing mesh JSON for: {', '.join(missing_meshes)}")

    summary = {
        "all_skinned_mesh_renderers": len(all_renderer_paths),
        "lod_renderer_counts": dict(sorted(lod_counts.items())),
        "active_lod": "lod0",
        "mesh_filter": (
            "lod0_non_vfx_source_gated_auxiliaries"
            if excluded_unsupported_white_fallbacks
            else "lod0_non_vfx"
        ),
        "excluded_vfx_lod0_renderers": excluded_vfx_lod0,
        "hidden_depth_only_auxiliary_renderers": hidden_depth_only_auxiliary,
        "hidden_runtime_override_placeholder_renderers": hidden_runtime_override_placeholders,
        "excluded_unsupported_white_fallback_renderers": len(
            excluded_unsupported_white_fallbacks
        ),
        "excluded_unsupported_white_fallbacks": excluded_unsupported_white_fallbacks,
        "active_lod_renderers": len(meshes),
    }
    return meshes, materials, summary


def build_scene_transform_manifest(
    transforms: list[dict[str, Any]],
    meshes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mesh_paths = {str(mesh["path"]) for mesh in meshes}
    mesh_container_paths: set[str] = set()
    for path in mesh_paths:
        current = path
        while current:
            mesh_container_paths.add(current)
            current = current.rsplit("/", 1)[0] if "/" in current else ""

    scene_transforms: list[dict[str, Any]] = []
    excluded = Counter()
    for item in transforms:
        path = str(item["path"])
        if path == "Mesh_all" or path.startswith("Mesh_all/"):
            if path in mesh_container_paths:
                scene_transforms.append(item)
            else:
                excluded["mesh_lod_or_vfx"] += 1
            continue
        if path == "Shadow_Proxy" or path.startswith("Shadow_Proxy/"):
            excluded["shadow_proxy"] += 1
            continue
        if "vfx" in path.lower():
            excluded["vfx_transform"] += 1
            continue
        scene_transforms.append(item)

    return scene_transforms, {
        "scene_transform_count": len(scene_transforms),
        "excluded_transform_counts": dict(sorted(excluded.items())),
    }


def build_experimental_model_variants(
    transforms: list[dict[str, Any]],
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    all_entries: list[dict[str, Any]],
    materials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not ALT_MESH_DIR.is_dir():
        return []

    transforms_by_crc = {int(item["path_crc"]): item for item in transforms}
    variant_meshes: list[dict[str, Any]] = []
    notes: list[str] = []

    def material_key(material_name: str) -> str:
        key = f"name_{material_name}"
        if key not in materials:
            materials[key] = material_info_by_name(by_type_path_id, all_entries, material_name)
        return key

    for mesh_name, material_names in EXPERIMENTAL_VARIANT_MESHES:
        if is_vfx_mesh_name(mesh_name):
            continue
        mesh_json = ALT_MESH_DIR / f"{mesh_name}.json"
        if not mesh_json.is_file():
            notes.append(f"missing mesh JSON: {mesh_name}")
            continue
        mesh_data = load_json(mesh_json)
        bone_hashes = [int(item) for item in mesh_data.get("m_BoneNameHashes") or []]
        matched = sum(1 for crc in bone_hashes if crc in transforms_by_crc)
        if bone_hashes and matched / len(bone_hashes) < 0.5:
            notes.append(f"skipped {mesh_name}: only {matched}/{len(bone_hashes)} bone hashes match the base postmodel")
            continue

        keys = [material_key(name) for name in material_names]
        variant_meshes.append(
            {
                "name": mesh_name,
                "path": f"Variant_SK_actor_zhuangfy_02/{mesh_name}",
                "parent_path": "Variant_SK_actor_zhuangfy_02",
                "mesh_json": str(mesh_json.resolve()),
                "mesh_path_id": 0,
                "mesh_container": "assets/beyond/arts/entity/actor/lady/zhuangfy/models/sk_actor_zhuangfy_02.fbx",
                "material_keys": keys,
                "material_key": keys[0] if keys else "",
                "material_names": material_names,
                "root_bone_path": "",
                "bone_paths": [
                    str((transforms_by_crc.get(int(crc)) or {}).get("path") or "")
                    for crc in bone_hashes
                ],
                "aabb_center": [0.0, 0.0, 0.0],
                "aabb_extent": [0.0, 0.0, 0.0],
                "matched_bone_hashes": matched,
                "total_bone_hashes": len(bone_hashes),
            }
        )

    if not variant_meshes:
        return []
    return [
        {
            "display_name": "Zhuangfy SK_actor_zhuangfy_02 experimental",
            "root_name": "actor_zhuangfy_variant02_experimental",
            "source_model": "SK_actor_zhuangfy_02.fbx",
            "exact_postmodel": False,
            "scene_offset": [4.0, 0.0, 0.0],
            "notes": [
                "Built by reusing the recovered chr_0030_zhuangfy_postmodel skeleton because most SK_actor_zhuangfy_02 bone hashes match it.",
                "Renderer/material pairings are inferred from matching Zhuangfy material names; this is a preview variant, not a proven original prefab binding.",
                "VFX body/part renderers are intentionally excluded from the viewer import.",
                *notes,
            ],
            "meshes": variant_meshes,
        }
    ]


def parse_clip_bindings(clip_path: Path, transforms_by_crc: dict[int, dict[str, Any]]) -> dict[str, Any]:
    data = load_json(clip_path)
    acl = data.get("m_AclCompressedBuffer") or {}
    bindings = (data.get("m_ClipBindingConstant") or {}).get("genericBindings") or []
    default_indices = set(int(item) for item in (acl.get("m_DefaultIndexs") or []))
    constant_indices = set(int(item) for item in (acl.get("m_ConstantIndexs") or []))

    bone_map: dict[int, dict[str, Any]] = {}
    first_binding_order: list[int] = []
    channel_track_orders: dict[str, list[int]] = {
        "position": [],
        "rotation": [],
        "scale": [],
    }
    for binding_index, binding in enumerate(bindings):
        if binding.get("typeID") != "Transform":
            continue
        crc = int(binding.get("path") or 0)
        attr = int(binding.get("attribute") or 0)
        if crc not in bone_map:
            first_binding_order.append(crc)
        item = bone_map.setdefault(
            crc,
            {
                "path_crc": crc,
                "track_index": None,
                "pos_animated": False,
                "rot_animated": False,
                "scale_animated": False,
                "_pos_binding_indices": [],
                "_rot_binding_indices": [],
                "_scale_binding_indices": [],
                "matched": crc in transforms_by_crc,
                "path": (transforms_by_crc.get(crc) or {}).get("path", ""),
                "name": (transforms_by_crc.get(crc) or {}).get("name", ""),
            },
        )
        if attr == 1:
            item["_pos_binding_indices"].append(binding_index)
            if crc not in channel_track_orders["position"]:
                channel_track_orders["position"].append(crc)
        elif attr in {2, 4}:
            item["_rot_binding_indices"].append(binding_index)
            if crc not in channel_track_orders["rotation"]:
                channel_track_orders["rotation"].append(crc)
        elif attr == 3:
            item["_scale_binding_indices"].append(binding_index)
            if crc not in channel_track_orders["scale"]:
                channel_track_orders["scale"].append(crc)

    output_track_count = int(acl.get("OutputTrackCount") or 0)
    transform_track_order = first_binding_order
    track_order_evidence = "generic_binding_first_occurrence"
    if output_track_count > 0:
        complete_orders = [
            (channel, order)
            for channel, order in channel_track_orders.items()
            if len(order) == output_track_count
        ]
        if not complete_orders:
            raise ValueError(
                f"{clip_path}: ACL output track count {output_track_count} has no "
                "complete Transform binding channel order; "
                f"position={len(channel_track_orders['position'])}, "
                f"rotation={len(channel_track_orders['rotation'])}, "
                f"scale={len(channel_track_orders['scale'])}"
            )
        preferred_channel = next(
            (
                channel
                for channel in ("rotation", "position", "scale")
                if any(candidate == channel for candidate, _ in complete_orders)
            ),
            complete_orders[0][0],
        )
        transform_track_order = next(
            order for channel, order in complete_orders if channel == preferred_channel
        )
        conflicting_channels = [
            channel
            for channel, order in complete_orders
            if order != transform_track_order
        ]
        if conflicting_channels:
            raise ValueError(
                f"{clip_path}: complete ACL Transform binding channel orders disagree; "
                f"selected={preferred_channel}, conflicting={conflicting_channels}"
            )
        track_order_evidence = f"complete_{preferred_channel}_binding_order"

    # Before decoded samples are applied, preserve every declared channel
    # except channels that ACL explicitly marks as defaults.  Constant ACL
    # bindings are deliberately retained: they may encode a non-bind pose.
    for item in bone_map.values():
        for manifest_prefix in ("pos", "rot", "scale"):
            channel_indices = item[f"_{manifest_prefix}_binding_indices"]
            uses_default = bool(channel_indices) and all(index in default_indices for index in channel_indices)
            uses_constant = bool(channel_indices) and all(index in constant_indices for index in channel_indices)
            item[f"_{manifest_prefix}_uses_default"] = uses_default
            item[f"_{manifest_prefix}_uses_constant"] = uses_constant
            item[f"{manifest_prefix}_animated"] = bool(channel_indices) and not uses_default

    for track_index, crc in enumerate(transform_track_order):
        if crc in bone_map:
            bone_map[crc]["track_index"] = track_index

    muscle_clip = data.get("m_MuscleClip") or {}
    dense_clip = ((muscle_clip.get("m_Clip") or {}).get("m_DenseClip") or {})
    return {
        "name": str(data.get("Name") or clip_path.stem),
        "frame_count": int(dense_clip.get("m_FrameCount") or 0),
        "sample_rate": float(dense_clip.get("m_SampleRate") or data.get("m_SampleRate") or 60.0),
        "stop_time": float(muscle_clip.get("m_StopTime") or 0.0),
        "loop": bool(muscle_clip.get("m_LoopTime") or False),
        "loop_blend": bool(muscle_clip.get("m_LoopBlend") or False),
        "binding_count": len(bindings),
        "transform_track_count": len(transform_track_order),
        "output_track_count": output_track_count,
        "track_order_evidence": track_order_evidence,
        "bones": sorted(bone_map.values(), key=lambda item: int(item["track_index"]) if item.get("track_index") is not None else 999999),
    }


def remap_muscleclip_info_to_sample_bindings(
    info: dict[str, Any],
    sample_data: dict[str, Any],
    transforms_by_crc: dict[int, dict[str, Any]],
    *,
    hierarchy_path_prefix: str = "",
) -> list[dict[str, Any]]:
    """Use the sampler's compact matched-track order for stock MuscleClips.

    The source GenericBinding order can contain transform paths absent from the
    recovered postmodel. ``unity_muscleclip_sampler`` drops those paths while
    building its qvvf frames, so retaining pre-filter source indices shifts
    every later curve onto the wrong transform. The sampler's track_bindings
    are the authoritative compact index/path/CRC mapping for its frames.
    Private-widget sampler paths are relative to their recovered prop root;
    ``hierarchy_path_prefix`` validates that relationship while retaining the
    full generated hierarchy path in the returned manifest binding.
    """

    sample_bindings = sample_data.get("track_bindings") or []
    sample_track_count = int(sample_data.get("num_tracks") or 0)
    if sample_track_count <= 0 or len(sample_bindings) != sample_track_count:
        raise ValueError(
            "MuscleClip sample track binding count mismatch: "
            f"bindings={len(sample_bindings)}, tracks={sample_track_count}"
        )

    source_by_crc = {int(bone.get("path_crc") or 0): bone for bone in info.get("bones") or []}
    remapped: list[dict[str, Any]] = []
    for track_index, binding in enumerate(sample_bindings):
        declared_index = int(binding.get("track_index") if binding.get("track_index") is not None else -1)
        crc = int(binding.get("path_crc") or 0)
        path = str(binding.get("path") or "")
        transform = transforms_by_crc.get(crc)
        source = source_by_crc.get(crc)
        if declared_index != track_index:
            raise ValueError(
                f"MuscleClip sample track index is not compact: expected={track_index}, got={declared_index}"
            )
        if source is None:
            raise ValueError(
                "MuscleClip compact binding is absent from the source binding table: "
                f"index={track_index}, crc={crc}"
            )
        if transform is None:
            # The sampler is built against the complete original prefab and
            # can therefore retain a source track that the render-focused lab
            # hierarchy deliberately omits (for example a VFX-only mount).
            # Keep that track at its compact frame index as an unmatched
            # source binding.  Unity curve emission already requires
            # ``matched``; dropping the row here would shift every later
            # sampled track and rejecting the whole clip would also discard
            # the independently recoverable rendered-item motion.
            item = dict(source)
            item.update(
                {
                    "track_index": track_index,
                    "matched": False,
                    "path_crc": crc,
                    "path": "",
                    "name": str(binding.get("name") or source.get("name") or ""),
                }
            )
            remapped.append(item)
            continue
        hierarchy_path = str(transform.get("path") or "")
        expected_sample_path = hierarchy_path
        if hierarchy_path_prefix:
            prefix = hierarchy_path_prefix.rstrip("/") + "/"
            if not hierarchy_path.startswith(prefix):
                raise ValueError(
                    "MuscleClip recovered hierarchy escaped its widget root: "
                    f"index={track_index}, hierarchy={hierarchy_path}, prefix={hierarchy_path_prefix}"
                )
            expected_sample_path = hierarchy_path[len(prefix):]
        if path != expected_sample_path:
            raise ValueError(
                "MuscleClip sample path/CRC does not match recovered hierarchy: "
                f"index={track_index}, sample={path}, hierarchy={hierarchy_path}"
            )
        item = dict(source)
        item.update(
            {
                "track_index": track_index,
                "matched": True,
                "path_crc": crc,
                "path": hierarchy_path,
                "name": str(binding.get("name") or transform.get("name") or ""),
            }
        )
        remapped.append(item)

    info["bones"] = remapped
    info["transform_track_count"] = sample_track_count
    info["output_track_count"] = sample_track_count
    return remapped


def clip_requirements(clip_name: str, matched: int, missing: int) -> list[str]:
    requirements: list[str] = []
    if missing:
        requirements.append(f"{missing} transform bindings are outside chr_0030_zhuangfy_postmodel")
    lowered = clip_name.lower()
    if "takeoutplane" in lowered:
        requirements.append("dialog prop/timeline item: takeout plane model is not recovered yet")
    if "_cs_" in lowered or "cutscene" in lowered:
        requirements.append("cutscene context may need extra timeline objects, effects, and camera bindings")
    if "climax" in lowered or "dialog_single" in lowered or "dialog_state" in lowered or "customized" in lowered:
        requirements.append("facial/morph layers are separate from this body clip")
    if (
        "additive" in lowered
        or "cloth_" in lowered
        or "_cloth" in lowered
        or "tail_" in lowered
        or "wind_" in lowered
        or "hair_roll" in lowered
        or "hair_yaw" in lowered
        or "lookat" in lowered
        or "_ao_" in lowered
        or "_tilt_" in lowered
        or "t_pose" in lowered
    ):
        requirements.append("controller/additive helper clip; not a standalone full-body state")
    if "item_widget" in lowered:
        requirements.append("UI/widget context may need separate prop or menu timeline bindings")
    if lowered.startswith("a_fx") or "fxui" in lowered or "fx_ui" in lowered:
        requirements.append("FX context may need separate particle, prop, or timeline objects")
    if matched == 0:
        requirements.append("no body transforms matched the recovered postmodel")
    return requirements


def clip_binding_evidence(clip_name: str) -> str:
    if clip_name in CONTROLLER_BOUND_ANIMATION_CLIPS:
        return "controller_bound_helper_clip"
    if clip_name in CANDIDATE_DIALOG_ANIMATION_CLIPS:
        return "dialog_or_cutscene_candidate_clip"
    lowered = clip_name.lower()
    if ACTOR_TOKEN in lowered:
        return "acl_transform_sampled_zhuangfy_clip"
    return "acl_transform_sampled_clip"


def clip_classification(clip_class: str, layer_role: str, standalone_candidate: bool) -> dict[str, Any]:
    return {
        "clip_class": clip_class,
        "clip_category": clip_class,
        "layer_role": layer_role,
        "standalone_candidate": standalone_candidate,
    }


def classify_clip(clip_name: str) -> dict[str, Any]:
    lowered = clip_name.lower()
    helper_tokens = (
        "additive",
        "cloth_",
        "_cloth",
        "onlycloth",
        "a_fx",
        "fxui",
        "fx_ui",
        "item_widget",
        "wind_",
        "hair_roll",
        "hair_yaw",
        "tail_",
        "lookat",
        "_ao_",
        "_tilt_",
        "t_pose",
    )
    ik_helper = re.search(r"(?:^|_)ik(?:_|$)", lowered) is not None
    if (
        clip_name in CONTROLLER_BOUND_ANIMATION_CLIPS
        or ik_helper
        or any(token in lowered for token in helper_tokens)
    ):
        clip_class = "additive" if "additive" in lowered else "helper"
        return clip_classification(
            clip_class,
            "additive_overlay" if clip_class == "additive" else "controller_helper",
            False,
        )
    if "_cs_" in lowered or "cutscene" in lowered or ("_cv_" in lowered and "_sc" in lowered):
        return clip_classification("cutscene", "cutscene_body", True)
    if "_ui_" in lowered or "uiteam" in lowered or "uigo" in lowered or "gacha" in lowered:
        return clip_classification("ui", "ui_body", True)
    if "dialog" in lowered or "dlgtl" in lowered:
        return clip_classification("dialog", "dialog_body", True)
    if "customized" in lowered:
        return clip_classification("customized", "customized_body", True)
    battle_tokens = (
        "battle",
        "attack",
        "skill",
        "ult",
        "hurt",
        "dash",
        "dodge",
        "guard",
        "dead",
        "stun",
        "knock",
        "poise",
        "airborne",
        "blowoff",
        "fightidle",
    )
    if any(token in lowered for token in battle_tokens):
        return clip_classification("battle", "battle_body", True)
    if "interact" in lowered:
        return clip_classification("interact", "interaction_body", True)
    locomotion_tokens = (
        "_walk_",
        "_run_",
        "_sprint_",
        "_jump_",
        "_idle_",
        "_move_",
        "locomotion",
        "rotate",
        "fall",
        "landing",
    )
    if any(token in lowered for token in locomotion_tokens):
        return clip_classification("locomotion", "locomotion_body", True)
    return clip_classification("standalone", "body", True)


def is_helper_or_additive_clip(clip_name: str) -> bool:
    classification = classify_clip(clip_name)
    return (
        not bool(classification.get("standalone_candidate", True))
        or str(classification.get("clip_class") or "").lower() in {"helper", "additive"}
        or str(classification.get("layer_role") or "").lower() in {"controller_helper", "additive_overlay"}
    )


def animation_clip_name_from_path_id(
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    path_id: int,
) -> str:
    asset = pick_asset(by_type_path_id, "AnimationClip", path_id)
    if asset and asset.get("Name"):
        return str(asset["Name"])
    return f"<AnimationClip:{path_id}>"


def collect_clip_ids(value: Any, out: list[int]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "m_ClipID":
                try:
                    clip_id = int(child)
                except (TypeError, ValueError):
                    continue
                if clip_id != 4294967295:
                    out.append(clip_id)
            else:
                collect_clip_ids(child, out)
    elif isinstance(value, list):
        for child in value:
            collect_clip_ids(child, out)


def unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def summarize_animator_controller(
    path: Path,
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
    include_state_groups: bool,
) -> dict[str, Any]:
    data = load_json(path)
    controller = data.get("m_Controller") or {}
    clip_names = [
        animation_clip_name_from_path_id(by_type_path_id, int((ref or {}).get("m_PathID") or 0))
        for ref in data.get("m_AnimationClips") or []
    ]

    state_machines = list(controller.get("m_StateMachineArray") or [])
    layer_summaries: list[dict[str, Any]] = []
    for layer_index, layer_obj in enumerate(controller.get("m_LayerArray") or []):
        layer_data = (layer_obj or {}).get("data") or {}
        states = []
        if layer_index < len(state_machines):
            states = ((state_machines[layer_index] or {}).get("data") or {}).get("m_StateConstantArray") or []
        layer_clip_ids: list[int] = []
        collect_clip_ids(states, layer_clip_ids)
        layer_clip_names = unique_preserving_order(
            [clip_names[clip_id] for clip_id in layer_clip_ids if 0 <= clip_id < len(clip_names)]
        )
        zhuangfy_layer_clip_names = [name for name in layer_clip_names if ACTOR_TOKEN in name.lower()]
        layer_summaries.append(
            {
                "index": layer_index,
                "state_count": len(states),
                "unique_clip_count": len(layer_clip_names),
                "zhuangfy_clip_count": len(zhuangfy_layer_clip_names),
                "layer_blending_mode": layer_data.get("(int&)m_LayerBlendingMode"),
                "default_weight": layer_data.get("m_DefaultWeight"),
                "ik_pass": bool(layer_data.get("m_IKPass")),
                "use_three_pose_blender": bool(layer_data.get("m_UseThreePoseBlender")),
                "post_process_layer": bool(layer_data.get("m_PostProcessLayer")),
                "lod_threshold": layer_data.get("m_LODThreshold"),
                "ability_threshold": layer_data.get("m_AbilityThreshold"),
            }
        )

    state_clip_groups: list[dict[str, Any]] = []
    if include_state_groups:
        for layer_index, state_machine in enumerate(state_machines):
            states = ((state_machine or {}).get("data") or {}).get("m_StateConstantArray") or []
            for state_index, state_obj in enumerate(states):
                state_data = (state_obj or {}).get("data") or {}
                clip_ids: list[int] = []
                collect_clip_ids(state_data.get("m_BlendTreeConstantArray") or [], clip_ids)
                group_clip_names = unique_preserving_order(
                    [clip_names[clip_id] for clip_id in clip_ids if 0 <= clip_id < len(clip_names)]
                )
                zhuangfy_clip_names = [name for name in group_clip_names if ACTOR_TOKEN in name.lower()]
                if not zhuangfy_clip_names or len(group_clip_names) < 2:
                    continue
                state_clip_groups.append(
                    {
                        "controller": data.get("m_Name", path.stem),
                        "source_json": str(path.relative_to(REPO_ROOT)),
                        "layer_index": layer_index,
                        "state_index": state_index,
                        "clip_count": len(group_clip_names),
                        "zhuangfy_clip_count": len(zhuangfy_clip_names),
                        "clips": group_clip_names[:16],
                        "zhuangfy_clips": zhuangfy_clip_names[:16],
                        "other_clips": [name for name in group_clip_names if ACTOR_TOKEN not in name.lower()][:16],
                    }
                )

    zhuangfy_clip_names = sorted({name for name in clip_names if ACTOR_TOKEN in name.lower()})
    return {
        "name": data.get("m_Name", path.stem),
        "source_json": str(path.relative_to(REPO_ROOT)),
        "layer_count": len(controller.get("m_LayerArray") or []),
        "animation_clip_ref_count": len(clip_names),
        "unique_animation_clip_count": len(set(clip_names)),
        "zhuangfy_animation_clip_count": len(zhuangfy_clip_names),
        "zhuangfy_animation_clips": zhuangfy_clip_names[:80],
        "layers": layer_summaries,
        "state_clip_groups": state_clip_groups[:120],
        "endfield_fields": {
            "cloth_calculator_type": data.get("m_ClothCalculatorType"),
            "enable_opt_clip_bindings": bool(data.get("m_EnableOptClipBindings")),
            "reserve_count": data.get("m_ReserveCount"),
        },
    }


def collect_controller_recovery(
    by_type_path_id: dict[tuple[str, int], list[dict[str, Any]]],
) -> dict[str, Any]:
    controller_paths: list[Path] = []
    for folder in ANIMATOR_CONTROLLER_DIRS:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json")):
            try:
                if ACTOR_TOKEN not in path.read_text(encoding="utf-8", errors="ignore").lower():
                    continue
            except OSError:
                continue
            controller_paths.append(path)

    summaries: list[dict[str, Any]] = []
    main_summary: dict[str, Any] = {}
    for path in controller_paths:
        is_main = path == MAIN_ANIMATOR_CONTROLLER
        summary = summarize_animator_controller(path, by_type_path_id, include_state_groups=is_main)
        summaries.append(
            {
                key: value
                for key, value in summary.items()
                if key not in {"layers", "state_clip_groups"}
            }
        )
        if is_main:
            main_summary = summary

    state_clip_groups = list(main_summary.get("state_clip_groups") or [])
    helper_groups = [
        group
        for group in state_clip_groups
        if any(is_helper_or_additive_clip(name) for name in group.get("zhuangfy_clips") or [])
    ]
    return {
        "source": "original AnimatorController JSON exported by AnimeStudio",
        "controller_json_count_with_zhuangfy_text": len(controller_paths),
        "controllers": summaries[:80],
        "main_controller": main_summary,
        "main_controller_state_clip_group_count": len(state_clip_groups),
        "main_controller_helper_group_count": len(helper_groups),
        "interpretation": [
            "The main Persistent controller is AC_chr_0030_zhuangfy.",
            "Controller layers include Endfield-specific fields such as m_UseThreePoseBlender, LOD thresholds, ability thresholds, and additive layer blending modes.",
            "State clip groups are blend-tree/state co-use evidence. They are stronger than filename similarity, but they still do not reproduce runtime IK, scripts, or pose-driver logic by themselves.",
        ],
    }


def add_clip_combination(
    combinations: dict[tuple[str, str], dict[str, Any]],
    base_clip: str,
    helper_clip: str,
    source: str,
    confidence: str,
    auto_apply: bool,
    note: str,
) -> None:
    if not base_clip or not helper_clip or base_clip == helper_clip:
        return
    key = (base_clip, helper_clip)
    existing = combinations.get(key)
    if existing:
        sources = set(existing.get("sources") or [])
        sources.add(source)
        existing["sources"] = sorted(sources)
        existing["auto_apply"] = bool(existing.get("auto_apply") or auto_apply)
        if confidence == "high":
            existing["confidence"] = "high"
        return
    combinations[key] = {
        "base_clip": base_clip,
        "helper_clip": helper_clip,
        "sources": [source],
        "confidence": confidence,
        "auto_apply": auto_apply,
        "note": note,
    }


def infer_clip_combinations(clips: list[dict[str, Any]], controller_recovery: dict[str, Any]) -> list[dict[str, Any]]:
    clip_names = {str(clip.get("name") or "") for clip in clips}
    combinations: dict[tuple[str, str], dict[str, Any]] = {}

    for name in sorted(clip_names):
        lowered = name.lower()
        if lowered.endswith("_cloth"):
            base = name[:-6]
            if base in clip_names:
                add_clip_combination(
                    combinations,
                    base,
                    name,
                    "matched_clip_name_suffix",
                    "medium",
                    True,
                    "Suffix-matched cloth companion imported with the same base clip name.",
                )

    main_controller = controller_recovery.get("main_controller") or {}
    for group in main_controller.get("state_clip_groups") or []:
        zhuangfy_group = [name for name in group.get("zhuangfy_clips") or [] if name in clip_names]
        if len(zhuangfy_group) != 2:
            continue
        first, second = zhuangfy_group
        first_helper = is_helper_or_additive_clip(first)
        second_helper = is_helper_or_additive_clip(second)
        if first_helper != second_helper:
            base_clip = second if first_helper else first
            helper_clip = first if first_helper else second
            add_clip_combination(
                combinations,
                base_clip,
                helper_clip,
                "main_controller_state_group",
                "high",
                True,
                "Main controller state/blend tree references this body clip with one helper/additive clip.",
            )
        else:
            add_clip_combination(
                combinations,
                first,
                second,
                "main_controller_helper_group",
                "medium",
                False,
                "Main controller co-references these helper/additive clips in the same state/blend tree.",
            )

    return sorted(combinations.values(), key=lambda item: (item["base_clip"], item["helper_clip"]))


def apply_clip_combinations(clips: list[dict[str, Any]], combinations: list[dict[str, Any]]) -> None:
    by_name = {str(clip.get("name") or ""): clip for clip in clips}
    for combo in combinations:
        base = by_name.get(str(combo.get("base_clip") or ""))
        if not base:
            continue
        combined = list(base.get("combined_with") or [])
        helper = str(combo.get("helper_clip") or "")
        if helper and helper not in combined:
            combined.append(helper)
        base["combined_with"] = combined
        if combo.get("auto_apply") and not base.get("auto_helper_clip"):
            base["auto_helper_clip"] = helper
            base["combination_note"] = str(combo.get("note") or "")


def build_recovered_states(
    clips: list[dict[str, Any]],
    combinations: list[dict[str, Any]],
    controller_recovery: dict[str, Any],
) -> list[dict[str, Any]]:
    by_name = {str(clip.get("name") or ""): clip for clip in clips}
    states: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()

    def role_for(name: str) -> str:
        clip = by_name.get(name) or {}
        return str(clip.get("layer_role") or clip.get("clip_class") or "")

    def helperish(name: str) -> bool:
        clip = by_name.get(name) or {}
        return bool(
            is_helper_or_additive_clip(name)
            or str(clip.get("clip_class") or "").lower() in {"helper", "additive"}
            or str(clip.get("layer_role") or "").lower() in {"controller_helper", "additive_overlay"}
        )

    def add_state(
        label: str,
        base_clip: str,
        layer_clips: list[str],
        source: str,
        confidence: str,
        note: str,
        evidence_clips: list[str],
    ) -> None:
        if base_clip not in by_name:
            return
        unique_layers = [name for name in unique_preserving_order(layer_clips) if name in by_name and name != base_clip]
        if not unique_layers:
            return
        key = (base_clip, tuple(unique_layers), source)
        if key in seen:
            return
        seen.add(key)
        short_label = label if len(label) <= 96 else label[:93] + "..."
        states.append(
            {
                "label": short_label,
                "base_clip": base_clip,
                "source": source,
                "confidence": confidence,
                "note": note,
                "evidence_clips": unique_preserving_order([name for name in evidence_clips if name in by_name])[:16],
                "layers": [
                    {
                        "clip": layer_clip,
                        "layer": index + 1,
                        "blend_mode": "additive" if helperish(layer_clip) else "blend",
                        "weight": 1.0,
                        "role": role_for(layer_clip),
                    }
                    for index, layer_clip in enumerate(unique_layers[:6])
                ],
            }
        )

    for combo in combinations:
        base_clip = str(combo.get("base_clip") or "")
        helper_clip = str(combo.get("helper_clip") or "")
        if not base_clip or not helper_clip:
            continue
        add_state(
            f"{base_clip} + {helper_clip}",
            base_clip,
            [helper_clip],
            ",".join(str(item) for item in combo.get("sources") or ["clip_combination"]),
            str(combo.get("confidence") or "medium"),
            str(combo.get("note") or "Recovered helper clip pairing."),
            [base_clip, helper_clip],
        )

    main_controller = controller_recovery.get("main_controller") or {}
    for group in main_controller.get("state_clip_groups") or []:
        group_clips = [name for name in group.get("zhuangfy_clips") or [] if name in by_name]
        if len(group_clips) < 2 or not any(helperish(name) for name in group_clips):
            continue

        base_candidates = [name for name in group_clips if not helperish(name)]
        if base_candidates:
            base_clip = base_candidates[0]
            layer_clips = [name for name in group_clips if name != base_clip and helperish(name)]
            note = "Main controller state/blend tree co-references this base clip with helper/additive layers."
        else:
            base_clip = group_clips[0]
            layer_clips = group_clips[1:]
            note = "Overlay-only controller group. This is useful evidence, but the original base pose comes from another controller layer."

        layer_index = int(group.get("layer_index") or 0)
        state_index = int(group.get("state_index") or 0)
        label = f"L{layer_index} S{state_index}: {base_clip}"
        if layer_clips:
            label += " + " + " + ".join(layer_clips[:3])
            if len(layer_clips) > 3:
                label += f" + {len(layer_clips) - 3} more"
        add_state(
            label,
            base_clip,
            layer_clips,
            "main_controller_state_group",
            "medium",
            note,
            group_clips,
        )

    return states[:80]


def build_ik_manifest(
    transforms: list[dict[str, Any]],
    character_id: str | None = None,
) -> dict[str, Any]:
    transform_by_path = {str(item.get("path") or ""): item for item in transforms}
    ik_targets = [
        {
            "name": str(item.get("name") or ""),
            "path": str(item.get("path") or ""),
            "local_pos": item.get("local_pos") or [],
        }
        for item in transforms
        if str(item.get("name") or "").startswith("IK_") or str(item.get("name") or "") == "GrounderIK"
    ]

    def exists(path: str) -> bool:
        return path in transform_by_path

    ik = {
        "source": "postmodel_transform_hierarchy",
        "status": "authored_targets_recovered_retail_foot_binding_proven_hand_targets_external",
        "note": f"All {grounder_profiles.expected_roster_count()} exact current-roster Grounder components bind sampled foot-reference fields to IK_Foot_L/R_001; these are Grounding inputs, not BipedIK limb targets. CharacterAnimationBlackboard requests three foot values; the complete current UI-clip audit recovers 24 exact FootIKWeight ACL curves and no FootIKFootWeight or FootIKAdsorbWeight bindings. Native absent-key behavior, the final pelvis-weight ground/air recurrence, and the active MovementSetting Terrain|IK mask are recovered exactly. Live controller inputs, callback order, a source-compatible terrain provider, and numeric original-frame fixtures remain absent, so the lab stays fail-closed. The quality-3 ordinary and root-aligned base paths are source-closed, while shared prediction/capsule branches and all non-foot policies remain disabled. BipedIK hand/foot targets and bend goals are null; CharacterLimbIKBrain receives hand targets from interaction exData, and no sampled component binds the baked knee or weapon markers.",
        "runtime_solver": {
            "default_enabled": False,
            "activation": "explicit_lab_opt_in_only",
            "consumer_proven": False,
            "weights_proven": False,
            "baked_target_binding_proven": False,
            "foot_binding_proven": True,
            "foot_weight_flow_proven": True,
            "foot_weight_source_proven": True,
            "consumer_semantics": "retail_foot_route_proven_other_baked_target_routes_unproven_or_external",
            "weight_semantics": (
                "three_blackboard_key_lookup_absent_semantics_and_final_"
                "FootIKWeight_recurrence_proven_live_inputs_and_callback_order_incomplete"
            ),
            "retail_consumer_evidence": {
                "hand": "CharacterLimbIKBrain_external_interaction_exData_targets_not_baked_markers",
                "grounding": "GrounderBipedIK_solver_IKFootBoneL_R_exact_authored_foot_reference_PPtr_binding",
                "rig_jobs": "HGIKPrepareEffectors_HGPrepareIKEffector_HGTwoBoneIK",
                "knee": "authored_curve_marker_no_sampled_component_binding",
                "weapon": "authored_curve_marker_no_sampled_component_binding",
            },
            "foot_weight_source": foot_ik_scalar_curves.runtime_metadata(character_id),
            "ordinary_grounding": json.loads(json.dumps(GROUNDING_RUNTIME_POLICY)),
            "per_target_binding": {
                "foot": {
                    "status": "proven_grounding_reference_in_all_current_original_postmodels",
                    "source_postmodel_examples": [
                        "chr_0030_zhuangfy",
                        "chr_0003_endminf",
                        "chr_0026_lastrite",
                        "chr_0032_lizhiyan",
                        "chr_0033_camille",
                    ],
                    "source_roster_audit_count": grounder_profiles.expected_roster_count(),
                    "consumer": "GrounderBipedIK.solver.IKFootBoneL_R_to_Grounding",
                    "target": "IK_Foot_L_R_001",
                    "bipedik_limb_target": False,
                },
                "hand": {
                    "status": "external_interaction_target_not_baked_marker",
                    "consumer": "CharacterLimbIKBrain_via_CharLimbIKAction_exData",
                    "left_target_exdata_offset": "0x48",
                    "right_target_exdata_offset": "0x50",
                },
                "knee": {
                    "status": "no_sampled_original_component_binding",
                    "sampled_bipedik_bend_goals": "all_null",
                },
                "weapon": {
                    "status": "no_sampled_original_component_or_native_binding",
                },
            },
            "migration": "clear_legacy_guessed_0.65_0.35_0.15_weights_on_prefab_regeneration",
        },
        "left": {
            "upper": "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_L_Clavicle/Bip001_L_UpperArm",
            "forearm": "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_L_Clavicle/Bip001_L_UpperArm/Bip001_L_Forearm",
            "hand": "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_L_Clavicle/Bip001_L_UpperArm/Bip001_L_Forearm/Bip001_L_Hand",
            "target": "Root/IK_Root/IK_Hand_L_001",
        },
        "right": {
            "upper": "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_R_Clavicle/Bip001_R_UpperArm",
            "forearm": "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_R_Clavicle/Bip001_R_UpperArm/Bip001_R_Forearm",
            "hand": "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/Bip001_Spine2/Bip001_R_Clavicle/Bip001_R_UpperArm/Bip001_R_Forearm/Bip001_R_Hand",
            "target": "Root/IK_Root/IK_Hand_R_001",
        },
        "left_leg": {
            "upper": "Root/Bip001/Bip001_Pelvis/Bip001_L_Thigh",
            "forearm": "Root/Bip001/Bip001_Pelvis/Bip001_L_Thigh/Bip001_L_Calf",
            "hand": "Root/Bip001/Bip001_Pelvis/Bip001_L_Thigh/Bip001_L_Calf/Bip001_L_Foot",
            "target": "Root/IK_Foot_L_001",
            "pole": "Root/IK_Knee_L_001",
        },
        "right_leg": {
            "upper": "Root/Bip001/Bip001_Pelvis/Bip001_R_Thigh",
            "forearm": "Root/Bip001/Bip001_Pelvis/Bip001_R_Thigh/Bip001_R_Calf",
            "hand": "Root/Bip001/Bip001_Pelvis/Bip001_R_Thigh/Bip001_R_Calf/Bip001_R_Foot",
            "target": "Root/IK_Foot_R_001",
            "pole": "Root/IK_Knee_R_001",
        },
        "source_evidence": {
            "target_count": len(ik_targets),
            "targets": ik_targets,
            "all_configured_paths_exist": True,
        },
    }
    if character_id:
        profile = grounder_profiles.build_grounder_profile(
            character_id,
            {"transforms": transforms},
        )
        grounder_profiles.attach_profile_to_runtime(
            ik["runtime_solver"],
            profile,
        )
    for chain_name in ("left", "right", "left_leg", "right_leg"):
        for key, path in ik[chain_name].items():
            if key in {"upper", "forearm", "hand", "target", "pole"} and not exists(str(path)):
                ik["source_evidence"]["all_configured_paths_exist"] = False
    return ik


def attach_ik_clip_evidence(
    ik: dict[str, Any],
    clips: list[dict[str, Any]],
) -> dict[str, Any]:
    """Record authored rig-control bindings without inferring their consumer."""

    evidence_specs = {
        "hand_targets": ("/IK_Hand_L_001", "/IK_Hand_R_001"),
        "deforming_hands": ("/Bip001_L_Hand", "/Bip001_R_Hand"),
        "foot_targets": ("/IK_Foot_L_001", "/IK_Foot_R_001"),
        "knee_targets": ("/IK_Knee_L_001", "/IK_Knee_R_001"),
        "weapon_targets": ("/IK_Weapon_L_001", "/IK_Weapon_R_001"),
    }
    records: list[dict[str, Any]] = []
    for clip in clips:
        bones = list(clip.get("bones") or [])
        record: dict[str, Any] = {"clip": str(clip.get("name") or "")}
        for evidence_name, suffixes in evidence_specs.items():
            bindings = sorted(
                str(bone.get("path") or "")
                for bone in bones
                if str(bone.get("path") or "").endswith(suffixes)
                and any(bool(bone.get(key)) for key in ("pos_animated", "rot_animated", "scale_animated"))
            )
            record[f"authored_{evidence_name}_bindings"] = bindings
            record[f"has_any_{evidence_name}"] = bool(bindings)
            record[f"has_bilateral_{evidence_name}"] = len(bindings) == len(suffixes)
        record["evidence_boundary"] = (
            "AnimationClip transform bindings with at least one recovered animated "
            "position/rotation/scale channel; no runtime solver, constraint, pole, "
            "layer-timing, or weight inference"
        )
        records.append(record)
    ik["clip_binding_evidence"] = records
    summary: dict[str, Any] = {"clip_count": len(records)}
    for evidence_name in evidence_specs:
        bilateral_key = f"has_bilateral_{evidence_name}"
        any_key = f"has_any_{evidence_name}"
        bilateral_clips = [record["clip"] for record in records if record[bilateral_key]]
        partial_clips = [
            record["clip"]
            for record in records
            if record[any_key] and not record[bilateral_key]
        ]
        summary[f"clips_with_bilateral_{evidence_name}"] = bilateral_clips
        summary[f"bilateral_{evidence_name}_clip_count"] = len(bilateral_clips)
        summary[f"clips_with_partial_{evidence_name}"] = partial_clips
        summary[f"partial_{evidence_name}_clip_count"] = len(partial_clips)
        ik["source_evidence"][f"clips_with_bilateral_{evidence_name}"] = len(bilateral_clips)
        ik["source_evidence"][f"clips_with_partial_{evidence_name}"] = len(partial_clips)
    ik["clip_binding_summary"] = summary
    return ik


def is_acl_aux_sample(path: Path) -> bool:
    return path.name.endswith(".FloatBufferData.json") or path.name.endswith(".RootMotionBufferData.json")


def build_clip_path_index() -> dict[str, Path]:
    if not ANIMATION_CLIP_DIR.is_dir():
        return {}
    return {path.stem.lower(): path for path in ANIMATION_CLIP_DIR.glob("*.json")}


def discover_transform_sample_paths() -> list[Path]:
    if not ACL_SAMPLE_DIR.is_dir():
        return []
    paths: list[Path] = []
    for path in ACL_SAMPLE_DIR.glob("*.json"):
        if is_acl_aux_sample(path):
            continue
        if "zhuangfy" not in path.stem.lower():
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.name.lower())


def source_clip_counts(clip_paths_by_stem: dict[str, Path]) -> dict[str, int]:
    zhuangfy_source = [key for key in clip_paths_by_stem if "zhuangfy" in key]
    return {
        "source_zhuangfy_clip_count": len(zhuangfy_source),
        "source_actor_zhuangfy_clip_count": sum(1 for key in zhuangfy_source if key.startswith("a_actor_zhuangfy")),
        "source_item_widget_zhuangfy_clip_count": sum(1 for key in zhuangfy_source if "item_widget" in key),
        "transform_sample_json_count": len(discover_transform_sample_paths()),
        "transform_aux_sample_json_count": sum(
            1
            for path in ACL_SAMPLE_DIR.glob("*.json")
            if ACL_SAMPLE_DIR.is_dir() and "zhuangfy" in path.stem.lower() and is_acl_aux_sample(path)
        ),
    }


def preview_stride_for_sample_count(sample_count: int) -> int:
    if sample_count <= 120:
        return 1
    if sample_count <= 600:
        return 2
    if sample_count <= 1800:
        return 4
    return 8


def build_clip_manifest(transforms: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    transforms_by_crc = {int(item["path_crc"]): item for item in transforms}
    clip_paths_by_stem = build_clip_path_index()
    sample_paths = discover_transform_sample_paths()
    if not sample_paths:
        sample_paths = [ACL_SAMPLE_DIR / f"{clip_name}.json" for clip_name in PLAYBACK_ANIMATION_CLIPS]

    clips: list[dict[str, Any]] = []
    skipped = Counter()
    channel_evidence_counts = Counter()
    for sample_path in sample_paths:
        clip_name = sample_path.stem
        if not sample_path.is_file():
            skipped["missing_acl_sample_json"] += 1
            continue
        sample_data = load_acl_sample_summary(sample_path)
        if not sample_data.get("ok") or sample_data.get("track_type") != "qvvf":
            skipped["acl_sample_not_qvvf"] += 1
            continue
        clip_path = clip_paths_by_stem.get(clip_name.lower(), ANIMATION_CLIP_DIR / f"{clip_name}.json")
        sample_tail_metadata = load_acl_sample_tail_metadata(sample_path)
        sample_source_json = str(sample_data.get("source_json") or sample_tail_metadata.get("source_json") or "")
        if sample_source_json:
            sample_source_path = Path(sample_source_json)
            if not sample_source_path.is_absolute():
                sample_source_path = REPO_ROOT / sample_source_path
            if sample_source_path.is_file():
                clip_path = sample_source_path
        if not clip_path.is_file():
            skipped["missing_source_clip_json"] += 1
            continue
        info = parse_clip_bindings(clip_path, transforms_by_crc)
        sample_source = str(sample_data.get("sample_source") or "acl_transform_buffer")
        source_missing_bones = [bone for bone in info["bones"] if not bone.get("matched")]
        if sample_source == "unity_muscleclip_standard":
            try:
                remap_muscleclip_info_to_sample_bindings(info, sample_data, transforms_by_crc)
            except ValueError:
                skipped["invalid_muscleclip_compact_track_bindings"] += 1
                continue
        channel_evidence = "binding_presence_fallback"
        try:
            channel_analysis = analyze_qvvf_sample_channels(
                sample_path,
                int(info["transform_track_count"]),
                int(sample_data.get("num_samples") or 0),
            )
            apply_qvvf_channel_evidence(info, channel_analysis, transforms_by_crc)
            channel_evidence = "decoded_qvvf_frames"
        except (OSError, ValueError):
            # The clip remains useful if its sample metadata is readable but a
            # truncated or legacy frame payload cannot be analyzed.  The
            # parser's binding-presence flags are intentionally conservative.
            pass
        matched_bones = [bone for bone in info["bones"] if bone.get("matched") and bone.get("track_index") is not None]
        missing_bones = source_missing_bones
        if not matched_bones:
            skipped["no_recovered_body_transform_bindings"] += 1
            continue
        channel_evidence_counts[channel_evidence] += 1
        sample_count = int(sample_data.get("num_samples") or info["frame_count"] or 0)
        classification = classify_clip(clip_name)
        requirements = clip_requirements(clip_name, len(matched_bones), len(missing_bones))
        binding_evidence = clip_binding_evidence(clip_name)
        if sample_source == "unity_streamed_dense_constant":
            binding_evidence = "unity_streamed_dense_constant_zhuangfy_clip"
        elif sample_source == "unity_muscleclip_standard":
            binding_evidence = "unity_muscleclip_standard_transform_clip"
        search_text = " ".join(
            [
                clip_name,
                str(classification.get("clip_class") or ""),
                str(classification.get("clip_category") or ""),
                str(classification.get("layer_role") or ""),
                binding_evidence,
                sample_source,
                " ".join(requirements),
            ]
        )
        clips.append(
            {
                "name": info["name"],
                "sample_json": str(sample_path.resolve()),
                "sample_source": sample_source,
                "humanoid_layout": (
                    sample_data.get("humanoid_layout")
                    or sample_tail_metadata.get("humanoid_layout")
                    or {}
                ),
                "frame_count": sample_count,
                "sample_rate": float(sample_data.get("sample_rate") or info["sample_rate"] or 60.0),
                "duration": float(sample_data.get("duration") or info["stop_time"] or 0.0),
                "loop": bool(info["loop"] or ("loop" in clip_name.lower())),
                "loop_blend": bool(info.get("loop_blend") or False),
                "unity_preview_stride": preview_stride_for_sample_count(sample_count),
                "binding_evidence": binding_evidence,
                "transform_channel_evidence": channel_evidence,
                **classification,
                "requires_extra_items": requirements,
                "search_text": search_text,
                "matched_transform_count": len(matched_bones),
                "missing_transform_count": len(missing_bones),
                "output_track_count": int(info["output_track_count"] or sample_data.get("num_tracks") or 0),
                "bones": [
                    {
                        "path_crc": int(bone["path_crc"]),
                        "path": str(bone.get("path") or ""),
                        "name": str(bone.get("name") or ""),
                        "track_index": int(bone["track_index"]),
                        "pos_animated": bool(bone.get("pos_animated")),
                        "rot_animated": bool(bone.get("rot_animated")),
                        "scale_animated": bool(bone.get("scale_animated")),
                    }
                    for bone in matched_bones
                ],
            }
        )

    clip_class_counts = Counter(str(clip.get("clip_class") or "unknown") for clip in clips)
    layer_role_counts = Counter(str(clip.get("layer_role") or "unknown") for clip in clips)
    sample_source_counts = Counter(str(clip.get("sample_source") or "unknown") for clip in clips)
    standalone_body_dialog_candidates = sum(
        1
        for clip in clips
        if clip.get("clip_class") in {"standalone", "dialog"}
        or clip.get("layer_role") in {"body", "dialog_body"}
    )
    summary = {
        "clip_count": len(clips),
        "body_ready_clip_count": sum(1 for clip in clips if clip["matched_transform_count"] > 0),
        "clip_class_counts": dict(sorted(clip_class_counts.items())),
        "layer_role_counts": dict(sorted(layer_role_counts.items())),
        "sample_source_counts": dict(sorted(sample_source_counts.items())),
        "transform_channel_evidence_counts": dict(sorted(channel_evidence_counts.items())),
        "standalone_body_dialog_candidate_clip_count": standalone_body_dialog_candidates,
        "clips_requiring_extra_items": [
            {
                "name": clip["name"],
                "clip_class": clip["clip_class"],
                "layer_role": clip["layer_role"],
                "requires_extra_items": clip["requires_extra_items"],
            }
            for clip in clips
            if clip["requires_extra_items"]
        ],
    }
    source_counts = source_clip_counts(clip_paths_by_stem)
    summary.update(source_counts)
    summary.update(
        {
            "animation_clip_json_dir": str(ANIMATION_CLIP_DIR.resolve()),
            "acl_sample_dir": str(ACL_SAMPLE_DIR.resolve()),
            "candidate_transform_sample_count": len(sample_paths),
            "imported_transform_clip_count": len(clips),
            "skipped_transform_sample_count": sum(skipped.values()),
            "skipped_transform_sample_counts": dict(sorted(skipped.items())),
            "unsampled_source_zhuangfy_clip_count": max(
                0,
                source_counts["source_zhuangfy_clip_count"] - len(sample_paths),
            ),
        }
    )
    return clips, summary


def collect_usage(all_entries: list[dict[str, Any]]) -> dict[str, Any]:
    relevant_names = {
        "P_actor_zhuangfy_01",
        "P_actor_zhuangfy_02",
        "chr_0030_zhuangfy_postmodel",
        "data_facemorph_avatar_zhuangfy",
        "data_npc_montage_lady_zhuangfy_attackult02",
    }
    asset_hits: dict[str, list[dict[str, Any]]] = {name: [] for name in relevant_names}
    for entry in all_entries:
        name = str(entry.get("Name") or "")
        if name in relevant_names:
            asset_hits[name].append(
                {
                    "type": entry.get("Type", ""),
                    "container": entry.get("Container", ""),
                    "path_id": entry.get("PathID"),
                    "asset_root": entry.get("_asset_root", ""),
                }
            )

    facemorph_path = STREAMING / "json_by_type" / "MonoBehaviour" / "data_facemorph_avatar_zhuangfy.json"
    facemorph = {}
    if facemorph_path.is_file():
        data = load_json(facemorph_path)
        facemorph = {
            "avatarPath": data.get("avatarPath", ""),
            "prefabPath": data.get("prefabPath", ""),
            "tag": ((data.get("tag") or {}).get("tagName", "")),
            "basePoseConfigCount": len(((data.get("data") or {}).get("basePoseConfig") or [])),
        }

    timeline_path = REPO_ROOT / "scratch" / "timeline_line_orders.json"
    timeline_summary: dict[str, Any] = {"total_zhuangfy_lines": 0, "bindings": []}
    if timeline_path.is_file():
        timeline_data = load_json(timeline_path)
        lines = []
        for key, value in timeline_data.items():
            if key.startswith("_"):
                continue
            for line in value.get("lines") or []:
                haystack = " ".join(str(line.get(field, "")) for field in ("actor", "binding", "timeline")).lower()
                if "zhuangfy" in haystack:
                    lines.append(line)
        timeline_summary["total_zhuangfy_lines"] = len(lines)
        seen_bindings = []
        for line in lines:
            binding = str(line.get("binding") or "")
            if binding and binding not in seen_bindings:
                seen_bindings.append(binding)
        timeline_summary["bindings"] = seen_bindings[:20]
        timeline_summary["examples"] = [
            {
                "id": line.get("id", ""),
                "actor": line.get("actor", ""),
                "binding": line.get("binding", ""),
                "timeline": line.get("timeline", ""),
            }
            for line in lines[:12]
        ]

    return {
        "asset_hits": asset_hits,
        "facial_morph_avatar": facemorph,
        "timeline": timeline_summary,
        "interpretation": [
            "The base facial/dialog avatar points at P_actor_zhuangfy_01 and SK_actor_zhuangfy_01.fbx.",
            "The recovered postmodel prefab chr_0030_zhuangfy_postmodel binds twelve lod0 _01 renderer pieces; the viewer imports the nine non-VFX body/model renderers.",
            "P_actor_zhuangfy_02 appears in separate level sequence/cutscene/effect contexts and should not be mixed into the base _01 postmodel rebuild.",
        ],
    }


def main() -> int:
    transforms, id_to_path, path_to_data = load_hierarchy()
    by_type_path_id, all_entries = load_asset_entries()
    meshes, materials, renderer_summary = build_mesh_manifest(path_to_data, id_to_path, by_type_path_id)
    scene_transforms, scene_transform_summary = build_scene_transform_manifest(transforms, meshes)
    model_variants = build_experimental_model_variants(transforms, by_type_path_id, all_entries, materials)
    clips, animation_summary = build_clip_manifest(transforms)
    usage = collect_usage(all_entries)
    controller_recovery = collect_controller_recovery(by_type_path_id)
    clip_combinations = infer_clip_combinations(clips, controller_recovery)
    apply_clip_combinations(clips, clip_combinations)
    recovered_states = build_recovered_states(clips, clip_combinations, controller_recovery)
    ik = attach_ik_clip_evidence(
        build_ik_manifest(transforms, "chr_0030_zhuangfy"), clips
    )
    animation_summary["clip_combination_count"] = len(clip_combinations)
    animation_summary["auto_helper_combination_count"] = sum(1 for item in clip_combinations if item.get("auto_apply"))
    animation_summary["recovered_state_count"] = len(recovered_states)
    animation_summary["main_controller_layer_count"] = int(
        ((controller_recovery.get("main_controller") or {}).get("layer_count")) or 0
    )

    manifest = {
        "repo_root": str(REPO_ROOT.resolve()),
        "unity_version": "2022.3.62f3",
        "model": "actor_zhuangfy",
        "source": "original_unity_postmodel_dump",
        "original_prefab_root": ROOT_POSTMODEL_NAME,
        "active_variant": "P_actor_zhuangfy_01 / SK_actor_zhuangfy_01 / _01 postmodel",
        "transforms": transforms,
        "bones": transforms,
        "scene_transforms": scene_transforms,
        "meshes": meshes,
        "model_variants": model_variants,
        "materials": materials,
        "clips": clips,
        "ik": ik,
        "animation_controller_recovery": controller_recovery,
        "clip_combinations": clip_combinations,
        "recovered_states": recovered_states,
        "original_usage": usage,
        "renderer_summary": renderer_summary,
        "scene_transform_summary": scene_transform_summary,
        "animation_summary": animation_summary,
    }

    report = {
        "model": manifest["model"],
        "active_variant": manifest["active_variant"],
        "original_prefab_root": ROOT_POSTMODEL_NAME,
        "transform_count": len(transforms),
        "scene_transform_summary": scene_transform_summary,
        "renderer_summary": renderer_summary,
        "animation_summary": animation_summary,
        "animation_controller_recovery": controller_recovery,
        "clip_combinations": clip_combinations,
        "recovered_states": recovered_states,
        "ik": {
            "source": ik.get("source", ""),
            "status": ik.get("status", ""),
            "source_evidence": ik.get("source_evidence", {}),
        },
        "model_variants": [
            {
                "display_name": variant["display_name"],
                "source_model": variant["source_model"],
                "exact_postmodel": variant["exact_postmodel"],
                "mesh_count": len(variant["meshes"]),
                "notes": variant["notes"],
            }
            for variant in model_variants
        ],
        "lod0_renderers": [
            {
                "path": mesh["path"],
                "mesh": mesh["name"],
                "materials": mesh["material_names"],
                "root_bone_path": mesh["root_bone_path"],
                "bone_count": len(mesh["bone_paths"]),
            }
            for mesh in meshes
        ],
        "usage": usage,
    }

    write_json(OUTPUT, manifest)
    write_json(REPORT_OUTPUT, report)
    print(f"wrote {OUTPUT}")
    print(f"wrote {REPORT_OUTPUT}")
    print(
        f"transforms={len(transforms)} scene_transforms={len(scene_transforms)} lod0_renderers={len(meshes)} "
        f"all_renderers={renderer_summary['all_skinned_mesh_renderers']} clips={len(clips)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
