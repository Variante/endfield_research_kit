#!/usr/bin/env python3
"""Recover the exact UI-clip foot-IK scalar curves from original ACL payloads.

Only serialized Animator bindings with the three native-requested hashes are
classified. Missing bindings remain missing; this builder never supplies a
fallback value.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
CLIP_GLOB = (
    "scratch/character_ui_import/characters/**/animation_scopes/all-ui/"
    "animation_clips/AnimationClip/*.json"
)
DEFAULT_SAMPLER = (
    REPO_ROOT / "tools/endfield_acl_sampler/bin/endfield_acl_sampler.exe"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/"
    "playable_character_foot_ik_scalar_curves.json"
)
TEMP_ROOT = PROJECT_ROOT / "Temp/FootIkScalarCurveRecovery"
EXPECTED_CLIP_COUNT = 779
EXPECTED_FLOAT_BUFFER_CLIP_COUNT = 754
AUDITED_ANIMATOR_CONTROLLER_COUNT = 329

REQUESTED_VALUES = (
    {
        "runtime_name": "FootIKWeight",
        "blackboard_name": "FOOT_IK_WEIGHT",
        "string_literal_index": 12275,
        "attribute_hash_u32": 0x2B797234,
    },
    {
        "runtime_name": "FootIKFootWeight",
        "blackboard_name": "FOOT_IK_FOOT_WEIGHT",
        "string_literal_index": 12274,
        "attribute_hash_u32": 0xCF74E25B,
    },
    {
        "runtime_name": "FootIKAdsorbWeight",
        "blackboard_name": "FOOT_IK_ADSORB_WEIGHT",
        "string_literal_index": 12273,
        "attribute_hash_u32": 0x7E3D4086,
    },
)

FINAL_PELVIS_WEIGHT_RUNTIME = {
    "status": "exact_installed_base_path_recurrence_live_inputs_and_callback_order_pending",
    "rvas": {
        "update_foot_ik": "0x3413830",
        "get_floor_predict_theta": "0x351F220",
        "get_is_accelerating": "0x320D160",
        "get_is_playing_sp_idle": "0x3911100",
        "get_desired_gait": "0x3414EB0",
        "update_magica_cloth_ult_flag_writer": "0x3415160",
        "grounder_biped_update_clamp": "0x3E5EA60",
    },
    "blackboard_fields": {
        "m_footIKPelvisWeight": "CharacterAnimationBlackboard+0x28",
        "m_floorFeetTheta": "CharacterAnimationBlackboard+0x28C",
        "m_isInUltSkill": "CharacterAnimationBlackboard+0x341",
    },
    "grounding_fields": {
        "floorPredictTheta": "Grounding+0x28",
        "floorFeetThetaByFoot": "Grounding+0x2C",
        "floorFeetThetaByRoot": "Grounding+0x30",
        "invalid_theta_sentinel": -99.0,
    },
    "raw_curve_value": (
        "r=TryGetCurveValue(FootIKWeight); absent_key_returns_raw_zero"
    ),
    "grounded": {
        "acceleration_target": (
            "T0=isAccelerating?"
            "r+0.08*min(abs(floorPredictTheta)-10,0):r"
        ),
        "acceleration_effect": "nonpositive_penalty_in_range_minus_0_8_to_0",
        "special_idle_gate": (
            "isPlayingSpIdle_and_floorFeetThetaByFoot_gt_minus90_"
            "and_floorFeetThetaByRoot_gt_minus90"
        ),
        "special_idle_formula": (
            "d=min(abs(m_floorFeetTheta-floorFeetThetaByFoot),"
            "abs(floorFeetThetaByFoot-floorFeetThetaByRoot));"
            "q=clamp01((clamp(d,10,30)-10)*0.05);T=T0*(1-q)"
        ),
        "ordinary_target": "T=T0",
        "recurrence": (
            "m_isInUltSkill?T:W+(T-W)*clamp01("
            "((T>W_and_desiredGait_gt_0)?8:3)*deltaTime)"
        ),
        "desired_gait_values": {"Walk": 0, "Run": 1, "Sprint": 2},
    },
    "air": {
        "recurrence": "Wnew=W+(0-W)*clamp01(360*deltaTime)",
        "rate": 360.0,
    },
    "live_state_producers": {
        "isAccelerating": (
            "not_blockGroundedMove_and_moveMode_not_Animated_24_and_"
            "any_absolute_acceleration_component_gte_1e_minus5"
        ),
        "desiredGait_persistence_exception": "moveMode_Dash_20",
        "m_isInUltSkill": "current_skill_skillType_equals_UltimateSkill_7",
    },
    "writes": [
        "Wnew_to_CharacterAnimationBlackboard+0x28",
        "Wnew_to_GrounderBipedIK+0x18",
    ],
    "downstream_grounder_update": {
        "formula": "GrounderBipedIK.weight=clamp(GrounderBipedIK.weight,0,1)",
        "consumer_gate": "OnSolverUpdate_consumes_live_weight_only_when_gt_0_01",
        "callback_order_recovered": False,
        "do_not_collapse_into_blackboard_recurrence": True,
    },
    "final_pelvis_weight_recurrence_recovered": True,
    "live_controller_inputs_recovered": False,
    "numeric_original_frame_fixture_recovered": False,
}


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")


def _source_row(clip_path: Path, clip_name: str) -> dict[str, Any]:
    scope = clip_path.parents[2]
    matches: dict[tuple[Any, ...], dict[str, Any]] = {}
    for filter_path in sorted((scope / "filters").glob("*.json")):
        for row in json.loads(filter_path.read_text(encoding="utf-8")):
            if row.get("Name") != clip_name or row.get("Type") != "AnimationClip":
                continue
            row = dict(row)
            row["_source_filter"] = _relative(filter_path)
            row["_source_filter_mtime_ns"] = filter_path.stat().st_mtime_ns
            key = tuple(
                row.get(field)
                for field in ("Source", "Offset", "PathID", "Hash", "Container")
            )
            matches[key] = row
    if len(matches) == 1:
        return next(iter(matches.values()))
    path_id_match = re.search(r"_p([0-9A-Fa-f]{16})$", clip_path.stem)
    if path_id_match:
        unsigned_path_id = int(path_id_match.group(1), 16)
        selected = [
            row
            for row in matches.values()
            if (int(row.get("PathID") or 0) & 0xFFFFFFFFFFFFFFFF)
            == unsigned_path_id
        ]
        if len(selected) == 1:
            return selected[0]
        if selected:
            # Forced scoped refreshes retain old filters while replacing the
            # exported object. Prefer the newest exact-PathID filter only when
            # its filesystem generation time is unambiguous.
            selected.sort(
                key=lambda row: (
                    int(row["_source_filter_mtime_ns"]),
                    str(row["_source_filter"]),
                ),
                reverse=True,
            )
            if selected[0]["_source_filter_mtime_ns"] > selected[1][
                "_source_filter_mtime_ns"
            ]:
                return selected[0]
    raise RuntimeError(
        f"{clip_path}: expected one exact source filter row, found {len(matches)}"
    )


def _decode_float_buffer(
    *,
    clip_path: Path,
    encoded: str,
    sampler: Path,
    temp_root: Path,
) -> tuple[dict[str, Any], bytes]:
    raw = base64.b64decode(encoded)
    temp_root.mkdir(parents=True, exist_ok=True)
    acl_path = temp_root / f"{clip_path.stem}.FloatBufferData.acl"
    sample_path = temp_root / f"{clip_path.stem}.FloatBufferData.json"
    acl_path.write_bytes(raw)
    subprocess.run(
        [str(sampler), str(acl_path), str(sample_path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(sample_path.read_text(encoding="utf-8")), raw


def build_catalog(*, sampler: Path = DEFAULT_SAMPLER) -> dict[str, Any]:
    if not sampler.is_file():
        raise RuntimeError(f"ACL sampler is missing: {sampler}")
    clip_paths = sorted(REPO_ROOT.glob(CLIP_GLOB))
    if len(clip_paths) != EXPECTED_CLIP_COUNT:
        raise RuntimeError(
            f"expected {EXPECTED_CLIP_COUNT} current all-ui clips, found {len(clip_paths)}"
        )

    counts = {item["runtime_name"]: 0 for item in REQUESTED_VALUES}
    rows: list[dict[str, Any]] = []
    float_buffer_clip_count = 0
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    run_temp_root = Path(tempfile.mkdtemp(prefix="run-", dir=TEMP_ROOT))
    try:
        for clip_path in clip_paths:
            source_bytes = clip_path.read_bytes()
            clip = json.loads(source_bytes)
            acl = clip.get("m_AclCompressedBuffer") or {}
            encoded = str(acl.get("FloatBufferData") or "")
            animator_bindings = [
                (index, binding)
                for index, binding in enumerate(
                    (clip.get("m_ClipBindingConstant") or {}).get(
                        "genericBindings"
                    )
                    or []
                )
                if binding.get("typeID") == "Animator"
            ]
            float_curve_count = int(acl.get("FloatCurveCount") or 0)
            if encoded:
                float_buffer_clip_count += 1
                if float_curve_count != len(animator_bindings):
                    raise RuntimeError(
                        f"{clip_path}: FloatCurveCount={float_curve_count} but "
                        f"Animator bindings={len(animator_bindings)}"
                    )

            requested = []
            for requested_value in REQUESTED_VALUES:
                for scalar_track_index, (binding_index, binding) in enumerate(
                    animator_bindings
                ):
                    if int(binding.get("attribute") or 0) != int(
                        requested_value["attribute_hash_u32"]
                    ):
                        continue
                    requested.append(
                        (requested_value, scalar_track_index, binding_index, binding)
                    )
            if not requested:
                continue
            if not encoded:
                raise RuntimeError(f"{clip_path}: requested scalar has no float payload")
            sampled, raw = _decode_float_buffer(
                clip_path=clip_path,
                encoded=encoded,
                sampler=sampler,
                temp_root=run_temp_root,
            )
            source = _source_row(
                clip_path,
                str(clip.get("Name") or clip.get("m_Name") or clip_path.stem),
            )
            curve_rows = []
            for requested_value, track_index, binding_index, binding in requested:
                values = [
                    float(frame["tracks"][track_index]["value"])
                    for frame in sampled["frames"]
                ]
                name = str(requested_value["runtime_name"])
                counts[name] += 1
                curve_rows.append(
                    {
                        **requested_value,
                        "attribute_hash_hex": (
                            f"0x{int(requested_value['attribute_hash_u32']):08X}"
                        ),
                        "scalar_track_index": track_index,
                        "generic_binding_index": binding_index,
                        "generic_binding": binding,
                        "sample_count": len(values),
                        "sample_rate": float(sampled["sample_rate"]),
                        "duration": float(sampled["duration"]),
                        "minimum": min(values),
                        "maximum": max(values),
                        "first": values[0],
                        "last": values[-1],
                        "samples": values,
                    }
                )
            actor = next(part for part in clip_path.parts if part.startswith("chr_"))
            rows.append(
                {
                    "character_id": actor,
                    "clip_name": str(clip.get("Name") or clip.get("m_Name")),
                    "source_json": _relative(clip_path),
                    "source_json_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
                    "float_buffer_sha256": hashlib.sha256(raw).hexdigest().upper(),
                    "container": source.get("Container"),
                    "source_chunk": source.get("Source"),
                    "source_offset": source.get("Offset"),
                    "path_id": source.get("PathID"),
                    "asset_hash": source.get("Hash"),
                    "source_filter": source.get("_source_filter"),
                    "float_curve_count": float_curve_count,
                    "animator_binding_count": len(animator_bindings),
                    "curves": curve_rows,
                }
            )
    finally:
        # Multiple recovery/validation workers may build this catalog at once.
        # Each owns only its unique run directory; deleting the shared parent
        # here used to truncate another worker's sampler JSON mid-read.
        shutil.rmtree(run_temp_root, ignore_errors=True)
        try:
            TEMP_ROOT.rmdir()
        except OSError:
            pass

    if float_buffer_clip_count != EXPECTED_FLOAT_BUFFER_CLIP_COUNT:
        raise RuntimeError(
            f"expected {EXPECTED_FLOAT_BUFFER_CLIP_COUNT} float buffers, "
            f"found {float_buffer_clip_count}"
        )
    if counts != {
        "FootIKWeight": 24,
        "FootIKFootWeight": 0,
        "FootIKAdsorbWeight": 0,
    }:
        raise RuntimeError(f"unexpected requested-value binding counts: {counts}")
    if any(
        curve["minimum"] != 1.0 or curve["maximum"] != 1.0
        for row in rows
        for curve in row["curves"]
    ):
        raise RuntimeError("current FootIKWeight curves are not all exact constant one")
    rows.sort(key=lambda row: (row["character_id"], row["clip_name"], row["path_id"]))
    requested_summary = []
    for item in REQUESTED_VALUES:
        name = str(item["runtime_name"])
        if name == "FootIKWeight":
            lookup_semantics = (
                "present_key_reads_Animator_GetFloat_absent_key_raw_zero_"
                "then_exact_ground_air_acceleration_special_idle_ult_and_gait_"
                "recurrence"
            )
        elif name == "FootIKFootWeight":
            lookup_semantics = (
                "absent_key_raw_zero_complemented_to_grounded_target_one_"
                "then_native_two_per_second_persistent_lerp"
            )
        else:
            lookup_semantics = (
                "absent_key_raw_zero_complemented_to_immediate_final_one"
            )
        requested_summary.append(
            {
                **item,
                "attribute_hash_hex": f"0x{int(item['attribute_hash_u32']):08X}",
                "ui_clip_binding_count": counts[name],
                "clip_curve_status": (
                    "exact_acl_samples_recovered"
                    if counts[name]
                    else "absent_from_all_current_ui_clips"
                ),
                "lookup_and_absent_key_semantics": lookup_semantics,
            }
        )
    return {
        "schema": "endfield_original_foot_ik_scalar_curve_catalog_v1",
        "authoritative_inputs": {
            "source": "installed_game_vfs_AnimationClip_objects_and_GameAssembly_flow",
            "game_assembly_sha256": (
                "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
            ),
            "global_metadata_sha256": (
                "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
            ),
            "blackboard_update_rva": "0x3413830",
            "grounder_parameter_bridge_rva": "0x326CF60",
            "getter_rva": "0x2F963C0",
            "getter_public_wrapper_rva": "0x6C6F530",
            "getter_call_offsets": ["+0xF8", "+0x119", "+0x13A"],
        },
        "scope": {
            "unique_current_all_ui_clip_count": len(clip_paths),
            "nonempty_float_buffer_clip_count": float_buffer_clip_count,
            "binding_order_proof": (
                "FloatCurveCount_equals_Animator_binding_count_for_all_779_"
                "nonempty_buffers_scalar_tracks_follow_Animator_only_serialized_order"
            ),
        },
        "requested_values": requested_summary,
        "authored_curve_count": len(rows),
        "authored_actor_count": len({row["character_id"] for row in rows}),
        "authored_curves": rows,
        "runtime": {
            "three_requested_key_lookup_semantics_recovered": True,
            "absent_key_fallback_recovered": True,
            "complete_three_value_source_recovered": False,
            "complete_grounder_weight_outputs_recovered": False,
            "final_pelvis_weight_recurrence_recovered": True,
            "final_pelvis_weight_runtime": FINAL_PELVIS_WEIGHT_RUNTIME,
            "getter_contract": (
                "out_zeroed_before_lookup_absent_key_returns_false_and_zero_"
                "caller_ignores_boolean"
            ),
            "audited_original_animator_controller_count": (
                AUDITED_ANIMATOR_CONTROLLER_COUNT
            ),
            "audited_controller_requested_hash_count": 0,
            "default_enabled": False,
            "safe_import": "only_the_24_exact_FootIKWeight_arrays",
            "forbidden_fallback": (
                "do_not_synthesize_absent_FootIKFootWeight_or_FootIKAdsorbWeight"
            ),
        },
    }


@lru_cache(maxsize=1)
def load_catalog(path: Path = DEFAULT_OUTPUT) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def runtime_metadata(
    character_id: str | None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = catalog if catalog is not None else load_catalog()
    requested = [
        {
            **item,
            "attribute_hash_hex": f"0x{int(item['attribute_hash_u32']):08X}",
            "ui_clip_binding_count": None,
            "clip_curve_status": "catalog_not_built",
        }
        for item in REQUESTED_VALUES
    ]
    actor_rows: list[dict[str, Any]] = []
    catalog_status = "missing_generated_catalog"
    if catalog:
        requested = list(catalog.get("requested_values") or requested)
        catalog_status = "exact_original_acl_catalog_loaded"
        for row in catalog.get("authored_curves") or []:
            if row.get("character_id") != character_id:
                continue
            actor_rows.append(
                {
                    "clip_name": row.get("clip_name"),
                    "source_json": row.get("source_json"),
                    "path_id": row.get("path_id"),
                    "source_offset": row.get("source_offset"),
                    "scalar_track_index": row["curves"][0]["scalar_track_index"],
                    "sample_count": row["curves"][0]["sample_count"],
                    "sample_rate": row["curves"][0]["sample_rate"],
                    "constant_value": row["curves"][0]["minimum"],
                }
            )
    return {
        "status": (
            "three_key_lookup_and_final_pelvis_recurrence_recovered_"
            "live_inputs_and_callback_order_incomplete"
        ),
        "catalog_status": catalog_status,
        "catalog_asset": (
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/"
            "playable_character_foot_ik_scalar_curves.json"
        ),
        "requested_values": requested,
        "current_actor_exact_foot_ik_weight_curve_count": len(actor_rows),
        "current_actor_exact_foot_ik_weight_curves": actor_rows,
        "blackboard_update_rva": "0x3413830",
        "grounder_parameter_bridge_rva": "0x326CF60",
        "distance_heuristic_proven": False,
        "complete_three_value_source_recovered": False,
        "three_requested_key_lookup_semantics_recovered": True,
        "absent_key_fallback_recovered": True,
        "complete_grounder_weight_outputs_recovered": False,
        "final_pelvis_weight_recurrence_recovered": True,
        "final_pelvis_weight_runtime": json.loads(
            json.dumps(FINAL_PELVIS_WEIGHT_RUNTIME)
        ),
        "getter_contract": (
            "TryGetCurveValue_out_zero_before_lookup_absent_returns_false_zero_"
            "UpdateFootIK_ignores_boolean"
        ),
        "foot_ik_foot_weight_absent_key_result": (
            "raw_zero_to_grounded_target_one_then_two_per_second_persistent_lerp"
        ),
        "foot_ik_adsorb_weight_absent_key_result": "raw_zero_to_immediate_one",
        "foot_ik_weight_absent_key_result": (
            "raw_zero_then_exact_ground_air_acceleration_special_idle_ult_and_"
            "gait_recurrence"
        ),
        "audited_original_animator_controller_count": (
            AUDITED_ANIMATOR_CONTROLLER_COUNT
        ),
        "audited_controller_requested_hash_count": 0,
        "do_not_synthesize_absent_values": True,
    }


def refresh_catalog(
    *,
    output: Path = DEFAULT_OUTPUT,
    sampler: Path = DEFAULT_SAMPLER,
    check: bool = False,
) -> tuple[dict[str, Any], bool]:
    payload = build_catalog(sampler=sampler)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    current = output.read_text(encoding="utf-8") if output.is_file() else ""
    stale = current != encoded
    if stale and not check:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
        load_catalog.cache_clear()
    return payload, stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sampler", type=Path, default=DEFAULT_SAMPLER)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload, stale = refresh_catalog(
        output=args.output,
        sampler=args.sampler,
        check=args.check,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "ui_clip_count": payload["scope"]["unique_current_all_ui_clip_count"],
                "authored_curve_count": payload["authored_curve_count"],
                "authored_actor_count": payload["authored_actor_count"],
                "stale": stale,
                "mode": "check" if args.check else "write",
            },
            indent=2,
        )
    )
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
