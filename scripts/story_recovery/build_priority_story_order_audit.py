#!/usr/bin/env python3
"""Summarize story-order recovery for the priority mission buckets.

Priority scope mirrors the WebUI labels the recovery work is currently focused
on: main story (e), event (a), major mission (gm), and character story (c).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, safe_key, write_report_json, write_text_if_changed  # noqa: E402


PRIORITY_MISSION_TYPES = {
    "e": "main",
    "a": "event",
    "gm": "major",
    "c": "character",
}
PRIORITY_BUCKET_ORDER = ["main", "event", "major", "character"]
MISSION_TYPE_RE = re.compile(r"^([a-z]+)")


def mission_type(mission: str) -> str:
    match = MISSION_TYPE_RE.match(safe_key(mission).lower())
    return match.group(1) if match else ""


def priority_bucket(mission: str) -> str:
    return PRIORITY_MISSION_TYPES.get(mission_type(mission), "")


def order_status(entry: dict[str, Any]) -> str:
    if entry.get("goStrong"):
        return "strong"
    if entry.get("goWeak"):
        return "weak"
    return "unknown"


def summarize_index(index_path: Path) -> dict[str, Any]:
    payload = read_json(index_path, {})
    entries = payload.get("entries") or []
    bucket_counts: Counter[tuple[str, str]] = Counter()
    bucket_totals: Counter[str] = Counter()
    kind_counts: Counter[tuple[str, str]] = Counter()
    mission_counts: dict[str, Counter[str]] = defaultdict(Counter)
    mission_kinds: dict[str, Counter[str]] = defaultdict(Counter)

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        mission = safe_key(entry.get("m")).lower()
        bucket = priority_bucket(mission)
        if not bucket:
            continue
        status = order_status(entry)
        kind = safe_key(entry.get("d")) or "?"
        bucket_counts[(bucket, status)] += 1
        bucket_totals[bucket] += 1
        kind_counts[(bucket, kind)] += 1
        mission_counts[mission][status] += 1
        mission_kinds[mission][kind] += 1

    bucket_rows = []
    for bucket in PRIORITY_BUCKET_ORDER:
        total = bucket_totals[bucket]
        strong = bucket_counts[(bucket, "strong")]
        weak = bucket_counts[(bucket, "weak")]
        unknown = bucket_counts[(bucket, "unknown")]
        bucket_rows.append({
            "bucket": bucket,
            "total": total,
            "strong": strong,
            "weak": weak,
            "unknown": unknown,
            "ordered": strong + weak,
            "strongPct": round((strong / total) * 100, 2) if total else 0.0,
            "orderedPct": round(((strong + weak) / total) * 100, 2) if total else 0.0,
        })

    top_unknown = []
    for mission, counts in sorted(
        mission_counts.items(),
        key=lambda item: (-item[1]["unknown"], priority_bucket(item[0]), item[0]),
    ):
        if not counts["unknown"]:
            continue
        top_unknown.append({
            "mission": mission,
            "bucket": priority_bucket(mission),
            "strong": counts["strong"],
            "weak": counts["weak"],
            "unknown": counts["unknown"],
            "total": sum(counts.values()),
            "kinds": dict(sorted(mission_kinds[mission].items())),
        })

    return {
        "buckets": bucket_rows,
        "grandTotals": {
            "total": sum(bucket_totals.values()),
            "strong": sum(bucket_counts[(bucket, "strong")] for bucket in PRIORITY_BUCKET_ORDER),
            "weak": sum(bucket_counts[(bucket, "weak")] for bucket in PRIORITY_BUCKET_ORDER),
            "unknown": sum(bucket_counts[(bucket, "unknown")] for bucket in PRIORITY_BUCKET_ORDER),
        },
        "kindCounts": [
            {"bucket": bucket, "kind": kind, "count": count}
            for (bucket, kind), count in sorted(
                kind_counts.items(),
                key=lambda item: (PRIORITY_BUCKET_ORDER.index(item[0][0]), -item[1], item[0][1]),
            )
        ],
        "topUnknownMissions": top_unknown[:40],
    }


def summarize_conversations(conv_dir: Path) -> dict[str, Any]:
    warning_counts: Counter[tuple[str, str]] = Counter()
    response_group_counts: Counter[str] = Counter()
    layout_rows: list[dict[str, Any]] = []
    non_runtime_layout_rows: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    uncovered_rows: list[dict[str, Any]] = []

    for path in sorted(conv_dir.glob("*.json")):
        conv = read_json(path, {})
        if not isinstance(conv, dict):
            continue
        mission = safe_key(conv.get("mission")).lower()
        bucket = priority_bucket(mission)
        if not bucket:
            continue
        key = safe_key(conv.get("key"))
        runtime_registry = ((conv.get("_debug") or {}).get("runtimeRegistry") or {})
        is_unregistered_scene = (
            isinstance(runtime_registry, dict)
            and runtime_registry.get("registered") is False
        )
        for warning in conv.get("warnings") or []:
            if not isinstance(warning, dict):
                continue
            code = safe_key(warning.get("code"))
            if code == "inferredOptionLayout":
                if is_unregistered_scene:
                    warning_counts[(bucket, "nonRuntimeOptionLayout")] += 1
                    non_runtime_layout_rows.append({
                        "bucket": bucket,
                        "mission": mission,
                        "key": key,
                        "reason": safe_key(warning.get("reason")),
                        "runtimeReason": safe_key(runtime_registry.get("reason")),
                        "groupBreakdown": warning.get("groupBreakdown") or {},
                    })
                    continue
                warning_counts[(bucket, code)] += 1
                group_details = warning.get("groupDetails") or []
                modes = Counter(
                    safe_key(group.get("inferredAnchorMode")) or safe_key(group.get("status")) or "?"
                    for group in group_details
                    if isinstance(group, dict)
                )
                layout_rows.append({
                    "bucket": bucket,
                    "mission": mission,
                    "key": key,
                    "reason": safe_key(warning.get("reason")),
                    "groupBreakdown": warning.get("groupBreakdown") or {},
                    "modes": dict(sorted(modes.items())),
                })
            elif code == "inferredOptionResponse":
                groups = warning.get("groups") or []
                warning_counts[(bucket, code)] += 1
                response_group_counts[bucket] += len(groups)
                response_rows.append({
                    "bucket": bucket,
                    "mission": mission,
                    "key": key,
                    "groupCount": len(groups),
                    "groups": [
                        {
                            "group": group.get("group"),
                            "after": safe_key(group.get("after")),
                            "candidateLineIds": group.get("candidateLineIds") or [],
                            "commonLineId": safe_key(group.get("commonLineId")),
                        }
                        for group in groups
                        if isinstance(group, dict)
                    ],
                })
            elif code == "sceneOrderDisorder":
                line_order = warning.get("lineOrder") if isinstance(warning.get("lineOrder"), dict) else {}
                uncovered = line_order.get("uncoveredLineIds") or []
                if uncovered:
                    warning_counts[(bucket, "uncoveredLines")] += 1
                    uncovered_rows.append({
                        "bucket": bucket,
                        "mission": mission,
                        "key": key,
                        "uncoveredLineIds": uncovered,
                        "mode": safe_key(line_order.get("reasonCode") or line_order.get("mode")),
                    })

    return {
        "warningCounts": [
            {"bucket": bucket, "code": code, "count": count}
            for (bucket, code), count in sorted(
                warning_counts.items(),
                key=lambda item: (PRIORITY_BUCKET_ORDER.index(item[0][0]), item[0][1]),
            )
        ],
        "inferredResponseGroupCounts": dict(sorted(response_group_counts.items())),
        "remainingOptionLayout": layout_rows,
        "nonRuntimeOptionLayout": non_runtime_layout_rows,
        "remainingInferredResponses": response_rows,
        "remainingUncoveredLines": uncovered_rows,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Priority Story Order Audit",
        "",
        f"Generated: {payload['generated']}",
        "",
        "Scope: `e` main story, `a` event, `gm` major mission, `c` character story.",
        "",
        "## Order Status",
        "",
        "| bucket | total | strong | weak | unknown | ordered | strong % | ordered % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["order"]["buckets"]:
        lines.append(
            f"| `{row['bucket']}` | {row['total']} | {row['strong']} | {row['weak']} | "
            f"{row['unknown']} | {row['ordered']} | {row['strongPct']:.2f} | {row['orderedPct']:.2f} |"
        )
    totals = payload["order"]["grandTotals"]
    lines.extend([
        "",
        f"Grand total: `{totals['total']}` entries; "
        f"`{totals['strong']}` strong, `{totals['weak']}` weak, `{totals['unknown']}` unknown.",
        "",
        "## Remaining Recovery Warnings",
        "",
        "| bucket | warning | count |",
        "| --- | --- | ---: |",
    ])
    for row in payload["conversations"]["warningCounts"]:
        lines.append(f"| `{row['bucket']}` | `{row['code']}` | {row['count']} |")

    lines.extend([
        "",
        "## Remaining Option Layout",
        "",
        "| scene | bucket | reason | groups | modes |",
        "| --- | --- | --- | --- | --- |",
    ])
    layout_rows = payload["conversations"]["remainingOptionLayout"]
    if layout_rows:
        for row in layout_rows:
            breakdown = row.get("groupBreakdown") or {}
            modes = ", ".join(f"{key}={value}" for key, value in (row.get("modes") or {}).items())
            lines.append(
                f"| `{md_escape(row['key'])}` | `{row['bucket']}` | `{md_escape(row.get('reason'))}` | "
                f"{md_escape(str(breakdown))} | {md_escape(modes)} |"
            )
    else:
        lines.append("| _(none)_ |  |  |  |  |")

    lines.extend([
        "",
        "## Non-Runtime Option Layout",
        "",
        "| scene | bucket | reason | runtime evidence |",
        "| --- | --- | --- | --- |",
    ])
    non_runtime_layout_rows = payload["conversations"].get("nonRuntimeOptionLayout") or []
    if non_runtime_layout_rows:
        for row in non_runtime_layout_rows:
            lines.append(
                f"| `{md_escape(row['key'])}` | `{row['bucket']}` | "
                f"`{md_escape(row.get('reason'))}` | {md_escape(row.get('runtimeReason'))} |"
            )
    else:
        lines.append("| _(none)_ |  |  |  |")

    lines.extend([
        "",
        "## Remaining Inferred Responses",
        "",
        "| scene | bucket | groups |",
        "| --- | --- | ---: |",
    ])
    response_rows = payload["conversations"]["remainingInferredResponses"]
    if response_rows:
        for row in response_rows:
            lines.append(f"| `{md_escape(row['key'])}` | `{row['bucket']}` | {row['groupCount']} |")
    else:
        lines.append("| _(none)_ |  |  |")

    lines.extend([
        "",
        "## Remaining Uncovered Lines",
        "",
        "| scene | bucket | mode | uncovered lines |",
        "| --- | --- | --- | --- |",
    ])
    uncovered_rows = payload["conversations"]["remainingUncoveredLines"]
    if uncovered_rows:
        for row in uncovered_rows:
            uncovered = ", ".join(f"`{md_escape(line_id)}`" for line_id in row.get("uncoveredLineIds") or [])
            lines.append(
                f"| `{md_escape(row['key'])}` | `{row['bucket']}` | "
                f"`{md_escape(row.get('mode'))}` | {uncovered} |"
            )
    else:
        lines.append("| _(none)_ |  |  |  |")

    lines.extend([
        "",
        "## Top Unknown Missions",
        "",
        "| mission | bucket | strong | weak | unknown | total |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ])
    for row in payload["order"]["topUnknownMissions"][:25]:
        lines.append(
            f"| `{md_escape(row['mission'])}` | `{row['bucket']}` | "
            f"{row['strong']} | {row['weak']} | {row['unknown']} | {row['total']} |"
        )

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "story" / "recovery" / "order")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    language = args.language
    lang_root = ROOT / "webui" / "data" / "lang" / language
    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "priorityMissionTypes": PRIORITY_MISSION_TYPES,
        "order": summarize_index(lang_root / "index.json"),
        "conversations": summarize_conversations(lang_root / "conv"),
    }
    out_json = args.reports_dir / f"priority_story_order_{language}.json"
    out_md = args.reports_dir / f"priority_story_order_{language}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
