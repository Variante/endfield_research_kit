#!/usr/bin/env python3
"""Verify Endminf overview ACL samples against generated Unity animation YAML.

The generated legacy clips retain one vector key for every selected ACL frame.
Unity supplies smooth component tangents for those keys, so integer-frame key
identity and fractional-frame interpolation are deliberately reported as two
separate contracts.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
ENDMINF_ROOT = (
    PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated"
    / "Characters" / "Playable" / "Endminf"
)
DEFAULT_MANIFEST = ENDMINF_ROOT / "endminf_ui_recovery_manifest.json"
DEFAULT_ANIMATION_DIR = ENDMINF_ROOT / "Animations"
TARGETS = (
    "A_actor_endminf_ui_overview_start",
    "A_actor_endminf_ui_overview_loop",
)
VECTOR_RE = re.compile(r"\{([^}]*)\}")
COMPONENT_RE = re.compile(r"([xyzw]):\s*([^,}]+)")


class ValidationError(RuntimeError):
    pass


def f32(value: Any) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def f32_bits(value: Any) -> bytes:
    return struct.pack("<f", float(value))


def parse_vector(text: str, components: str) -> tuple[float, ...]:
    match = VECTOR_RE.search(text)
    if not match:
        raise ValidationError(f"malformed Unity vector: {text.strip()}")
    values = {key: float(value) for key, value in COMPONENT_RE.findall(match.group(1))}
    if set(values) != set(components):
        raise ValidationError(f"Unity vector components differ from {components}: {text.strip()}")
    return tuple(values[key] for key in components)


def parse_anim_curves(path: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Parse only the three vector-curve arrays from force-text Unity YAML."""
    sections = {
        "m_RotationCurves": ("xyzw", {}),
        "m_PositionCurves": ("xyz", {}),
        "m_ScaleCurves": ("xyz", {}),
    }
    current_name: str | None = None
    current_curve: list[dict[str, Any]] | None = None
    pending: dict[str, Any] | None = None
    unnamed: list[list[dict[str, Any]]] = []

    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read Unity animation: {path}: {exc}") from exc
    with handle:
        for line_number, line in enumerate(handle, 1):
            header = re.match(r"^  (m_[A-Za-z]+Curves):(?:\s*\[\])?\s*$", line)
            if header:
                current_name = header.group(1) if header.group(1) in sections else None
                current_curve = None
                pending = None
                unnamed = []
                continue
            if current_name and re.match(r"^  m_", line):
                current_name = None
                current_curve = None
                pending = None
                continue
            if not current_name:
                continue
            if line.startswith("  - curve:"):
                current_curve = []
                unnamed.append(current_curve)
                pending = None
            elif current_curve is not None and line.startswith("        time:"):
                try:
                    pending = {"time": float(line.split(":", 1)[1])}
                except ValueError as exc:
                    raise ValidationError(f"{path}:{line_number}: malformed key time") from exc
            elif current_curve is not None and pending is not None and line.startswith("        value:"):
                pending["value"] = parse_vector(line, sections[current_name][0])
            elif current_curve is not None and pending is not None and line.startswith("        inSlope:"):
                pending["in_slope"] = parse_vector(line, sections[current_name][0])
            elif current_curve is not None and pending is not None and line.startswith("        outSlope:"):
                pending["out_slope"] = parse_vector(line, sections[current_name][0])
                current_curve.append(pending)
                pending = None
            elif current_curve is not None and line.startswith("    path:"):
                curve_path = line.split(":", 1)[1].strip()
                curves = sections[current_name][1]
                if curve_path in curves:
                    raise ValidationError(f"{path}: duplicate {current_name} path {curve_path!r}")
                curves[curve_path] = unnamed[-1]
                current_curve = None

    return {name: curves for name, (_, curves) in sections.items()}


def quaternion_normalize(value: tuple[float, ...]) -> tuple[float, ...]:
    norm = math.sqrt(sum(component * component for component in value))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValidationError(f"cannot normalize quaternion {value}")
    return tuple(component / norm for component in value)


def quaternion_nlerp(left: tuple[float, ...], right: tuple[float, ...], phase: float) -> tuple[float, ...]:
    if sum(a * b for a, b in zip(left, right)) < 0.0:
        right = tuple(-component for component in right)
    return quaternion_normalize(tuple(a + (b - a) * phase for a, b in zip(left, right)))


def hermite(left: dict[str, Any], right: dict[str, Any], phase: float) -> tuple[float, ...]:
    duration = right["time"] - left["time"]
    p2 = phase * phase
    p3 = p2 * phase
    h00, h10, h01, h11 = 2 * p3 - 3 * p2 + 1, p3 - 2 * p2 + phase, -2 * p3 + 3 * p2, p3 - p2
    return tuple(
        h00 * a + h10 * duration * out_slope + h01 * b + h11 * duration * in_slope
        for a, out_slope, b, in_slope in zip(
            left["value"], left["out_slope"], right["value"], right["in_slope"]
        )
    )


