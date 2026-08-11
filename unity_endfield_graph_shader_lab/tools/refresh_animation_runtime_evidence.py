#!/usr/bin/env python3
"""Refresh recovered animation ABI/IK/root-motion evidence without rebuilding caches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import character_manifest_common as common
from character_import import foot_ik_scalar_curves, grounder_profiles, ik_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_ROOT = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable"
)
IK_STATUS = "authored_targets_recovered_retail_foot_binding_proven_hand_targets_external"
IK_NOTE = (
    "All current-roster Grounder components bind sampled foot-reference "
    "fields to IK_Foot_L/R_001; these are Grounding inputs, not BipedIK limb targets. "
    "CharacterAnimationBlackboard requests three foot values, but the complete "
    "current UI-clip audit recovers only 24 exact FootIKWeight ACL curves and no "
    "FootIKFootWeight or FootIKAdsorbWeight bindings. Native TryGetCurveValue "
    "returns raw zero on an absent key; the latter two paths complement that to "
    "a smoothed target one and immediate one respectively. The final pelvis-weight "
    "ground/air recurrence and active MovementSetting Terrain|IK mask are exact, "
    "while live controller inputs, callback order, a source-compatible terrain "
    "provider, and numeric original-frame fixtures remain absent. BipedIK "
    "hand/foot targets and bend goals are null; CharacterLimbIKBrain receives hand "
    "targets from interaction exData, and no sampled component binds the baked knee "
    "or weapon markers. The quality-3 ordinary and root-aligned terrain, pelvis, "
    "length-clamp, and authored/procedural blend base paths are source-closed, while "
    "shared prediction/capsule branches and all non-foot policies remain disabled. "
    "The lab solver remains "
    "diagnostic and fail-closed."
)
RETAIL_CONSUMER_EVIDENCE = {
    "hand": "CharacterLimbIKBrain_external_interaction_exData_targets_not_baked_markers",
    "grounding": "GrounderBipedIK_solver_IKFootBoneL_R_exact_authored_foot_reference_PPtr_binding",
    "rig_jobs": "HGIKPrepareEffectors_HGPrepareIKEffector_HGTwoBoneIK",
    "knee": "authored_curve_marker_no_sampled_component_binding",
    "weapon": "authored_curve_marker_no_sampled_component_binding",
}
ROOT_MOTION_POLICY = {
    "motion_root_semantics": (
        "MotionT_Q_are_object_trajectory_RootT_Q_are_absolute_skeleton_body_reference"
    ),
    "sample_count_policy": "preserve_decoded_counts_never_synthesize_terminal_sample",
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
        "blocked_on": [
            "controller_transition_and_interruption_quaternion_blending",
            "loop_cycle_accumulation",
            "pipeline_time_semantics",
            "multiple_modifier_aggregation",
            "movement_mode_collision_cliff_and_motor_application",
        ],
    },
}


def refresh_layouts(value: Any) -> int:
    changed = 0
    if isinstance(value, dict):
        if value.get("layout") == "endfield_101_muscle_206_index":
            normalized = common.normalize_endfield_humanoid_layout(value)
            if normalized != value:
                value.clear()
                value.update(normalized)
                changed += 1
        for child in value.values():
            changed += refresh_layouts(child)
    elif isinstance(value, list):
        for child in value:
            changed += refresh_layouts(child)
    return changed


def refresh_ik(
    manifest: dict[str, Any],
    grounder_profile: dict[str, Any],
    foot_scalar_catalog: dict[str, Any],
) -> bool:
    ik = manifest.get("ik")
    if not isinstance(ik, dict):
        return False
    before = json.dumps(ik, sort_keys=True, ensure_ascii=False)
    ik["status"] = IK_STATUS
    ik["note"] = IK_NOTE
    runtime = ik.setdefault("runtime_solver", {})
    runtime.update(
        {
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
            "retail_consumer_evidence": dict(RETAIL_CONSUMER_EVIDENCE),
            "foot_weight_source": foot_ik_scalar_curves.runtime_metadata(
                str(manifest.get("character_id") or ""),
                foot_scalar_catalog,
            ),
            "ordinary_grounding": json.loads(
                json.dumps(common.GROUNDING_RUNTIME_POLICY)
            ),
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
        }
    )
    grounder_profiles.attach_profile_to_runtime(runtime, grounder_profile)
    return before != json.dumps(ik, sort_keys=True, ensure_ascii=False)


def refresh_root_motion(manifest: dict[str, Any]) -> bool:
    before = json.dumps(
        manifest.get("animation_runtime_recovery"),
        sort_keys=True,
        ensure_ascii=False,
    )
    runtime = manifest.setdefault("animation_runtime_recovery", {})
    runtime["root_motion"] = json.loads(json.dumps(ROOT_MOTION_POLICY))
    return before != json.dumps(runtime, sort_keys=True, ensure_ascii=False)


def manifest_paths() -> list[Path]:
    return sorted(MANIFEST_ROOT.glob("*/*_ui_recovery_manifest.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale manifests without writing and fail when any are stale",
    )
    args = parser.parse_args()

    paths = manifest_paths()
    expected_count = grounder_profiles.expected_roster_count()
    if len(paths) != expected_count:
        raise RuntimeError(
            f"expected {expected_count} playable manifests, found {len(paths)}"
        )

    stale: list[dict[str, Any]] = []
    foot_scalar_catalog, foot_scalar_catalog_stale = (
        foot_ik_scalar_curves.refresh_catalog(check=args.check)
    )
    for path in paths:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        grounder_profile = grounder_profiles.build_grounder_profile(
            str(manifest.get("character_id") or ""), manifest
        )
        layout_changes = refresh_layouts(manifest)
        ik_changed = refresh_ik(manifest, grounder_profile, foot_scalar_catalog)
        root_motion_changed = refresh_root_motion(manifest)
        if layout_changes or ik_changed or root_motion_changed:
            stale.append(
                {
                    "path": str(path),
                    "layout_changes": layout_changes,
                    "ik_changed": ik_changed,
                    "root_motion_changed": root_motion_changed,
                }
            )
            if not args.check:
                path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

    profile_catalog_stale = grounder_profiles.refresh_catalog(check=args.check)
    ik_evidence_catalog_stale = ik_evidence.refresh_playable_ik_evidence_catalog(
        check=args.check
    )
    print(
        json.dumps(
            {
                "manifest_count": len(paths),
                "stale_count": len(stale),
                "mode": "check" if args.check else "refresh",
                "stale": stale,
                "grounder_profile_catalog_stale": profile_catalog_stale,
                "foot_scalar_catalog_stale": foot_scalar_catalog_stale,
                "ik_evidence_catalog_stale": ik_evidence_catalog_stale,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if args.check and (
        stale
        or profile_catalog_stale
        or foot_scalar_catalog_stale
        or ik_evidence_catalog_stale
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
