#!/usr/bin/env python3
"""Audit manual option overrides against inferred option branch edges."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", Path(__file__).resolve().parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import EXPORT_ROOT, REPORTS_DIR, ROOT, md_escape, safe_key, write_report_json
from build_runtime_jump_option_route_audit import collect_audit_rows


DEFAULT_DB = REPORTS_DIR / "source_graph" / "endfield_source_graph.sqlite"
DEFAULT_OUTPUT_PREFIX = REPORTS_DIR / "source_graph" / "option_override_branch_conflicts"
DEFAULT_TIMELINE_ORDERS = EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit manual WebUI option overrides against inferred source-graph branch edges.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Source graph SQLite path.")
    parser.add_argument("--language", default="CN", help="Language code for runtime-jump joins.")
    parser.add_argument(
        "--conv-dir",
        type=Path,
        default=None,
        help="Conversation JSON directory. Defaults to webui/data/lang/<language>/conv.",
    )
    parser.add_argument("--timeline-orders", type=Path, default=DEFAULT_TIMELINE_ORDERS)
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_OUTPUT_PREFIX,
        help="Output prefix without extension.",
    )
    parser.add_argument(
        "--skip-runtime-jump",
        action="store_true",
        help="Only compare graph manual/inferred branch edges; skip runtime-jump audit join.",
    )
    return parser.parse_args(argv)


def parse_json_text(value: Any) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}


def node_key(node_id: str) -> str:
    return node_id.split(":", 1)[1] if ":" in node_id else node_id


def story_group_from_option(option_id: str) -> tuple[str, str]:
    if option_id.startswith("option_"):
        parts = option_id[len("option_") :].rsplit("_", 2)
        if len(parts) == 3:
            return parts[0], parts[1]
    return "", ""


def compact_line(conn: sqlite3.Connection, node_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT id, name, data FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if not row:
        return {"id": node_key(node_id)}
    data = parse_json_text(row["data"])
    out = {"id": node_key(row["id"])}
    for key in ("actor", "actorId", "audio", "text", "timestamp"):
        value = data.get(key) if isinstance(data, dict) else None
        if value not in (None, "", [], {}):
            out[key] = value
    return out


def compact_option(conn: sqlite3.Connection, node_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT id, name, data FROM nodes WHERE id = ?", (node_id,)).fetchone()
    out = {"id": node_key(node_id)}
    if not row:
        return out
    data = parse_json_text(row["data"])
    text = data.get("text") if isinstance(data, dict) else ""
    if text:
        out["text"] = text
    return out


def edge_ref(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    return {
        "line": compact_line(conn, row["dst"]),
        "source": row["source"],
        "evidence": row["evidence"],
        "data": parse_json_text(row["data"]),
    }


def load_first_line_edges(conn: sqlite3.Connection) -> tuple[dict[str, sqlite3.Row], dict[str, list[sqlite3.Row]]]:
    manual_rows = conn.execute(
        """
        SELECT src, dst, source, evidence, data
        FROM edges
        WHERE kind = 'option_first_line'
          AND source = 'webui/option_override'
        ORDER BY src, dst
        """
    ).fetchall()
    inferred_rows = conn.execute(
        """
        SELECT src, dst, source, evidence, data
        FROM edges
        WHERE kind = 'option_first_line'
          AND source <> 'webui/option_override'
        ORDER BY src, source, dst
        """
    ).fetchall()
    manual_by_option = {row["src"]: row for row in manual_rows}
    inferred_by_option: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in inferred_rows:
        inferred_by_option[row["src"]].append(row)
    return manual_by_option, inferred_by_option


def load_manual_paths(conn: sqlite3.Connection) -> dict[str, list[str]]:
    rows = conn.execute(
        """
        SELECT src, dst
        FROM edges
        WHERE kind = 'option_path_line'
          AND source = 'webui/option_override'
        ORDER BY src, id
        """
    ).fetchall()
    paths: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        line_id = node_key(row["dst"])
        if line_id not in paths[row["src"]]:
            paths[row["src"]].append(line_id)
    return paths


def classify_first_line(manual_first: str, inferred_rows: list[sqlite3.Row]) -> str:
    if not inferred_rows:
        return "manual_only"
    inferred_firsts = {node_key(row["dst"]) for row in inferred_rows}
    if inferred_firsts == {manual_first}:
        return "manual_matches_inference"
    if manual_first in inferred_firsts:
        return "manual_partially_matches_inference"
    return "manual_conflicts_inference"


def runtime_rows_by_group(
    language: str,
    conv_dir: Path,
    timeline_orders: Path,
    stories: list[str],
    *,
    skip: bool,
) -> dict[tuple[str, str], dict[str, Any]]:
    if skip or not stories:
        return {}
    rows = collect_audit_rows(
        language,
        conv_dir,
        timeline_orders,
        story_filters=stories,
        only_nearby_jumps=True,
    )
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        out[(safe_key(row.get("sceneKey")), safe_key(row.get("group")))] = row
    return out


def classify_runtime_support(
    option_id: str,
    manual_first: str,
    inferred_firsts: set[str],
    runtime_row: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    if not runtime_row:
        return "runtime_jump_incomplete", {}
    checks = runtime_row.get("checks") if isinstance(runtime_row.get("checks"), dict) else {}
    runtime_first = safe_key((checks.get("runtimeFirstLineByOption") or {}).get(option_id))
    if not runtime_first:
        return "runtime_jump_incomplete", {"recommendation": runtime_row.get("recommendation")}
    evidence = {
        "runtimeFirstLine": runtime_first,
        "recommendation": runtime_row.get("recommendation"),
        "nearbyRuntimeJumpCount": len(runtime_row.get("nearbyRuntimeJumps") or []),
        "runtimePathConflicts": checks.get("runtimePathConflicts") or [],
    }
    if runtime_first == manual_first:
        return "runtime_jump_supports_manual", evidence
    if runtime_first in inferred_firsts:
        return "runtime_jump_supports_inference", evidence
    return "runtime_jump_other", evidence


def build_rows(
    conn: sqlite3.Connection,
    *,
    language: str,
    conv_dir: Path,
    timeline_orders: Path,
    skip_runtime_jump: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manual_by_option, inferred_by_option = load_first_line_edges(conn)
    manual_paths = load_manual_paths(conn)
    stories = sorted(
        {
            story
            for option_node in manual_by_option
            for story, _group in [story_group_from_option(node_key(option_node))]
            if story
        }
    )
    runtime_by_group = runtime_rows_by_group(
        language,
        conv_dir,
        timeline_orders,
        stories,
        skip=skip_runtime_jump,
    )

    rows: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    runtime_counts: Counter[str] = Counter()
    for option_node, manual_edge in sorted(manual_by_option.items(), key=lambda item: node_key(item[0])):
        option_id = node_key(option_node)
        story, group = story_group_from_option(option_id)
        manual_first = node_key(manual_edge["dst"])
        inferred_rows = inferred_by_option.get(option_node, [])
        inferred_firsts = {node_key(row["dst"]) for row in inferred_rows}
        classification = classify_first_line(manual_first, inferred_rows)
        runtime_row = runtime_by_group.get((story, group))
        runtime_class, runtime_evidence = classify_runtime_support(
            option_id,
            manual_first,
            inferred_firsts,
            runtime_row,
        )
        class_counts[classification] += 1
        runtime_counts[runtime_class] += 1
        row = {
            "story": story,
            "group": group,
            "option": compact_option(conn, option_node),
            "classification": classification,
            "manual": {
                "firstLine": compact_line(conn, manual_edge["dst"]),
                "pathLineIds": manual_paths.get(option_node, []),
                "source": manual_edge["source"],
                "evidence": manual_edge["evidence"],
                "data": parse_json_text(manual_edge["data"]),
            },
            "inferred": [edge_ref(conn, row) for row in inferred_rows],
            "runtimeJump": {
                "classification": runtime_class,
                **runtime_evidence,
            },
        }
        rows.append(row)

    summary = {
        "generated": int(time.time()),
        "language": language,
        "manualResponseOptions": len(rows),
        "classificationCounts": dict(sorted(class_counts.items())),
        "runtimeJumpCounts": dict(sorted(runtime_counts.items())),
        "runtimeJumpGroupsJoined": len(runtime_by_group),
        "conflictingStories": sorted({row["story"] for row in rows if row["classification"] == "manual_conflicts_inference"}),
        "highSignalRuntimeManualSupport": [
            {
                "story": row["story"],
                "group": row["group"],
                "option": row["option"]["id"],
                "manualFirstLine": row["manual"]["firstLine"]["id"],
                "inferredFirstLines": [item["line"]["id"] for item in row["inferred"]],
                "runtimeFirstLine": row["runtimeJump"].get("runtimeFirstLine"),
            }
            for row in rows
            if row["classification"] == "manual_conflicts_inference"
            and row["runtimeJump"]["classification"] == "runtime_jump_supports_manual"
        ],
    }
    return summary, rows


def write_markdown(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conflicts = [row for row in rows if row["classification"] == "manual_conflicts_inference"]
    high_signal = summary.get("highSignalRuntimeManualSupport") or []
    lines = [
        "# Option Override Branch Conflict Audit",
        "",
        "Manual WebUI option overrides are authoritative for display. Inferred branch edges remain diagnostic evidence.",
        "",
        "## Summary",
        "",
        f"- Manual response options: {summary['manualResponseOptions']}",
        f"- Manual matches inference: {summary['classificationCounts'].get('manual_matches_inference', 0)}",
        f"- Manual conflicts inference: {summary['classificationCounts'].get('manual_conflicts_inference', 0)}",
        f"- Manual only: {summary['classificationCounts'].get('manual_only', 0)}",
        f"- Runtime jump supports manual: {summary['runtimeJumpCounts'].get('runtime_jump_supports_manual', 0)}",
        f"- Runtime jump supports inference: {summary['runtimeJumpCounts'].get('runtime_jump_supports_inference', 0)}",
        f"- Runtime jump incomplete: {summary['runtimeJumpCounts'].get('runtime_jump_incomplete', 0)}",
        "",
        "## High-Signal Runtime Support",
        "",
    ]
    if high_signal:
        lines.extend([
            "| Story | Group | Option | Manual first | Inferred first | Runtime first |",
            "| --- | ---: | --- | --- | --- | --- |",
        ])
        for row in high_signal:
            lines.append(
                "| "
                + " | ".join(
                    md_escape(value)
                    for value in (
                        row["story"],
                        row["group"],
                        row["option"],
                        row["manualFirstLine"],
                        ", ".join(row["inferredFirstLines"]),
                        row.get("runtimeFirstLine") or "",
                    )
                )
                + " |"
            )
    else:
        lines.append("No conflict rows had nearby runtime-jump support for the manual first line.")
    lines.extend([
        "",
        "## Manual Conflicts",
        "",
        "| Story | Group | Option | Manual first | Inferred first | Runtime support |",
        "| --- | ---: | --- | --- | --- | --- |",
    ])
    for row in conflicts:
        lines.append(
            "| "
            + " | ".join(
                md_escape(value)
                for value in (
                    row["story"],
                    row["group"],
                    row["option"]["id"],
                    row["manual"]["firstLine"]["id"],
                    ", ".join(item["line"]["id"] for item in row["inferred"]),
                    row["runtimeJump"]["classification"],
                )
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(args: argparse.Namespace) -> dict[str, Path]:
    conv_dir = args.conv_dir or ROOT / "webui" / "data" / "lang" / args.language / "conv"
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        summary, rows = build_rows(
            conn,
            language=args.language,
            conv_dir=conv_dir,
            timeline_orders=args.timeline_orders,
            skip_runtime_jump=args.skip_runtime_jump,
        )
    payload = {"summary": summary, "rows": rows}
    json_path = args.output_prefix.with_suffix(".json")
    md_path = args.output_prefix.with_suffix(".md")
    write_report_json(json_path, payload)
    write_markdown(md_path, summary, rows)
    return {"json": json_path, "markdown": md_path}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_report(args)
    print(f"Option override branch conflict audit: {result['markdown']}")
    print(f"Option override branch conflict data:  {result['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
