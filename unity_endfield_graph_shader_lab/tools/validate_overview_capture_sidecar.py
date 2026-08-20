"""Validate actor-only Overview capture sidecars without opening Unity.

Alpha readback remains an audit signal, never proof of a character matte.  A
capture is accepted only when every frame contains both a transparent clear
region and rendered actor pixels, all pixel counts cover the declared target,
and the sidecar describes a complete ``start -> transition -> loop`` sequence.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any, Dict, Iterable, List


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _in_range(value: Any, lower: float, upper: float, label: str, errors: List[str]) -> None:
    if not _finite(value):
        errors.append(f"{label} must be finite")
    elif float(value) < lower - 1e-5 or float(value) > upper + 1e-5:
        errors.append(f"{label} must be in [{lower},{upper}]")


def validate_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["sidecar root must be an object"]
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if payload.get("status") != "ok":
        errors.append("status must be ok")
    if not isinstance(payload.get("actor"), str) or not payload["actor"].strip():
        errors.append("actor must be a non-empty string")
    fps = payload.get("fps")
    if not _int(fps) or not 1 <= fps <= 120:
        errors.append("fps must be an integer in [1,120]")
    if payload.get("matte_verified") is not False:
        errors.append("matte_verified must remain false until an independent matte is verified")
    if payload.get("secondary_dynamics_verified") is not False:
        errors.append(
            "secondary_dynamics_verified must remain false until the retail solver is reproduced"
        )
    if payload.get("render_fidelity_status") != (
        "incomplete_missing_retail_secondary_dynamics_solver"
    ):
        errors.append("render_fidelity_status must expose the missing retail secondary-dynamics solver")
    if not isinstance(payload.get("secondary_dynamics_contract"), str) or not payload[
        "secondary_dynamics_contract"
    ].endswith("secondary_dynamics_owner_recovery.json"):
        errors.append("secondary_dynamics_contract must identify the recovered owner contract")
    if payload.get("transparent_clear_requested") is not True:
        errors.append("transparent_clear_requested must be true")
    if payload.get("transparent_pipeline_override_applied") is not True:
        errors.append("transparent_pipeline_override_applied must be true")
    if payload.get("transparent_post_process_disabled") is not True:
        errors.append("transparent_post_process_disabled must be true")
    if payload.get("transition_mode") != "state_weighted_crossfade_sample":
        errors.append("transition_mode must record state_weighted_crossfade_sample")
    for field in (
        "reference_backdrop_disabled",
        "non_actor_renderers_disabled",
        "non_actor_ui_disabled",
        "actor_props_disabled",
    ):
        if payload.get(field) is not True:
            errors.append(f"{field} must be true for an actor-only capture")

    exit_normalized = payload.get("controller_exit_normalized_time")
    _in_range(exit_normalized, 0.0, 1.25, "controller_exit_normalized_time", errors)
    transition_seconds = payload.get("controller_transition_seconds")
    if not _finite(transition_seconds) or float(transition_seconds) < 0:
        errors.append("controller_transition_seconds must be finite and non-negative")

    clips = payload.get("clips")
    if not isinstance(clips, list) or len(clips) != 3:
        errors.append("clips must contain start, transition, and loop records")
        clips = []
    roles = [clip.get("role") for clip in clips if isinstance(clip, dict)]
    if roles != [
        "ui_overview_start",
        "ui_overview_transition",
        "ui_overview_loop",
    ]:
        errors.append("clip roles must be ui_overview_start then transition then ui_overview_loop")
    clip_records: List[Dict[str, Any]] = []
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            errors.append(f"clips[{index}] must be an object")
            continue
        clip_records.append(clip)
        duration = clip.get("duration_seconds")
        if not _finite(duration) or float(duration) < 0 or (
            index != 1 and float(duration) <= 0
        ):
            errors.append(
                f"clips[{index}].duration_seconds must be "
                + ("non-negative and finite" if index == 1 else "positive and finite")
            )
        count = clip.get("frame_count")
        if not _int(count) or count < 0 or (index != 1 and count < 1):
            errors.append(f"clips[{index}].frame_count has an invalid value")
        for field in ("sequence_start_seconds", "sequence_end_seconds"):
            if not _finite(clip.get(field)):
                errors.append(f"clips[{index}].{field} must be finite")
        if _finite(clip.get("sequence_start_seconds")) and _finite(clip.get("sequence_end_seconds")):
            if float(clip["sequence_end_seconds"]) < float(clip["sequence_start_seconds"]) - 1e-5:
                errors.append(f"clips[{index}] sequence range must be non-decreasing")
    if clip_records and clip_records[-1].get("loop_cycles", 0) < 1:
        errors.append("loop clip must declare at least one loop cycle")
    if len(clip_records) == 3:
        if abs(float(clip_records[0].get("sequence_end_seconds", math.nan)) -
               float(clip_records[1].get("sequence_start_seconds", math.nan))) > 1e-4:
            errors.append("start/transition sequence boundary must match")
        if abs(float(clip_records[1].get("sequence_end_seconds", math.nan)) -
               float(clip_records[2].get("sequence_start_seconds", math.nan))) > 1e-4:
            errors.append("transition/loop sequence boundary must match")

    camera = payload.get("camera_contract")
    if not isinstance(camera, dict):
        errors.append("camera_contract must be an object")
    else:
        if not isinstance(camera.get("path"), str) or not camera["path"].strip():
            errors.append("camera_contract.path must be present")
        for field, size in (
            ("camera_position", 3),
            ("look_at_position", 3),
            ("serialized_vcam_rotation", 4),
        ):
            values = camera.get(field)
            if not isinstance(values, list) or len(values) != size or not all(_finite(value) for value in values):
                errors.append(f"camera_contract.{field} must contain {size} finite values")
        for field in ("field_of_view", "near_clip_plane", "far_clip_plane"):
            if not _finite(camera.get(field)):
                errors.append(f"camera_contract.{field} must be finite")

    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        errors.append("frames must be non-empty")
        frames = []
    phases = [frame.get("phase") for frame in frames if isinstance(frame, dict)]
    if phases:
        phase_rank = {"start": 0, "transition": 1, "loop": 2}
        previous_rank = -1
        for phase in phases:
            if phase not in phase_rank:
                errors.append("frames phases must be start, transition, or loop")
                continue
            rank = phase_rank[phase]
            if rank < previous_rank:
                errors.append("frames must follow strict start* -> transition* -> loop* order")
            previous_rank = max(previous_rank, rank)
        if phases[0] != "start":
            errors.append("first frame must be in start phase")
        if "loop" not in phases:
            errors.append("frames must contain a loop phase")
        if "transition" in phases and phases.index("transition") == 0:
            errors.append("transition cannot precede start frames")

    previous_timestamp = -math.inf
    previous_phase_seconds = -math.inf
    previous_phase_name = None
    frame_counts = {"start": 0, "transition": 0, "loop": 0}
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            errors.append(f"frames[{index}] must be an object")
            continue
        if frame.get("index") != index:
            errors.append(f"frames[{index}].index must equal its array index")
        timestamp = frame.get("timestamp_seconds")
        if not _finite(timestamp) or float(timestamp) < previous_timestamp - 1e-5:
            errors.append(f"frames[{index}] timestamps must be finite and non-decreasing")
        if _finite(timestamp):
            previous_timestamp = float(timestamp)
        phase = frame.get("phase")
        if phase in frame_counts:
            frame_counts[phase] += 1
        phase_seconds = frame.get("phase_seconds")
        clip_time = frame.get("clip_time_seconds")
        phase_normalized = frame.get("phase_normalized")
        if not _finite(phase_seconds):
            errors.append(f"frames[{index}].phase_seconds must be finite")
        if not _finite(clip_time):
            errors.append(f"frames[{index}].clip_time_seconds must be finite")
        if not _finite(phase_normalized):
            errors.append(f"frames[{index}].phase_normalized must be finite")
        if phase in ("start", "transition", "loop") and _finite(phase_seconds):
            if phase != previous_phase_name:
                previous_phase_seconds = -math.inf
            if phase_seconds < previous_phase_seconds - 1e-5:
                errors.append(f"frames[{index}].phase_seconds must be non-decreasing within a phase")
            previous_phase_seconds = float(phase_seconds)
            previous_phase_name = phase
        if phase == "start" and clip_records:
            _in_range(clip_time, 0.0, float(clip_records[0].get("duration_seconds", math.nan)),
                      f"frames[{index}].clip_time_seconds", errors)
            _in_range(phase_seconds, 0.0, float(clip_records[0].get("duration_seconds", math.nan)),
                      f"frames[{index}].phase_seconds", errors)
            _in_range(phase_normalized, 0.0, 1.0, f"frames[{index}].phase_normalized", errors)
        elif phase == "transition" and len(clip_records) >= 2:
            _in_range(clip_time, 0.0, float(clip_records[1].get("duration_seconds", math.nan)),
                      f"frames[{index}].clip_time_seconds", errors)
            _in_range(phase_seconds, 0.0, float(clip_records[1].get("duration_seconds", math.nan)),
                      f"frames[{index}].phase_seconds", errors)
            _in_range(phase_normalized, 0.0, 1.0, f"frames[{index}].phase_normalized", errors)
        elif phase == "loop" and len(clip_records) >= 3:
            _in_range(clip_time, 0.0, float(clip_records[2].get("duration_seconds", math.nan)),
                      f"frames[{index}].clip_time_seconds", errors)
            _in_range(phase_seconds, 0.0, float(clip_records[2].get("duration_seconds", math.nan)),
                      f"frames[{index}].phase_seconds", errors)
            _in_range(phase_normalized, 0.0, 1.0, f"frames[{index}].phase_normalized", errors)
        clip_name = frame.get("clip")
        if not isinstance(clip_name, str) or not clip_name.strip():
            errors.append(f"frames[{index}].clip must be a non-empty string")
        elif len(clip_records) == 3:
            expected = {"start": 0, "transition": 1, "loop": 2}.get(phase)
            if expected is not None and clip_name != clip_records[expected].get("name"):
                errors.append(f"frames[{index}].clip does not match its phase clip record")

        alpha = frame.get("alpha_audit")
        if not isinstance(alpha, dict):
            errors.append(f"frames[{index}].alpha_audit must be an object")
            continue
        if not all(_int(alpha.get(name)) for name in (
            "width", "height", "transparent_pixels", "nontransparent_pixels"
        )):
            errors.append(f"frames[{index}].alpha_audit dimensions/counts must be integers")
            continue
        width = alpha["width"]
        height = alpha["height"]
        transparent = alpha["transparent_pixels"]
        nontransparent = alpha["nontransparent_pixels"]
        if width <= 0 or height <= 0:
            errors.append(f"frames[{index}].alpha_audit dimensions must be positive")
        if transparent <= 0 or nontransparent <= 0:
            errors.append(f"frames[{index}] must contain both transparent and non-transparent pixels")
        if transparent < 0 or nontransparent < 0 or transparent + nontransparent != width * height:
            errors.append(f"frames[{index}].alpha_audit counts must sum to width*height")

    if clip_records:
        declared = sum(clip.get("frame_count", 0) for clip in clip_records if _int(clip.get("frame_count")))
        if declared != len(frames):
            errors.append("sum of clip frame_count values must match frames length")
        for phase, count in frame_counts.items():
            role_index = {"start": 0, "transition": 1, "loop": 2}[phase]
            if role_index < len(clip_records) and clip_records[role_index].get("frame_count") != count:
                errors.append(f"{phase} clip frame_count must match the number of {phase} frames")

    alpha_summary = payload.get("alpha_audit")
    if not isinstance(alpha_summary, dict):
        errors.append("alpha_audit summary must be an object")
    else:
        if alpha_summary.get("matte_verified") is not False:
            errors.append("alpha_audit.matte_verified must remain false")
        if alpha_summary.get("frame_count") != len(frames):
            errors.append("alpha_audit.frame_count must match frames")
        if alpha_summary.get("frames_with_transparent_pixels") != len(frames):
            errors.append("alpha_audit.frames_with_transparent_pixels must equal total frames")
        if alpha_summary.get("frames_with_nontransparent_pixels") != len(frames):
            errors.append("alpha_audit.frames_with_nontransparent_pixels must equal total frames")

    limitations = payload.get("limitations")
    if not isinstance(limitations, list) or not any(
        isinstance(item, str) and "matteVerified=false" in item for item in limitations
    ):
        errors.append("limitations must explicitly document matteVerified=false")
    if not isinstance(limitations, list) or not any(
        isinstance(item, str) and "secondaryDynamicsVerified=false" in item
        for item in limitations
    ):
        errors.append("limitations must explicitly document secondaryDynamicsVerified=false")
    if not isinstance(limitations, list) or not any(
        isinstance(item, str) and "transparent pass" in item.lower() and "post" in item.lower()
        for item in limitations
    ):
        errors.append("limitations must document that transparent pass excludes post processing")
    return errors


def validate_path(path: pathlib.Path) -> List[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: could not read JSON: {exc}"]
    return [f"{path}: {error}" for error in validate_payload(payload)]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sidecar", nargs="+", type=pathlib.Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    errors: List[str] = []
    for path in args.sidecar:
        errors.extend(validate_path(path))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"validated {len(args.sidecar)} overview capture sidecar(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