def quaternion_angle_degrees(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = abs(sum(a * b for a, b in zip(quaternion_normalize(left), quaternion_normalize(right))))
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot))))


def sampled_indices(frame_count: int, stride: int, loop: bool, duration: float, frames: list[dict[str, Any]]) -> list[int]:
    indices = [index for index in range(frame_count) if index % stride == 0 or index == frame_count - 1]
    if loop and frames and duration > float(frames[-1]["time"]) + 0.00001:
        indices.append(0)
    return indices


def validate_clip(
    clip: dict[str, Any], animation_dir: Path, *, phase: float, max_fractional_error: float | None,
    worst_limit: int,
) -> dict[str, Any]:
    name = str(clip["name"])
    sample_path = Path(str(clip["sample_json"]))
    anim_path = animation_dir / f"{name}.anim"
    try:
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{name}: source ACL sample JSON is unavailable: {sample_path}: {exc}") from exc
    if sample.get("ok") is not True or sample.get("hash_ok") is not True or sample.get("track_type") != "qvvf":
        raise ValidationError(f"{name}: source ACL sample validation fields are not valid qvvf evidence")
    frames = sample.get("frames")
    if not isinstance(frames, list) or len(frames) != int(sample.get("num_samples", -1)):
        raise ValidationError(f"{name}: source frame count does not match num_samples")
    if len(frames) != int(clip.get("frame_count", -1)):
        raise ValidationError(f"{name}: source frame count does not match manifest")

    curves = parse_anim_curves(anim_path)
    stride = int(clip.get("unity_preview_stride") or 1)
    duration = float(clip["duration"])
    loop = bool(clip["loop"])
    indices = sampled_indices(len(frames), stride, loop, duration, frames)
    failures: list[str] = []
    exact_keys = 0
    fractional: list[dict[str, Any]] = []
    flagged_paths: dict[str, set[str]] = {
        "m_RotationCurves": set(), "m_PositionCurves": set(), "m_ScaleCurves": set()
    }
    bones_by_path = {str(row["path"]): row for row in clip.get("bones") or []}

    channel_specs = (
        ("m_RotationCurves", "rot_animated", "rotation"),
        ("m_PositionCurves", "pos_animated", "translation"),
        ("m_ScaleCurves", "scale_animated", "scale"),
    )
    for section, flag, source_field in channel_specs:
        flagged_paths[section] = {
            str(bone["path"]) for bone in clip.get("bones") or [] if bone.get(flag)
        }
        missing_flagged = flagged_paths[section] - set(curves[section])
        if missing_flagged:
            failures.append(
                f"{section}: {len(missing_flagged)} manifest-flagged curve paths missing; "
                f"first={sorted(missing_flagged)[0]!r}"
            )
        for bone_path, keys in curves[section].items():
            bone = bones_by_path.get(bone_path)
            if bone is None:
                failures.append(f"{section}/{bone_path}: path has no ACL output-track binding")
                continue
            if not bone.get(flag):
                # The setup also emits two-key rest-pose hold curves for some
                # channels omitted by ACL's animated mask. They are not ACL
                # samples; require their complete constant-curve contract and
                # keep them out of the source-value/interpolation comparison.
                if len(keys) != 2:
                    failures.append(f"{section}/{bone_path}: expected 2 constant keys, found {len(keys)}")
                    continue
                if f32_bits(keys[0]["time"]) != f32_bits(0.0) or f32_bits(keys[1]["time"]) != f32_bits(duration):
                    failures.append(f"{section}/{bone_path}: constant key times are not 0 and {f32(duration)}")
                    continue
                if any(f32_bits(a) != f32_bits(b) for a, b in zip(keys[0]["value"], keys[1]["value"])):
                    failures.append(f"{section}/{bone_path}: constant endpoint values differ")
                    continue
                exact_keys += 2
                continue
            curve_indices = indices
            if len(keys) != len(curve_indices):
                failures.append(f"{section}/{bone_path}: expected {len(curve_indices)} keys, found {len(keys)}")
                continue
            track_index = int(bone["track_index"])
            for key_index, source_index in enumerate(curve_indices):
                source_frame = frames[source_index]
                loop_endpoint = (
                    loop and key_index == len(curve_indices) - 1
                    and source_index == 0
                )
                expected_time = duration if loop_endpoint else source_frame["time"]
                key = keys[key_index]
                expected_value = source_frame["tracks"][track_index][source_field]
                if f32_bits(key["time"]) != f32_bits(expected_time):
                    failures.append(f"{section}/{bone_path}[{key_index}]: time {key['time']} != {f32(expected_time)}")
                    break
                direct = all(
                    f32_bits(actual) == f32_bits(expected)
                    for actual, expected in zip(key["value"], expected_value)
                )
                # Unity's quaternion curve setter enforces sign continuity.
                # q and -q are the same rotation, but require every component
                # to be the exact float32 antipode; component-wise tolerance
                # would hide genuine key corruption.
                antipodal = section == "m_RotationCurves" and all(
                    f32_bits(actual) == f32_bits(-f32(expected))
                    for actual, expected in zip(key["value"], expected_value)
                )
                mismatches = [] if direct or antipodal else [
                    (axis, actual, f32(expected))
                    for axis, (actual, expected) in enumerate(zip(key["value"], expected_value))
                    if f32_bits(actual) != f32_bits(expected)
                ]
                if mismatches:
                    axis, actual, expected = mismatches[0]
                    failures.append(f"{section}/{bone_path}[{key_index}].value[{axis}]: {actual} != {expected}")
                    break
                exact_keys += 1

            if section == "m_RotationCurves" and len(keys) == len(curve_indices):
                for interval in range(len(keys) - 1):
                    source_left = quaternion_normalize(tuple(keys[interval]["value"]))
                    source_right = quaternion_normalize(tuple(keys[interval + 1]["value"]))
                    expected = quaternion_nlerp(source_left, source_right, phase)
                    unity = quaternion_normalize(hermite(keys[interval], keys[interval + 1], phase))
                    error = quaternion_angle_degrees(expected, unity)
                    fractional.append({
                        "error_degrees": error,
                        "path": bone_path,
                        "interval": interval,
                        "time": keys[interval]["time"] + (keys[interval + 1]["time"] - keys[interval]["time"]) * phase,
                    })

    fractional.sort(key=lambda row: (-row["error_degrees"], row["path"], row["interval"]))
    maximum = fractional[0]["error_degrees"] if fractional else 0.0
    if max_fractional_error is not None and maximum > max_fractional_error:
        failures.append(
            f"fractional quaternion error {maximum:.9g} degrees exceeds {max_fractional_error:.9g}"
        )
    return {
        "name": name,
        "sample_json": str(sample_path),
        "anim_yaml": str(anim_path),
        "source_frames": len(frames),
        "expected_sampled_keys_per_animated_curve": len(indices),
        "expected_keys_per_constant_curve": 2,
        "curve_counts": {section: len(rows) for section, rows in curves.items()},
        "manifest_flagged_curve_counts": {section: len(rows) for section, rows in flagged_paths.items()},
        "additional_constant_curve_counts": {
            section: len(set(curves[section]) - flagged_paths[section]) for section in curves
        },
        "exact_key_values_checked": exact_keys,
        "fractional_phase": phase,
        "fractional_rotation_intervals_checked": len(fractional),
        "max_fractional_quaternion_error_degrees": maximum,
        "worst_fractional_errors": fractional[:worst_limit],
        "failures": failures[:50],
        "failure_count": len(failures),
    }


