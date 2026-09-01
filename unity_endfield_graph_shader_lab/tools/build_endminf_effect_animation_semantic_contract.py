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


def curve_payload_sha256(
    times: list[float],
    values: list[float],
    in_tangents: list[float],
    out_tangents: list[float],
    left_tangent_mode: int,
    right_tangent_mode: int,
    weighted_mode: int,
    in_weight: float,
    out_weight: float,
) -> str:
    require(
        len(times) == len(values) == len(in_tangents) == len(out_tangents),
        "curve payload arrays have different lengths",
    )
    payload = bytearray()
    for index, time in enumerate(times):
        payload.extend(f32_bytes(time))
        payload.extend(f32_bytes(values[index]))
        payload.extend(f32_bytes(in_tangents[index]))
        payload.extend(f32_bytes(out_tangents[index]))
        payload.extend(struct.pack("<i", int(left_tangent_mode)))
        payload.extend(struct.pack("<i", int(right_tangent_mode)))
        payload.extend(struct.pack("<i", int(weighted_mode)))
        payload.extend(f32_bytes(in_weight))
        payload.extend(f32_bytes(out_weight))
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

    key_times = [f32(frame["time"]) for frame in frames]
    tangent_mode = 0
    weighted_mode = 0
    in_weight = f32(1.0 / 3.0)
    out_weight = f32(1.0 / 3.0)
    curves: list[dict[str, Any]] = []
    for binding in sample.get("track_bindings") or []:
        track_index = int(binding["track_index"])
        path = str(binding["path"])
        for channel in binding.get("declared_channels") or []:
            property_prefix, frame_field, axes = CHANNELS[str(channel)]
            for component, axis in enumerate(axes):
                values = [
                    f32(frame["tracks"][track_index][frame_field][component])
                    for frame in frames
                ]
                keys = [
                    {"time": key_times[index], "value": value}
                    for index, value in enumerate(values)
                ]
                tangents = [
                    expected_tangent(keys, index)
                    for index in range(len(keys))
                ]
                curves.append({
                    "path": path,
                    "propertyName": f"{property_prefix}.{axis}",
                    "keyCount": len(keys),
                    "keyTimeValueSha256": curve_key_sha256(keys),
                    "keyPayloadSha256": curve_payload_sha256(
                        key_times,
                        values,
                        tangents,
                        tangents,
                        tangent_mode,
                        tangent_mode,
                        weighted_mode,
                        in_weight,
                        out_weight,
                    ),
                    "values": values,
                    "inTangents": tangents,
                    "outTangents": tangents,
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
        "keyTimes": key_times,
        "keySettings": {
            "leftTangentMode": tangent_mode,
            "rightTangentMode": tangent_mode,
            "weightedMode": weighted_mode,
            "inWeight": in_weight,
            "outWeight": out_weight,
        },
        "unityTransport": {
            "legacy": True,
            "compressed": False,
            "wrapMode": 0,
            "useHighQualityCurve": True,
        },
        "curves": curves,
    }


def build_contract() -> dict[str, Any]:
    return {
        "schema": "endfield.endminf-effect-animation-source-curves.v2",
        "status": "source_derived_rebuildable_curve_contract",
        "derivation": {
            "decoder": "tools/unity_muscleclip_sampler.py::ClipSampler",
            "curveRule": "all source frames; declared Transform channels only",
            "keyDigest": "sha256(concat(float32_le(time),float32_le(value)))",
            "payloadDigest": "sha256(per-key float32 time/value/in/out tangent, int32 left/right tangent modes, int32 weighted mode, float32 in/out weight)",
            "tangentRule": "Unity smooth float32 average of adjacent float32 secants; endpoints one-sided",
            "weightRule": "WeightedMode.None with default one-third weights",
            "storage": "clip-shared float32 keyTimes plus per-binding float32 values/inTangents/outTangents and shared exact key settings",
            "boundary": "Tracked payload is rederived only from exact serialized AnimationClip JSON; no cached .anim bytes or capture-fitted values participate.",
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

    def slope(left: int, right: int) -> float:
        delta_time = f32(keys[right]["time"] - keys[left]["time"])
        if delta_time == 0.0:
            return 0.0
        return f32(
            f32(keys[right]["value"] - keys[left]["value"]) / delta_time
        )

    if index == 0:
        return slope(0, 1)
    if index == len(keys) - 1:
        return slope(index - 1, index)
    # Unity's smooth-key result is the float32 average of the adjacent
    # float32 secants, not a single secant spanning both neighbours.
    return f32(f32(slope(index - 1, index) + slope(index, index + 1)) * f32(0.5))


def exact_f32(left: Any, right: Any) -> bool:
    return f32_bytes(left) == f32_bytes(right)


def is_exact_f32(value: Any) -> bool:
    return math.isfinite(float(value)) and float(value) == f32(value)


def validate_contract(contract: dict[str, Any]) -> None:
    require(
        contract.get("schema") ==
        "endfield.endminf-effect-animation-source-curves.v2" and
        contract.get("status") ==
        "source_derived_rebuildable_curve_contract",
        "semantic animation contract schema/status drifted",
    )
    clips = contract.get("clips")
    require(isinstance(clips, list) and len(clips) == len(SPECS),
            "semantic animation clip census drifted")
    expected_specs = {str(spec["name"]): spec for spec in SPECS}
    require({str(clip.get("name")) for clip in clips} == set(expected_specs),
            "semantic animation clip identity set drifted")
    for clip in clips:
        spec = expected_specs[str(clip["name"])]
        require(
            clip.get("sourceFile") == spec["source"] and
            clip.get("sourceSha256") == spec["sourceSha256"] and
            int(clip.get("bindingCount", -1)) == spec["expectedBindingCount"] and
            int(clip.get("keyCountPerBinding", -1)) == spec["expectedKeyCount"],
            f"semantic animation source identity drifted: {clip['name']}",
        )
        key_times = clip.get("keyTimes")
        require(
            isinstance(key_times, list) and
            len(key_times) == spec["expectedKeyCount"] and
            all(is_exact_f32(value)
                for value in key_times) and
            all(float(key_times[index]) > float(key_times[index - 1])
                for index in range(1, len(key_times))),
            f"semantic animation key-time payload drifted: {clip['name']}",
        )
        settings = clip.get("keySettings") or {}
        require(
            settings == {
                "leftTangentMode": 0,
                "rightTangentMode": 0,
                "weightedMode": 0,
                "inWeight": f32(1.0 / 3.0),
                "outWeight": f32(1.0 / 3.0),
            },
            f"semantic animation key settings drifted: {clip['name']}",
        )
        require(
            clip.get("unityTransport") == {
                "legacy": True,
                "compressed": False,
                "wrapMode": 0,
                "useHighQualityCurve": True,
            },
            f"semantic animation Unity transport drifted: {clip['name']}",
        )
        curves = clip.get("curves")
        require(isinstance(curves, list) and len(curves) == spec["expectedBindingCount"],
                f"semantic animation curve census drifted: {clip['name']}")
        identities = [(str(row.get("path")), str(row.get("propertyName")))
                      for row in curves]
        require(identities == sorted(identities) and
                len(set(identities)) == len(identities),
                f"semantic animation binding identities drifted: {clip['name']}")
        for row in curves:
            count = int(row.get("keyCount", -1))
            values = row.get("values")
            in_tangents = row.get("inTangents")
            out_tangents = row.get("outTangents")
            require(
                count == len(key_times) and
                all(isinstance(items, list) and len(items) == count
                    for items in (values, in_tangents, out_tangents)) and
                all(is_exact_f32(value)
                    for items in (values, in_tangents, out_tangents)
                    for value in items),
                f"semantic animation curve payload shape drifted: "
                f"{clip['name']}/{row.get('path')}/{row.get('propertyName')}",
            )
            keys = [
                {"time": key_times[index], "value": values[index]}
                for index in range(count)
            ]
            require(
                row.get("keyTimeValueSha256") == curve_key_sha256(keys) and
                row.get("keyPayloadSha256") == curve_payload_sha256(
                    key_times,
                    values,
                    in_tangents,
                    out_tangents,
                    int(settings["leftTangentMode"]),
                    int(settings["rightTangentMode"]),
                    int(settings["weightedMode"]),
                    float(settings["inWeight"]),
                    float(settings["outWeight"]),
                ),
                f"semantic animation curve digest drifted: "
                f"{clip['name']}/{row.get('path')}/{row.get('propertyName')}",
            )


def load_published_contract(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    require(path.is_file(), f"missing published semantic contract: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "published semantic contract is not an object")
    validate_contract(value)
    return value


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
        key_times = clip_contract["keyTimes"]
        settings = clip_contract["keySettings"]
        require(len(keys) == int(row["keyCount"]),
                f"{clip_contract['name']}/{binding}: key count drifted")
        require(curve_key_sha256(keys) == row["keyTimeValueSha256"],
                f"{clip_contract['name']}/{binding}: key time/value drifted")
        for index, key in enumerate(keys):
            require(exact_f32(key["time"], key_times[index]) and
                    exact_f32(key["value"], row["values"][index]),
                    f"{clip_contract['name']}/{binding}[{index}]: "
                    "exact float32 time/value drifted")
            require(exact_f32(key["inTangent"], row["inTangents"][index]) and
                    exact_f32(key["outTangent"], row["outTangents"][index]),
                    f"{clip_contract['name']}/{binding}[{index}]: tangent drifted")
            require(int(key["tangentMode"]) ==
                        int(settings["leftTangentMode"]) and
                    int(key["weightedMode"]) ==
                        int(settings["weightedMode"]) and
                    exact_f32(key["inWeight"], settings["inWeight"]) and
                    exact_f32(key["outWeight"], settings["outWeight"]),
                    f"{clip_contract['name']}/{binding}[{index}]: tangent mode/weight drifted")
        require(
            curve_payload_sha256(
                [key["time"] for key in keys],
                [key["value"] for key in keys],
                [key["inTangent"] for key in keys],
                [key["outTangent"] for key in keys],
                int(settings["leftTangentMode"]),
                int(settings["rightTangentMode"]),
                int(settings["weightedMode"]),
                float(settings["inWeight"]),
                float(settings["outWeight"]),
            ) == row["keyPayloadSha256"],
            f"{clip_contract['name']}/{binding}: exact key payload drifted",
        )


def verify_generated(contract: dict[str, Any]) -> None:
    for clip in contract["clips"]:
        path = ANIMATION_ROOT / f"{clip['name']}.anim"
        require(path.is_file(), f"missing generated AnimationClip: {path}")
        validate_actual_curves(clip, parse_generated_curves(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        "--update-from-source",
        dest="write",
        action="store_true",
        help="rederive and publish the tracked payload from exact source JSON",
    )
    mode.add_argument(
        "--check",
        "--check-source",
        dest="check_source",
        action="store_true",
        help="rederive from exact source JSON and compare with the publication (default)",
    )
    mode.add_argument(
        "--check-contract",
        action="store_true",
        help="validate only the tracked rebuildable payload (clean-checkout safe)",
    )
    mode.add_argument(
        "--check-generated",
        action="store_true",
        help="compare ignored generated .anim caches with the tracked payload",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.write:
        contract = build_contract()
        validate_contract(contract)
        encoded = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
        operation = "updated_from_source"
    elif args.check_contract:
        contract = load_published_contract(args.output)
        operation = "checked_tracked_contract"
    elif args.check_generated:
        contract = load_published_contract(args.output)
        verify_generated(contract)
        operation = "checked_generated_clips"
    else:
        contract = build_contract()
        validate_contract(contract)
        published = load_published_contract(args.output)
        require(published == contract,
                "published semantic animation contract drifted")
        operation = "checked_source_derivation"
    print("build_endminf_effect_animation_semantic_contract: OK " + json.dumps({
        "clips": len(contract["clips"]),
        "bindings": sum(row["bindingCount"] for row in contract["clips"]),
        "keys": sum(
            curve["keyCount"]
            for clip in contract["clips"] for curve in clip["curves"]
        ),
        "operation": operation,
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
