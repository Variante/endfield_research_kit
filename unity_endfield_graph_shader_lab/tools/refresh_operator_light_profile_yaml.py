#!/usr/bin/env python3
"""Refresh generated Unity profile light fields from recovered source JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return format(float(value), ".9g")


def color_yaml(value: dict[str, Any]) -> str:
    return (
        "{r: " + scalar(value["r"]) +
        ", g: " + scalar(value["g"]) +
        ", b: " + scalar(value["b"]) +
        ", a: " + scalar(value["a"]) + "}"
    )


def replace_or_insert(
    block: list[str],
    key: str,
    rendered_value: str,
    after_key: str,
) -> list[str]:
    prefix = "    " + key + ":"
    replacement = prefix + " " + rendered_value
    matches = [index for index, line in enumerate(block) if line.startswith(prefix)]
    require(len(matches) <= 1, f"duplicate profile field {key}")
    if matches:
        block[matches[0]] = replacement
        return block
    after_prefix = "    " + after_key + ":"
    anchors = [index for index, line in enumerate(block) if line.startswith(after_prefix)]
    require(len(anchors) == 1, f"missing profile anchor {after_key} for {key}")
    block.insert(anchors[0] + 1, replacement)
    return block


def refresh_text(
    profile_text: str,
    actor_key: str,
    operator_payload: dict[str, Any],
    render_payload: dict[str, Any],
) -> str:
    newline = "\r\n" if "\r\n" in profile_text else "\n"
    had_final_newline = profile_text.endswith(("\n", "\r"))
    lines = profile_text.splitlines()

    actor = operator_payload.get("actors", {}).get(actor_key)
    require(isinstance(actor, dict), f"operator source has no actor {actor_key}")
    source_rows = actor.get("lights")
    require(isinstance(source_rows, list) and source_rows, "operator source has no lights")
    require(actor.get("count") == len(source_rows), "operator source count mismatch")

    starts = [
        index for index, line in enumerate(lines)
        if line.startswith("  - sourceName: ")
    ]
    require(len(starts) == len(source_rows), "profile/source operator-light count mismatch")
    section_end = next(
        (index for index in range(starts[-1] + 1, len(lines))
         if lines[index].startswith("  characterLightingProvenance:")),
        len(lines),
    )

    rebuilt: list[str] = lines[:starts[0]]
    for row_index, start in enumerate(starts):
        end = starts[row_index + 1] if row_index + 1 < len(starts) else section_end
        block = lines[start:end]
        source = source_rows[row_index]
        expected_name = str(source.get("name") or "")
        require(
            block[0] == "  - sourceName: " + expected_name,
            f"profile/source identity mismatch at row {row_index}",
        )
        semantic = str(source.get("runtime_semantic_sha256") or "")
        require(len(semantic) == 64, f"missing semantic fingerprint at row {row_index}")
        replace_or_insert(
            block,
            "cullingBoxFalloffThreshold",
            scalar(source["culling_box_falloff_threshold"]),
            "falloffDistance",
        )
        replace_or_insert(
            block,
            "useFarDistanceShow",
            scalar(bool(source["use_far_distance_show"])),
            "cullingBoxFalloffThreshold",
        )
        replace_or_insert(
            block,
            "enableOverrideShadowLight",
            scalar(bool(source["enable_override_shadow_light"])),
            "useFarDistanceShow",
        )
        replace_or_insert(
            block,
            "sourceSemanticSha256",
            semantic,
            "followerSourceRawDataSha256",
        )
        rebuilt.extend(block)
    rebuilt.extend(lines[section_end:])

    serialized = render_payload.get("environment", {}).get("serialized", {})
    require(isinstance(serialized, dict), "render source environment is malformed")
    color_key = (
        "direct_custom_color"
        if int(serialized.get("direct_color_mode") or 0) == 1
        else "direct_color"
    )
    direct_color = serialized.get(color_key)
    require(isinstance(direct_color, dict), "render source direct color is missing")
    lighting_start = rebuilt.index("  characterLighting:")
    operator_start = rebuilt.index("  operatorLights:")
    lighting = rebuilt[lighting_start:operator_start]
    replace_or_insert(
        lighting,
        "sourceDirectColor",
        color_yaml(direct_color),
        "useRecoveredSourceMainLightDescriptor",
    )
    rebuilt = rebuilt[:lighting_start] + lighting + rebuilt[operator_start:]

    result = newline.join(rebuilt)
    if had_final_newline:
        result += newline
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", default="endminf")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--operator-lights", type=Path, required=True)
    parser.add_argument("--render-parameters", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    original = args.profile.read_text(encoding="utf-8")
    refreshed = refresh_text(
        original,
        args.actor.lower(),
        json.loads(args.operator_lights.read_text(encoding="utf-8")),
        json.loads(args.render_parameters.read_text(encoding="utf-8")),
    )
    if args.check:
        require(original == refreshed, f"profile is stale: {args.profile}")
        print(f"operator-light profile is current: {args.profile}")
        return 0
    args.profile.write_text(refreshed, encoding="utf-8", newline="")
    print(f"refreshed {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