def build_report(manifest_path: Path, animation_dir: Path, *, phase: float = 0.5,
                 max_fractional_error: float | None = None, worst_limit: int = 8) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"manifest is unavailable: {manifest_path}: {exc}") from exc
    clips = {str(row.get("name")): row for row in manifest.get("clips") or [] if isinstance(row, dict)}
    missing = [name for name in TARGETS if name not in clips]
    if missing:
        raise ValidationError(f"manifest lacks target clips: {', '.join(missing)}")
    results = [
        validate_clip(clips[name], animation_dir, phase=phase,
                      max_fractional_error=max_fractional_error, worst_limit=worst_limit)
        for name in TARGETS
    ]
    return {
        "schema": "endfield.endminf-overview-acl-anim-key-validation.v1",
        "ok": all(row["failure_count"] == 0 for row in results),
        "manifest": str(manifest_path),
        "fractional_error_is_diagnostic_only": max_fractional_error is None,
        "fractional_error_limit_degrees": max_fractional_error,
        "clips": results,
        "failure_count": sum(row["failure_count"] for row in results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--animation-dir", type=Path, default=DEFAULT_ANIMATION_DIR)
    parser.add_argument("--phase", type=float, default=0.5)
    parser.add_argument(
        "--max-fractional-error-degrees",
        type=float,
        help=(
            "optionally fail on the diagnostic midpoint quaternion difference; "
            "by default only exact recovered key identity is gated"
        ),
    )
    parser.add_argument("--worst-limit", type=int, default=8)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if not 0.0 < args.phase < 1.0:
        parser.error("--phase must be strictly between zero and one")
    if (args.max_fractional_error_degrees is not None
            and args.max_fractional_error_degrees < 0.0) or args.worst_limit < 0:
        parser.error("error limit and worst limit must be non-negative")
    try:
        report = build_report(args.manifest, args.animation_dir, phase=args.phase,
                              max_fractional_error=args.max_fractional_error_degrees,
                              worst_limit=args.worst_limit)
    except ValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
