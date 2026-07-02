#!/usr/bin/env python3
"""Rank FindTarget selector tag candidates by payload complexity.

This audit combines the tag-only FindTarget replay output with the IL2CPP
MemoryPack metadata catalog. It does not decode selector payload bytes. It
answers: "which nonzero selector tags look simplest to turn into a bounded
payload probe next?"

Output:

    reports/mission_order/findtarget_selector_payload_priority_audit.json
    reports/mission_order/findtarget_selector_payload_priority_audit.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_REPLAY_JSON = REPORT_DIR / "findtarget_selector_replay_audit.json"
DEFAULT_TAG_JSON = REPORT_DIR / "selector_formatter_tag_audit.json"
DEFAULT_METADATA_JSON = REPORT_DIR / "selector_targetsettings_memorypack_metadata.json"
DEFAULT_JSON = REPORT_DIR / "findtarget_selector_payload_priority_audit.json"
DEFAULT_MD = REPORT_DIR / "findtarget_selector_payload_priority_audit.md"


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def wrapper_type_from_formatter(formatter_name: str) -> str:
    if formatter_name.endswith("Formatter"):
        return formatter_name[: -len("Formatter")] + "ForMemoryPack"
    return formatter_name


def load_metadata_types(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    by_name: dict[str, dict[str, Any]] = {}
    for section in ("matchedTypes", "memberOnlyTypes"):
        for row in payload.get(section) or []:
            full_name = str(row.get("fullName") or "")
            if full_name and full_name not in by_name:
                by_name[full_name] = row
    return by_name


def setter_rows(type_row: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for method in type_row.get("methods") or []:
        name = str(method.get("name") or "")
        if not (name.startswith("set___") and name.endswith("__")):
            continue
        field = name[len("set___") : -len("__")]
        if field == "instance":
            continue
        detail = (method.get("parameterDetails") or [{}])[0]
        rows.append(
            {
                "field": field,
                "method": name,
                "token": method.get("token"),
                "typeName": detail.get("typeName") or "",
                "typeIndex": detail.get("typeIndex"),
            }
        )
    return rows


def classify_payload(setters: list[dict[str, Any]]) -> str:
    if not setters:
        return "empty-instance-only"
    type_names = [str(row.get("typeName") or "") for row in setters]
    if any("TargetSettings" in value for value in type_names):
        return "nested-target-settings"
    if any("Blackboard" in value for value in type_names):
        return "blackboard-value"
    if any(value.startswith("<type-index:") for value in type_names):
        return "unresolved-or-collection"
    if any("String" in value for value in type_names):
        return "string-or-primitive"
    primitive_prefixes = ("System.", "Beyond.", "UnityEngine.")
    if all(value.startswith(primitive_prefixes) for value in type_names):
        return "primitive-or-enum"
    return "mixed"


def complexity_rank(classification: str, setter_count: int) -> tuple[int, int, str]:
    order = {
        "empty-instance-only": 0,
        "primitive-or-enum": 1,
        "string-or-primitive": 2,
        "blackboard-value": 3,
        "unresolved-or-collection": 4,
        "nested-target-settings": 5,
        "mixed": 6,
    }
    return (order.get(classification, 9), setter_count, classification)


def tag_map_rows(tag_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for table in tag_payload.get("selectorTables") or []:
        family = str(table.get("id") or "")
        for row in table.get("formatterTags") or []:
            rows.append(
                {
                    "family": family,
                    "tag": str(row.get("tagHex") or ""),
                    "actionName": row.get("actionName") or "",
                    "formatterName": row.get("formatterName") or "",
                }
            )
    return rows


def replay_candidate_rows(replay_payload: dict[str, Any], tag_payload: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = (replay_payload.get("summary") or {}).get("selectorNonZeroTagCandidates") or []
    if explicit:
        return explicit
    count_map = (replay_payload.get("summary") or {}).get("selectorNonZeroUnionTagFamilyTagCounts") or {}
    tags = {(row["family"], row["tag"]): row for row in tag_map_rows(tag_payload)}
    rows = []
    for key, count in count_map.items():
        family, tag = key.split(":", 1)
        tag_row = tags.get((family, tag), {})
        rows.append(
            {
                "family": family,
                "tag": tag,
                "count": count,
                "actionName": tag_row.get("actionName") or "",
                "formatterName": tag_row.get("formatterName") or "",
            }
        )
    return rows


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    replay = read_json(args.replay_json)
    tag_payload = read_json(args.tag_json)
    metadata_types = load_metadata_types(args.metadata_json)
    rows = []
    for candidate in replay_candidate_rows(replay, tag_payload)[: args.limit]:
        formatter_name = str(candidate.get("formatterName") or "")
        wrapper_type = wrapper_type_from_formatter(formatter_name)
        type_row = metadata_types.get(wrapper_type) or {}
        setters = setter_rows(type_row)
        classification = classify_payload(setters)
        rows.append(
            {
                **candidate,
                "wrapperType": wrapper_type,
                "metadataTypeFound": bool(type_row),
                "payloadSetterCount": len(setters),
                "payloadClassification": classification,
                "payloadSetters": setters,
                "complexityRank": list(complexity_rank(classification, len(setters))),
            }
        )

    ranked = sorted(
        rows,
        key=lambda row: (
            complexity_rank(row["payloadClassification"], row["payloadSetterCount"]),
            -int(row.get("count") or 0),
        ),
    )
    simplest = ranked[:8]
    return {
        "metadata": {
            "replayAudit": repo_rel(args.replay_json),
            "selectorTagAudit": repo_rel(args.tag_json),
            "memorypackMetadata": repo_rel(args.metadata_json),
        },
        "summary": {
            "candidateCount": len(rows),
            "emptyPayloadCandidateCount": sum(
                1 for row in rows if row.get("payloadClassification") == "empty-instance-only"
            ),
            "nestedTargetSettingsCandidateCount": sum(
                1 for row in rows if row.get("payloadClassification") == "nested-target-settings"
            ),
            "topRecommendation": (
                "Probe empty-instance-only selector payloads first; they should only need a union tag and no nested payload bytes."
                if any(row.get("payloadClassification") == "empty-instance-only" for row in rows)
                else "No empty payload candidate found; choose the lowest complexity ranked primitive/string candidate."
            ),
        },
        "interpretation": [
            "This audit ranks payload probe targets only; it does not prove byte boundaries.",
            "Tags with no payload setters beyond instance are the safest next bounded-reader experiment.",
            "Nested TargetSettings, Blackboard values, unresolved collections, and shape lists should wait until simpler selector payload boundaries are proven.",
        ],
        "candidates": rows,
        "rankedCandidates": ranked,
        "simplestCandidates": simplest,
    }


def setter_summary(row: dict[str, Any]) -> str:
    setters = row.get("payloadSetters") or []
    if not setters:
        return "none"
    return ", ".join(f"{item.get('field')}:{item.get('typeName')}" for item in setters)


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# FindTarget Selector Payload Priority Audit",
        "",
        f"- replay audit: `{md_escape(payload.get('metadata', {}).get('replayAudit'))}`",
        f"- selector tag audit: `{md_escape(payload.get('metadata', {}).get('selectorTagAudit'))}`",
        f"- MemoryPack metadata: `{md_escape(payload.get('metadata', {}).get('memorypackMetadata'))}`",
        f"- candidates: `{summary.get('candidateCount')}`",
        f"- empty-payload candidates: `{summary.get('emptyPayloadCandidateCount')}`",
        f"- nested TargetSettings candidates: `{summary.get('nestedTargetSettingsCandidateCount')}`",
        f"- recommendation: {md_escape(summary.get('topRecommendation'))}",
        "",
        "## Interpretation",
        "",
    ]
    for item in payload.get("interpretation") or []:
        lines.append(f"- {md_escape(item)}")

    lines.extend(
        [
            "",
            "## Simplest Candidates",
            "",
            "| family | tag | count | selector | class | setters |",
            "| --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in payload.get("simplestCandidates") or []:
        lines.append(
            f"| `{md_escape(row.get('family'))}` | `{md_escape(row.get('tag'))}` | {row.get('count')} | "
            f"`{md_escape(row.get('actionName'))}` | `{md_escape(row.get('payloadClassification'))}` | "
            f"`{md_escape(setter_summary(row))}` |"
        )

    lines.extend(
        [
            "",
            "## All Nonzero Candidates",
            "",
            "| family | tag | count | selector | class | setters |",
            "| --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in payload.get("candidates") or []:
        lines.append(
            f"| `{md_escape(row.get('family'))}` | `{md_escape(row.get('tag'))}` | {row.get('count')} | "
            f"`{md_escape(row.get('actionName'))}` | `{md_escape(row.get('payloadClassification'))}` | "
            f"`{md_escape(setter_summary(row))}` |"
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-json", type=Path, default=DEFAULT_REPLAY_JSON)
    parser.add_argument("--tag-json", type=Path, default=DEFAULT_TAG_JSON)
    parser.add_argument("--metadata-json", type=Path, default=DEFAULT_METADATA_JSON)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--limit", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(f"FindTarget selector payload priority audit: {args.json}")
    print(f"FindTarget selector payload priority report: {args.markdown}")
    print(
        "candidates="
        f"{summary['candidateCount']} "
        f"emptyPayload={summary['emptyPayloadCandidateCount']} "
        f"nestedTargetSettings={summary['nestedTargetSettingsCandidateCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
