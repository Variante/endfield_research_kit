"""Validate actor-only Overview capture sidecars without opening Unity.

The validator deliberately treats alpha readback as an audit signal, never as
proof of a character matte. It is useful in CI or after a long editor capture
because it checks the source-clip ordering, complete loop coverage, frame
timestamps, and the fail-closed matte flag.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any, Dict, Iterable, List


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


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
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        errors.append("fps must be an integer in [1,120]")
    if payload.get("matte_verified") is not False:
        errors.append("matte_verified must remain false until an independent matte is verified")
    if payload.get("transparent_clear_requested") is not True:
        errors.append("transparent_clear_requested must be true")
    for field in (
        "reference_backdrop_disabled",
        "non_actor_renderers_disabled",
        "non_actor_ui_disabled",
        "actor_props_disabled",
    ):
        if payload.get(field) is not True:
            errors.append(f"{field} must be true for an actor-only capture")

    clips = payload.get("clips")
    if not isinstance(clips, list) or len(clips) != 2:
        errors.append("clips must contain exactly start and loop records")
        clips = []
    roles = [clip.get("role") for clip in clips if isinstance(clip, dict)]
    if roles != ["ui_overview_start", "ui_overview_loop"]:
        errors.append("clip roles must be ui_overview_start then ui_overview_loop")
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            errors.append(f"clips[{index}] must be an object")
            continue
        duration = clip.get("duration_seconds")
        if not _finite(duration) or float(duration) <= 0:
            errors.append(f"clips[{index}].duration_seconds must be positive and finite")
        count = clip.get("frame_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            errors.append(f"clips[{index}].frame_count must be positive")
    if clips and isinstance(clips[-1], dict):
        if clips[-1].get("loop_cycles") != 1:
            errors.append("loop clip must declare at least one loop cycle")

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
            if not isinstance(values, list) or len(values) != size or not all(
                _finite(value) for value in values
            ):
                errors.append(f"camera_contract.{field} must contain {size} finite values")
        for field in ("field_of_view", "near_clip_plane", "far_clip_plane"):
            if not _finite(camera.get(field)):
                errors.append(f"camera_contract.{field} must be finite")

    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        errors.append("frames must be non-empty")
        frames = []
    if frames and frames[0].get("phase") != "start":
        errors.append("first frame must be in start phase")
    if not any(isinstance(frame, dict) and frame.get("phase") == "loop" for frame in frames):
        errors.append("frames must contain a loop phase")
    previous_timestamp = -math.inf
    loop_phase_seconds = -math.inf
    loop_count = 0
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            errors.append(f"frames[{index}] must be an object")
            continue
        if frame.get("index") != index:
            errors.append(f"frames[{index}].index must equal its array index")
        timestamp = frame.get("timestamp_seconds")
        if not _finite(timestamp) or float(timestamp) < previous_timestamp:
            errors.append(f"frames[{index}] timestamps must be finite and non-decreasing")
        if _finite(timestamp):
            previous_timestamp = float(timestamp)
        phase = frame.get("phase")
        if phase not in ("start", "loop"):
            errors.append(f"frames[{index}].phase must be start or loop")
        if phase == "loop":
            loop_count += 1
            phase_seconds = frame.get("phase_seconds")
            if _finite(phase_seconds):
                loop_phase_seconds = max(loop_phase_seconds, float(phase_seconds))
        alpha = frame.get("alpha_audit")
        if not isinstance(alpha, dict):
            errors.append(f"frames[{index}].alpha_audit must be an object")
        elif not all(
            isinstance(alpha.get(name), int) and not isinstance(alpha.get(name), bool)
            for name in ("width", "height", "transparent_pixels", "nontransparent_pixels")
        ):
            errors.append(f"frames[{index}].alpha_audit dimensions/counts must be integers")

    if clips and len(clips) == 2 and isinstance(clips[1], dict):
        duration = clips[1].get("duration_seconds")
        if _finite(duration) and loop_count < 1:
            errors.append("loop duration cannot be represented without loop frames")
        if _finite(duration) and loop_phase_seconds >= 0 and loop_count > 1:
            # The final sampled phase plus one sample interval covers the full
            # source loop period. This tolerates a final frame just before the
            # exact endpoint, as the C# plan intentionally avoids duplicate loop
            # endpoints.
            if loop_phase_seconds + 1.0 / float(fps) + 1e-5 < float(duration):
                errors.append("loop frames do not cover one complete source period")

    alpha_summary = payload.get("alpha_audit")
    if not isinstance(alpha_summary, dict):
        errors.append("alpha_audit summary must be an object")
    else:
        if alpha_summary.get("matte_verified") is not False:
            errors.append("alpha_audit.matte_verified must remain false")
        if alpha_summary.get("frame_count") != len(frames):
            errors.append("alpha_audit.frame_count must match frames")

    limitations = payload.get("limitations")
    if not isinstance(limitations, list) or not any(
        isinstance(item, str) and "matteVerified=false" in item for item in limitations
    ):
        errors.append("limitations must explicitly document matteVerified=false")
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
