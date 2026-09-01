#!/usr/bin/env python3
"""Build and verify source-derived Endminf effect AnimationClip curve semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any

from unity_muscleclip_sampler import ClipSampler, unity_crc32


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE = (
    PROJECT_ROOT
    / "scratch/character_recovery/endminf_external_fx_rig/"
    "exact_four_root_stage/AnimationClip"
)
ANIMATION_ROOT = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/"
    "Effects/Overview/Animation"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "endminf_effect_animation_source_curve_contract.json"
)
SPECS = (
    {
        "name": "A_actor_endminf_ui_overview_02",
        "source": "A_actor_endminf_ui_overview_02_p910F78E15CD34301.json",
        "sourceSha256": "22c191d15ea18dc2d890b9c6e4411e8e2985c6ea5fd6db96263b499e3d86a70d",
        "paths": ("Dummy002", "Dummy003", "Dummy004"),
        "expectedBindingCount": 30,
        "expectedKeyCount": 354,
    },
    {
        "name": "A_fx_endminf_ui_overview_04",
        "source": "A_fx_endminf_ui_overview_04_pDB8EF20719226683.json",
        "sourceSha256": "220ae359098e5a843afdced4680265e3eead2aba79b926988c5ba46ae6d42e6f",
        "paths": ("Sphere002", "Sphere003", "Sphere004", "Sphere005"),
        "expectedBindingCount": 28,
        "expectedKeyCount": 263,
    },
)
CHANNELS = {
    "translation": ("m_LocalPosition", "translation", "xyz"),
    "rotation": ("m_LocalRotation", "rotation", "xyzw"),
    "scale": ("m_LocalScale", "scale", "xyz"),
}
VECTOR_RE = re.compile(r"\{([^}]*)\}")
COMPONENT_RE = re.compile(r"([xyzw]):\s*([^,}]+)")


class SemanticError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise SemanticError(message)


def f32(value: Any) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def f32_bytes(value: Any) -> bytes:
    converted = f32(value)
    # Unity's AnimationCurve storage canonicalizes signed zero.
    if converted == 0.0:
        converted = 0.0
    return struct.pack("<f", converted)


def file_sha256(path: Path) -> str:
    require(path.is_file(), f"missing exact animation evidence: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def curve_key_sha256(keys: list[dict[str, float]]) -> str:
    payload = bytearray()
    for key in keys:
        payload.extend(f32_bytes(key["time"]))
        payload.extend(f32_bytes(key["value"]))
    return hashlib.sha256(payload).hexdigest()


def placeholder_transforms(paths: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            "name": path,
            "path": path,
            "path_crc": unity_crc32(path),
            "local_pos": [0.0, 0.0, 0.0],
            "local_rot": [0.0, 0.0, 0.0, 1.0],
            "local_scale": [1.0, 1.0, 1.0],
        }
        for path in paths
    ]


def derive_clip(spec: dict[str, Any]) -> dict[str, Any]:
    source_path = STAGE / str(spec["source"])
    source_sha = file_sha256(source_path)
    require(source_sha == spec["sourceSha256"],
            f"source AnimationClip hash drifted: {source_path.name}")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    sample = ClipSampler(
        source,
        placeholder_transforms(tuple(spec["paths"])),
    ).sample(source_path, include_frames=True)
    require(sample.get("ok") is True and sample.get("hash_ok") is True,
            f"source AnimationClip decode failed: {spec['name']}")
    require(not (sample.get("validation") or {}).get("unmatched_transform_path_count"),
            f"source AnimationClip retained an unmatched transform: {spec['name']}")
    frames = sample.get("frames") or []
    require(len(frames) == int(spec["expectedKeyCount"]),
            f"source frame count drifted: {spec['name']}")

    curves: list[dict[str, Any]] = []
    for binding in sample.get("track_bindings") or []:
        track_index = int(binding["track_index"])
        path = str(binding["path"])
        for channel in binding.get("declared_channels") or []:
            property_prefix, frame_field, axes = CHANNELS[str(channel)]
            for component, axis in enumerate(axes):
                keys = [
                    {
                        "time": f32(frame["time"]),
                        "value": f32(frame["tracks"][track_index][frame_field][component]),
                    }
                    for frame in frames
                ]
                curves.append({
                    "path": path,
                    "propertyName": f"{property_prefix}.{axis}",
                    "keyCount": len(keys),
                    "keyTimeValueSha256": curve_key_sha256(keys),
                })
    curves.sort(key=lambda row: (row["path"], row["propertyName"]))
    require(len(curves) == int(spec["expectedBindingCount"]),
            f"source binding count drifted: {spec['name']}")
    return {
        "name": spec["name"],
        "sourceFile": spec["source"],
        "sourceSha256": source_sha,
        "sampleRate": f32(sample["sample_rate"]),
        "duration": f32(sample["duration"]),
        "bindingCount": len(curves),
        "keyCountPerBinding": int(spec["expectedKeyCount"]),
        "curves": curves,
    }


def build_contract() -> dict[str, Any]:
    return {
        "schema": "endfield.endminf-effect-animation-source-curves.v1",
        "status": "source_derived_semantic_curve_contract",
        "derivation": {
            "decoder": "tools/unity_muscleclip_sampler.py::ClipSampler",
            "curveRule": "all source frames; declared Transform channels only",
            "keyDigest": "sha256(concat(float32_le(time),float32_le(value)))",
            "tangentRule": "Unity EnsureQuaternionContinuity smooth central derivative; endpoints one-sided",
            "weightRule": "WeightedMode.None with default one-third weights",
            "boundary": "No cached .anim bytes or capture-fitted values participate in expected curves.",
        },
        "clips": [derive_clip(spec) for spec in SPECS],
    }


def parse_vector(text: str, axes: str) -> tuple[float, ...]:
    match = VECTOR_RE.search(text)
    require(match is not None, f"malformed Unity vector: {text.strip()}")
    values = {key: f32(value) for key, value in COMPONENT_RE.findall(match.group(1))}
    require(set(values) == set(axes), f"Unity vector components drifted: {text.strip()}")
    return tuple(values[axis] for axis in axes)


def parse_generated_curves(path: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    sections = {
        "m_RotationCurves": ("m_LocalRotation", "xyzw"),
        "m_PositionCurves": ("m_LocalPosition", "xyz"),
        "m_ScaleCurves": ("m_LocalScale", "xyz"),
    }
    current: tuple[str, str] | None = None
    vector_keys: list[dict[str, Any]] | None = None
    pending: dict[str, Any] | None = None
    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        header = re.match(r"^  (m_[A-Za-z]+Curves):(?:\s*\[\])?\s*$", line)
        if header:
            current = sections.get(header.group(1))
            vector_keys = None
            pending = None
            continue
        if current and re.match(r"^  m_", line):
            current = None
            vector_keys = None
            pending = None
            continue
        if not current:
            continue
        prefix, axes = current
        if line.startswith("  - curve:"):
            vector_keys = []
            pending = None
        elif vector_keys is not None and line.startswith("        time:"):
            pending = {"time": f32(line.split(":", 1)[1])}
        elif pending is not None and line.startswith("        value:"):
            pending["value"] = parse_vector(line, axes)
        elif pending is not None and line.startswith("        inSlope:"):
            pending["inTangent"] = parse_vector(line, axes)
        elif pending is not None and line.startswith("        outSlope:"):
            pending["outTangent"] = parse_vector(line, axes)
        elif pending is not None and line.startswith("        tangentMode:"):
            pending["tangentMode"] = int(line.split(":", 1)[1])
        elif pending is not None and line.startswith("        weightedMode:"):
            pending["weightedMode"] = int(line.split(":", 1)[1])
        elif pending is not None and line.startswith("        inWeight:"):
            pending["inWeight"] = parse_vector(line, axes)
        elif pending is not None and line.startswith("        outWeight:"):
            pending["outWeight"] = parse_vector(line, axes)
            vector_keys.append(pending)
            pending = None
        elif vector_keys is not None and line.startswith("    path:"):
            curve_path = line.split(":", 1)[1].strip()
            for component, axis in enumerate(axes):
                key = (curve_path, f"{prefix}.{axis}")
                require(key not in result, f"duplicate generated binding: {key}")
                result[key] = [
                    {
                        "time": row["time"],
                        "value": row["value"][component],
                        "inTangent": row["inTangent"][component],
                        "outTangent": row["outTangent"][component],
                        "tangentMode": row["tangentMode"],
                        "weightedMode": row["weightedMode"],
                        "inWeight": row["inWeight"][component],
                        "outWeight": row["outWeight"][component],
                    }
                    for row in vector_keys
                ]
            vector_keys = None
    return result


def expected_tangent(keys: list[dict[str, Any]], index: int) -> float:
    if len(keys) <= 1:
        return 0.0
    left = max(0, index - 1)
    right = min(len(keys) - 1, index + 1)
    delta_time = f32(keys[right]["time"] - keys[left]["time"])
    if delta_time == 0.0:
        return 0.0
    return f32(f32(keys[right]["value"] - keys[left]["value"]) / delta_time)


def nearly(left: float, right: float) -> bool:
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= max(
        2.0e-5, abs(right) * 2.0e-4
    )


def validate_actual_curves(
    clip_contract: dict[str, Any],
    actual: dict[tuple[str, str], list[dict[str, Any]]],
) -> None:
    expected_rows = {
        (str(row["path"]), str(row["propertyName"])): row
        for row in clip_contract["curves"]
    }
    require(set(actual) == set(expected_rows),
            f"{clip_contract['name']}: generated binding set drifted")
    for binding, row in expected_rows.items():
        keys = actual[binding]
        require(len(keys) == int(row["keyCount"]),
                f"{clip_contract['name']}/{binding}: key count drifted")
        require(curve_key_sha256(keys) == row["keyTimeValueSha256"],
                f"{clip_contract['name']}/{binding}: key time/value drifted")
        for index, key in enumerate(keys):
            tangent = expected_tangent(keys, index)
            require(nearly(float(key["inTangent"]), tangent) and
                    nearly(float(key["outTangent"]), tangent),
                    f"{clip_contract['name']}/{binding}[{index}]: tangent drifted")
            require(int(key["tangentMode"]) == 0 and
                    int(key["weightedMode"]) == 0 and
                    nearly(float(key["inWeight"]), 1.0 / 3.0) and
                    nearly(float(key["outWeight"]), 1.0 / 3.0),
                    f"{clip_contract['name']}/{binding}[{index}]: tangent mode/weight drifted")


def verify_generated(contract: dict[str, Any]) -> None:
    for clip in contract["clips"]:
        path = ANIMATION_ROOT / f"{clip['name']}.anim"
        require(path.is_file(), f"missing generated AnimationClip: {path}")
        validate_actual_curves(clip, parse_generated_curves(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify the published contract and generated clips (default)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    contract = build_contract()
    verify_generated(contract)
    encoded = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        require(args.output.is_file(), f"missing published semantic contract: {args.output}")
        require(json.loads(args.output.read_text(encoding="utf-8")) == contract,
                "published semantic animation contract drifted")
    print("build_endminf_effect_animation_semantic_contract: OK " + json.dumps({
        "clips": len(contract["clips"]),
        "bindings": sum(row["bindingCount"] for row in contract["clips"]),
        "keys": sum(
            curve["keyCount"]
            for clip in contract["clips"] for curve in clip["curves"]
        ),
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
