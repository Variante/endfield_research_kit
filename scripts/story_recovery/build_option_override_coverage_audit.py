#!/usr/bin/env python3
"""Audit WebUI option-warning coverage by manual option overrides.

This report separates raw recovery uncertainty from WebUI display coverage. It
checks current generated conversation warnings against `webui/overrides/options.json`
and validates that manual option anchors and response targets still point at
existing generated line/option IDs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, STORY_OPTION_REPORTS_DIR, md_escape, read_json, rel_path, write_report_json

OPTION_WARNING_CODES = {"inferredOptionLayout", "inferredOptionResponse"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit generated option warnings against WebUI option overrides.",
    )
    parser.add_argument("--language", default="CN", help="Language code to audit. Defaults to CN.")
    parser.add_argument(
        "--conv-root",
        type=Path,
        default=None,
        help="Conversation JSON directory. Defaults to webui/data/lang/<language>/conv.",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=ROOT / "webui" / "overrides" / "options.json",
        help="Option override JSON path.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=None,
        help="Output prefix without extension. Defaults to reports/story/recovery/options/option_override_coverage_<language>.",
    )
    return parser.parse_args(argv)


def safe_str(value: Any) -> str:
    return str(value) if value not in (None, "") else ""


def as_group(value: Any) -> str:
    text = safe_str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = safe_str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def load_conversations(conv_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(conv_root.glob("*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            rows.append((path, payload))
    return rows


def line_ids(conv: dict[str, Any]) -> set[str]:
    return {
        safe_str(line.get("id"))
        for line in conv.get("lines") or []
        if isinstance(line, dict) and safe_str(line.get("id"))
    }


def option_groups(conv: dict[str, Any]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for group in conv.get("optionGroups") or []:
        if not isinstance(group, dict):
            continue
        group_id = as_group(group.get("g"))
        if not group_id:
            continue
        values = groups.setdefault(group_id, set())
        for option in group.get("options") or []:
            if isinstance(option, dict) and safe_str(option.get("id")):
                values.add(safe_str(option.get("id")))
    return groups


def normalize_positions(scene_override: dict[str, Any]) -> tuple[dict[str, list[str]], set[str]]:
    positions = scene_override.get("positions") if isinstance(scene_override, dict) else {}
    positions = positions if isinstance(positions, dict) else {}
    after_raw = positions.get("after") if isinstance(positions.get("after"), dict) else {}
    after: dict[str, list[str]] = {}
    for anchor, groups in after_raw.items():
        if isinstance(groups, list):
            after[safe_str(anchor)] = [as_group(group) for group in groups if as_group(group)]
    pre_raw = positions.get("pre") if isinstance(positions.get("pre"), list) else []
    pre = {as_group(group) for group in pre_raw if as_group(group)}
    return after, pre


def normalize_responses(scene_override: dict[str, Any]) -> dict[str, list[str]]:
    responses = scene_override.get("responses") if isinstance(scene_override, dict) else {}
    if not isinstance(responses, dict):
        return {}
    out: dict[str, list[str]] = {}
    for option_id, targets in responses.items():
        if isinstance(targets, list):
            out[safe_str(option_id)] = [safe_str(target) for target in targets if safe_str(target)]
    return out


def position_override_status(
    group_id: str,
    *,
    positions_after: dict[str, list[str]],
    positions_pre: set[str],
    known_lines: set[str],
    known_groups: dict[str, set[str]],
) -> tuple[str, list[str]]:
    problems: list[str] = []
    if group_id not in known_groups:
        problems.append(f"missing option group {group_id}")
    if group_id in positions_pre:
        return ("manual-covered" if not problems else "invalid-override", problems)
    matching_anchors = [anchor for anchor, groups in positions_after.items() if group_id in groups]
    if not matching_anchors:
        return ("uncovered", problems)
    missing_anchors = [anchor for anchor in matching_anchors if anchor not in known_lines]
    if missing_anchors:
        problems.extend(f"missing anchor line {anchor}" for anchor in missing_anchors)
    return ("manual-covered" if not problems else "invalid-override", problems)


def response_override_status(
    option_ids: list[str],
    *,
    responses: dict[str, list[str]],
    known_lines: set[str],
    known_option_ids: set[str],
) -> tuple[str, list[str], list[str], list[str]]:
    problems: list[str] = []
    covered: list[str] = []
    missing: list[str] = []
    for option_id in option_ids:
        if option_id not in known_option_ids:
            problems.append(f"missing option id {option_id}")
        targets = responses.get(option_id) or []
        if not targets:
            missing.append(option_id)
            continue
        bad_targets = [target for target in targets if target not in known_lines]
        if bad_targets:
            problems.extend(f"{option_id} targets missing line {target}" for target in bad_targets)
            continue
        covered.append(option_id)
    if problems:
        status = "invalid-override"
    elif covered and not missing:
        status = "manual-covered"
    elif covered:
        status = "partially-covered"
    else:
        status = "uncovered"
    return status, problems, covered, missing


def classify_conversation(
    path: Path,
    conv: dict[str, Any],
    scene_override: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = safe_str(conv.get("key")) or path.stem
    known_lines = line_ids(conv)
    groups = option_groups(conv)
    known_option_ids = {option_id for values in groups.values() for option_id in values}
    positions_after, positions_pre = normalize_positions(scene_override)
    responses = normalize_responses(scene_override)
    warning_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []

    for warning in conv.get("warnings") or []:
        if not isinstance(warning, dict):
            continue
        code = safe_str(warning.get("code"))
        if code == "inferredOptionLayout":
            for detail in warning.get("groupDetails") or []:
                if not isinstance(detail, dict):
                    continue
                group_id = as_group(detail.get("group"))
                status, problems = position_override_status(
                    group_id,
                    positions_after=positions_after,
                    positions_pre=positions_pre,
                    known_lines=known_lines,
                    known_groups=groups,
                )
                warning_rows.append({
                    "scene": key,
                    "file": rel_path(path),
                    "code": code,
                    "unit": "group",
                    "group": group_id,
                    "classification": status,
                    "warningReason": safe_str(warning.get("reason")),
                    "warningStatus": safe_str(detail.get("status")),
                    "warningAfter": safe_str(detail.get("after")),
                    "overrideAfter": [anchor for anchor, values in positions_after.items() if group_id in values],
                    "overridePre": group_id in positions_pre,
                    "optionIds": unique([safe_str(value) for value in detail.get("optionIds") or []]),
                    "problems": problems,
                })
        elif code == "inferredOptionResponse":
            for group in warning.get("groups") or []:
                if not isinstance(group, dict):
                    continue
                option_ids = unique([safe_str(value) for value in group.get("optionIds") or []])
                status, problems, covered, missing = response_override_status(
                    option_ids,
                    responses=responses,
                    known_lines=known_lines,
                    known_option_ids=known_option_ids,
                )
                warning_rows.append({
                    "scene": key,
                    "file": rel_path(path),
                    "code": code,
                    "unit": "group",
                    "group": as_group(group.get("group")),
                    "classification": status,
                    "warningReason": safe_str(group.get("reason")) or safe_str(warning.get("reason")),
                    "warningSource": safe_str(group.get("source")),
                    "after": safe_str(group.get("after")),
                    "optionIds": option_ids,
                    "candidateLineIds": unique([safe_str(value) for value in group.get("candidateLineIds") or []]),
                    "coveredOptionIds": covered,
                    "missingOptionIds": missing,
                    "overrideTargets": {option_id: responses.get(option_id, []) for option_id in option_ids if option_id in responses},
                    "problems": problems,
                })

    for anchor, values in positions_after.items():
        if anchor not in known_lines:
            validation_rows.append({"scene": key, "kind": "position", "anchor": anchor, "groups": values, "problem": "missing anchor line"})
        for group_id in values:
            if group_id not in groups:
                validation_rows.append({"scene": key, "kind": "position", "anchor": anchor, "group": group_id, "problem": "missing option group"})
    for group_id in positions_pre:
        if group_id not in groups:
            validation_rows.append({"scene": key, "kind": "position", "group": group_id, "problem": "missing option group"})
    for option_id, targets in responses.items():
        if option_id not in known_option_ids:
            validation_rows.append({"scene": key, "kind": "response", "optionId": option_id, "targets": targets, "problem": "missing option id"})
        for target in targets:
            if target not in known_lines:
                validation_rows.append({"scene": key, "kind": "response", "optionId": option_id, "target": target, "problem": "missing target line"})

    return warning_rows, validation_rows


def build_payload(language: str, conv_root: Path, overrides_path: Path) -> dict[str, Any]:
    overrides_payload = read_json(overrides_path, {})
    overrides = overrides_payload.get("scenes") if isinstance(overrides_payload, dict) else {}
    overrides = overrides if isinstance(overrides, dict) else {}
    conversations = load_conversations(conv_root)

    warning_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    warning_scene_keys: set[str] = set()
    raw_warning_counts: Counter[str] = Counter()
    option_warning_conversations: set[str] = set()

    for path, conv in conversations:
        key = safe_str(conv.get("key")) or path.stem
        scene_override = overrides.get(key) if isinstance(overrides.get(key), dict) else {}
        for warning in conv.get("warnings") or []:
            if isinstance(warning, dict):
                code = safe_str(warning.get("code"))
                raw_warning_counts[code] += 1
                warning_scene_keys.add(key)
                if code in OPTION_WARNING_CODES:
                    option_warning_conversations.add(key)
        rows, validations = classify_conversation(path, conv, scene_override)
        warning_rows.extend(rows)
        validation_rows.extend(validations)

    classification_counts = Counter(row.get("classification") for row in warning_rows)
    code_class_counts: dict[str, dict[str, int]] = {}
    for row in warning_rows:
        code = safe_str(row.get("code"))
        status = safe_str(row.get("classification"))
        code_class_counts.setdefault(code, {})[status] = code_class_counts.setdefault(code, {}).get(status, 0) + 1

    override_scene_count = len(overrides)
    override_scenes_with_positions = sum(
        1 for scene in overrides.values()
        if isinstance(scene, dict) and isinstance(scene.get("positions"), dict) and scene.get("positions")
    )
    override_scenes_with_responses = sum(
        1 for scene in overrides.values()
        if isinstance(scene, dict) and isinstance(scene.get("responses"), dict) and scene.get("responses")
    )

    return {
        "generated": int(time.time()),
        "language": language,
        "source": {
            "convRoot": rel_path(conv_root),
            "overrides": rel_path(overrides_path),
        },
        "counts": {
            "conversations": len(conversations),
            "warningConversations": len(warning_scene_keys),
            "optionWarningConversations": len(option_warning_conversations),
            "rawWarnings": dict(sorted(raw_warning_counts.items())),
            "optionWarningUnits": len(warning_rows),
            "classifications": dict(sorted(classification_counts.items())),
            "byCode": code_class_counts,
            "overrideScenes": override_scene_count,
            "overrideScenesWithPositions": override_scenes_with_positions,
            "overrideScenesWithResponses": override_scenes_with_responses,
            "invalidOverrideReferences": len(validation_rows),
        },
        "warningRows": warning_rows,
        "invalidOverrideReferences": validation_rows,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    counts = payload.get("counts") or {}
    rows = payload.get("warningRows") or []
    invalid = payload.get("invalidOverrideReferences") or []
    lines: list[str] = [
        f"# Option Override Coverage Audit ({payload.get('language')})",
        "",
        "This generated audit distinguishes raw option-recovery warnings from WebUI manual override coverage.",
        "A `manual-covered` classification means the current override file validates against generated line and option IDs; it is display coverage, not independent runtime proof.",
        "",
        "## Summary",
        "",
        f"- Conversations scanned: {counts.get('conversations', 0)}",
        f"- Conversations with any warning: {counts.get('warningConversations', 0)}",
        f"- Conversations with option warnings: {counts.get('optionWarningConversations', 0)}",
        f"- Option warning units audited: {counts.get('optionWarningUnits', 0)}",
        f"- Override scenes: {counts.get('overrideScenes', 0)} ({counts.get('overrideScenesWithPositions', 0)} with positions, {counts.get('overrideScenesWithResponses', 0)} with responses)",
        f"- Invalid override references: {counts.get('invalidOverrideReferences', 0)}",
        "",
        "### Raw Warning Counts",
        "",
    ]
    for code, value in (counts.get("rawWarnings") or {}).items():
        lines.append(f"- `{code}`: {value}")
    lines.extend(["", "### Option Warning Classifications", ""])
    for status, value in (counts.get("classifications") or {}).items():
        lines.append(f"- `{status}`: {value}")
    lines.extend(["", "### By Warning Code", ""])
    for code, values in (counts.get("byCode") or {}).items():
        summary = ", ".join(f"{key}={value}" for key, value in sorted(values.items()))
        lines.append(f"- `{code}`: {summary}")
    lines.extend(["", "## Option Warning Rows", ""])
    if rows:
        lines.append("| Scene | Code | Group | Classification | Override | Warning reason |")
        lines.append("| --- | --- | ---: | --- | --- | --- |")
        for row in rows:
            override_bits: list[str] = []
            if row.get("overridePre"):
                override_bits.append("pre")
            if row.get("overrideAfter"):
                override_bits.append("after=" + ", ".join(row.get("overrideAfter") or []))
            if row.get("overrideTargets"):
                override_bits.append("responses=" + str(len(row.get("overrideTargets") or {})))
            if row.get("problems"):
                override_bits.append("problems=" + str(len(row.get("problems") or [])))
            lines.append(
                "| "
                + " | ".join([
                    md_escape(row.get("scene")),
                    md_escape(row.get("code")),
                    md_escape(row.get("group")),
                    md_escape(row.get("classification")),
                    md_escape(", ".join(override_bits) or "none"),
                    md_escape(row.get("warningReason")),
                ])
                + " |"
            )
    else:
        lines.append("No option warning rows found.")
    lines.extend(["", "## Invalid Override References", ""])
    if invalid:
        lines.append("| Scene | Kind | Problem | Detail |")
        lines.append("| --- | --- | --- | --- |")
        for row in invalid:
            detail = row.get("anchor") or row.get("optionId") or row.get("group") or row.get("target") or ""
            lines.append(
                "| "
                + " | ".join([
                    md_escape(row.get("scene")),
                    md_escape(row.get("kind")),
                    md_escape(row.get("problem")),
                    md_escape(detail),
                ])
                + " |"
            )
    else:
        lines.append("No invalid override references found.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    language = safe_str(args.language).upper() or "CN"
    conv_root = args.conv_root or (ROOT / "webui" / "data" / "lang" / language / "conv")
    if not conv_root.exists():
        raise SystemExit(f"Conversation root not found: {conv_root}")
    if not args.overrides.exists():
        raise SystemExit(f"Option overrides not found: {args.overrides}")
    output_prefix = args.output_prefix or (STORY_OPTION_REPORTS_DIR / f"option_override_coverage_{language}")
    payload = build_payload(language, conv_root, args.overrides)
    write_report_json(output_prefix.with_suffix(".json"), payload)
    write_markdown(output_prefix.with_suffix(".md"), payload)
    counts = payload["counts"]
    print(
        f"{language}: audited {counts['optionWarningUnits']} option warning unit(s); "
        f"manual-covered={counts['classifications'].get('manual-covered', 0)}, "
        f"invalid={counts['invalidOverrideReferences']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
