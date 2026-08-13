#!/usr/bin/env python3
"""Compare OCR-observed Story order directly with the manual order override.

The active override remains the only editable Story-order source. This report
is a read-only review of coverage and ordering differences between
``webui/data/story_order_ocr.json`` and ``webui/overrides/story_order.json``.
It does not promote OCR keys or modify either input.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if __package__ == "scripts.story_recovery.ocr":
    from ...common import (
        REPORTS_DIR,
        md_escape,
        read_json,
        rel_path,
        safe_key,
        write_report_json,
        write_text_if_changed,
    )
    from ...story_builder.mission_recovery import natural_key
elif __package__ == "story_recovery.ocr":
    from common import (
        REPORTS_DIR,
        md_escape,
        read_json,
        rel_path,
        safe_key,
        write_report_json,
        write_text_if_changed,
    )
    from story_builder.mission_recovery import natural_key
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")


DEFAULT_OVERRIDE = ROOT / "webui" / "overrides" / "story_order.json"
DEFAULT_OCR = ROOT / "webui" / "data" / "story_order_ocr.json"
DEFAULT_OUTPUT_DIR = REPORTS_DIR / "gameplay_video_ocr"
SCHEMA = "gameplayVideoOcrOverrideDisagreement.v1"
EXAMPLE_LIMIT = 24


def _mission_rows(payload: Any) -> dict[str, dict[str, Any]]:
    missions = payload.get("missions") if isinstance(payload, dict) else {}
    if not isinstance(missions, dict):
        return {}
    return {
        safe_key(mission): row
        for mission, row in missions.items()
        if safe_key(mission) and isinstance(row, dict)
    }


def _orders(payload: Any) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for mission, row in _mission_rows(payload).items():
        values = row.get("order")
        if not isinstance(values, list):
            continue
        order: list[str] = []
        for value in values:
            key = safe_key(value)
            if key and key not in order:
                order.append(key)
        if order:
            out[mission] = order
    return out


def _inversion_count_and_examples(
    override_common: list[str],
    ocr_common: list[str],
) -> tuple[int, list[dict[str, Any]]]:
    ocr_positions = {key: index for index, key in enumerate(ocr_common)}
    sequence = [ocr_positions[key] for key in override_common]
    bit = [0] * (len(sequence) + 1)

    def add(index: int) -> None:
        while index < len(bit):
            bit[index] += 1
            index += index & -index

    def prefix(index: int) -> int:
        total = 0
        while index:
            total += bit[index]
            index -= index & -index
        return total

    inversions = 0
    for index, value in enumerate(sequence):
        fenwick_index = value + 1
        inversions += index - prefix(fenwick_index)
        add(fenwick_index)

    examples: list[dict[str, Any]] = []
    for index in range(1, len(override_common)):
        first = override_common[index - 1]
        second = override_common[index]
        first_ocr = ocr_positions[first]
        second_ocr = ocr_positions[second]
        if first_ocr <= second_ocr:
            continue
        examples.append({
            "overrideFrom": first,
            "overrideTo": second,
            "overrideFromIndex": index - 1,
            "overrideToIndex": index,
            "ocrFromIndex": first_ocr,
            "ocrToIndex": second_ocr,
        })
        if len(examples) >= EXAMPLE_LIMIT:
            break
    return inversions, examples


def _compare_mission(
    mission: str,
    override_order: list[str],
    ocr_order: list[str],
    *,
    locked: bool,
) -> dict[str, Any]:
    override_set = set(override_order)
    ocr_set = set(ocr_order)
    common = override_set & ocr_set
    override_common = [key for key in override_order if key in common]
    ocr_common = [key for key in ocr_order if key in common]
    key_set_same = override_set == ocr_set
    order_same = override_common == ocr_common

    if not override_order:
        status = "ocr-only"
    elif not ocr_order:
        status = "override-only"
    elif key_set_same and order_same:
        status = "agree"
    elif key_set_same:
        status = "order-disagrees"
    elif order_same:
        status = "keys-disagree"
    else:
        status = "keys-and-order-disagree"

    inversions, examples = _inversion_count_and_examples(override_common, ocr_common)
    return {
        "mission": mission,
        "status": status,
        "disagrees": status != "agree",
        "locked": bool(locked),
        "overrideCount": len(override_order),
        "ocrCount": len(ocr_order),
        "commonKeyCount": len(common),
        "overrideOnlyKeys": [key for key in override_order if key not in ocr_set],
        "ocrOnlyKeys": [key for key in ocr_order if key not in override_set],
        "overrideCommonOrder": override_common,
        "ocrCommonOrder": ocr_common,
        "commonSamePositionCount": sum(
            left == right for left, right in zip(override_common, ocr_common)
        ),
        "inversionCount": inversions,
        "inversionExamples": examples,
        "overrideOrder": override_order,
        "ocrOrder": ocr_order,
    }


def build_report(
    override_payload: dict[str, Any],
    ocr_payload: dict[str, Any],
    *,
    override_path: Path,
    ocr_path: Path,
) -> dict[str, Any]:
    override_orders = _orders(override_payload)
    ocr_orders = _orders(ocr_payload)
    override_rows = _mission_rows(override_payload)
    rows = [
        _compare_mission(
            mission,
            override_orders.get(mission, []),
            ocr_orders.get(mission, []),
            locked=bool((override_rows.get(mission) or {}).get("locked")),
        )
        for mission in sorted(set(override_orders) | set(ocr_orders), key=natural_key)
    ]

    status_counts = Counter(row["status"] for row in rows)
    summary = {
        "unionMissions": len(rows),
        "overrideMissions": len(override_orders),
        "ocrMissions": len(ocr_orders),
        "bothMissions": len(set(override_orders) & set(ocr_orders)),
        "overrideOnlyMissions": status_counts.get("override-only", 0),
        "ocrOnlyMissions": status_counts.get("ocr-only", 0),
        "agreeMissions": status_counts.get("agree", 0),
        "disagreeMissions": len(rows) - status_counts.get("agree", 0),
        "keySetDisagreementMissions": sum(
            row["status"] in {
                "override-only",
                "ocr-only",
                "keys-disagree",
                "keys-and-order-disagree",
            }
            for row in rows
        ),
        "orderDisagreementMissions": sum(
            row["status"] in {"order-disagrees", "keys-and-order-disagree"}
            for row in rows
        ),
        "lockedDisagreementMissions": sum(
            row["disagrees"] and row["locked"] for row in rows
        ),
        "overrideKeys": sum(len(order) for order in override_orders.values()),
        "ocrKeys": sum(len(order) for order in ocr_orders.values()),
        "overrideOnlyKeys": sum(len(row["overrideOnlyKeys"]) for row in rows),
        "ocrOnlyKeys": sum(len(row["ocrOnlyKeys"]) for row in rows),
        "commonKeys": sum(row["commonKeyCount"] for row in rows),
        "inversions": sum(row["inversionCount"] for row in rows),
        "statusCounts": dict(sorted(status_counts.items())),
    }
    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "_note": (
            "Read-only comparison of the WebUI OCR candidate order and the "
            "manual Story-order override. No OCR key is promoted and no "
            "override row is changed by this report."
        ),
        "inputs": {
            "override": rel_path(override_path),
            "ocr": rel_path(ocr_path),
            "overrideSchema": safe_key(override_payload.get("_schema")),
            "ocrSchema": safe_key(ocr_payload.get("_schema")),
            "ocrGeneratedAt": safe_key(
                ocr_payload.get("_generatedAt") or ocr_payload.get("generatedAt")
            ),
        },
        "summary": summary,
        "missions": rows,
    }


def _compact_keys(values: list[str], limit: int = 12) -> str:
    if not values:
        return "-"
    shown = ", ".join(f"`{md_escape(value)}`" for value in values[:limit])
    if len(values) > limit:
        shown += f", … (+{len(values) - limit})"
    return shown


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Gameplay Video OCR vs Story-Order Override",
        "",
        f"Generated: `{report['_generatedAt']}`",
        "",
        "This is a read-only disagreement report. The OCR order is a candidate",
        "source for WebUI review; it does not modify the manual override.",
        "",
        "## Summary",
        "",
        f"- missions in override: `{summary['overrideMissions']}`",
        f"- missions in OCR candidates: `{summary['ocrMissions']}`",
        f"- missions compared: `{summary['unionMissions']}`",
        f"- exact agreements: `{summary['agreeMissions']}`",
        f"- disagreements: `{summary['disagreeMissions']}`",
        f"- override-only missions: `{summary['overrideOnlyMissions']}`",
        f"- OCR-only missions: `{summary['ocrOnlyMissions']}`",
        f"- missions with order disagreement: `{summary['orderDisagreementMissions']}`",
        f"- locked missions with disagreement: `{summary['lockedDisagreementMissions']}`",
        f"- override-only keys: `{summary['overrideOnlyKeys']}`",
        f"- OCR-only keys: `{summary['ocrOnlyKeys']}`",
        f"- shared-key inversions: `{summary['inversions']}`",
        "",
        "## Disagreement Missions",
        "",
        "| mission | status | locked | override | OCR | shared | override-only | OCR-only | inversions |",
        "| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    disagreements = [row for row in report["missions"] if row["disagrees"]]
    disagreements.sort(
        key=lambda row: (
            {"keys-and-order-disagree": 0, "order-disagrees": 1, "keys-disagree": 2,
             "override-only": 3, "ocr-only": 4}.get(row["status"], 5),
            -int(row["inversionCount"]),
            natural_key(row["mission"]),
        )
    )
    if not disagreements:
        lines.append("| _(none)_ | agree | no | 0 | 0 | 0 | 0 | 0 | 0 |")
    else:
        for row in disagreements:
            lines.append(
                f"| `{md_escape(row['mission'])}` | `{row['status']}` | "
                f"{'yes' if row['locked'] else 'no'} | {row['overrideCount']} | "
                f"{row['ocrCount']} | {row['commonKeyCount']} | "
                f"{len(row['overrideOnlyKeys'])} | {len(row['ocrOnlyKeys'])} | "
                f"{row['inversionCount']} |"
            )

    lines.extend(["", "## Key-Level Details", ""])
    for row in disagreements:
        lines.extend([
            f"### `{md_escape(row['mission'])}` — `{row['status']}`",
            "",
            f"- locked: `{str(row['locked']).lower()}`",
            f"- shared keys: `{row['commonKeyCount']}`; shared-key inversions: `{row['inversionCount']}`",
            f"- override-only keys: {_compact_keys(row['overrideOnlyKeys'])}",
            f"- OCR-only keys: {_compact_keys(row['ocrOnlyKeys'])}",
        ])
        if row["inversionExamples"]:
            examples = "; ".join(
                f"`{md_escape(example['overrideFrom'])}` → `{md_escape(example['overrideTo'])}` "
                f"(OCR positions {example['ocrFromIndex']} → {example['ocrToIndex']})"
                for example in row["inversionExamples"]
            )
            lines.append(f"- adjacent inversion examples: {examples}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--override", type=Path, default=DEFAULT_OVERRIDE)
    parser.add_argument("--ocr", type=Path, default=DEFAULT_OCR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        read_json(args.override, {}),
        read_json(args.ocr, {}),
        override_path=args.override,
        ocr_path=args.ocr,
    )
    output_dir = args.output_dir
    output_json = output_dir / "story_order_ocr_override_disagreement.json"
    output_md = output_dir / "story_order_ocr_override_disagreement.md"
    write_report_json(output_json, report)
    write_text_if_changed(output_md, render_markdown(report))
    summary = report["summary"]
    print(
        "OCR/override disagreement: "
        f"missions={summary['unionMissions']} "
        f"disagreements={summary['disagreeMissions']} "
        f"order_disagreements={summary['orderDisagreementMissions']} "
        f"inversions={summary['inversions']}"
    )
    print(f"Wrote {rel_path(output_json)}")
    print(f"Review disagreement summary at {rel_path(output_md)}")
    return 0
