#!/usr/bin/env python3
"""Recover story option branch structure from the Endfield source graph."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "reports" / "source_graph"
DEFAULT_DB = GRAPH_DIR / "endfield_source_graph.sqlite"
DEFAULT_OUT_DIR = GRAPH_DIR / "story_branches"

GROUP_EDGE_KIND = "has_option_group"
OPTION_EDGE_KIND = "has_option"
BRANCH_EDGE_KINDS = (
    "option_anchor_after",
    "option_first_line",
    "option_path_line",
    "option_path_story",
    "option_merge_line",
    "option_enters_story",
)

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
GROUP_INDEX_RE = re.compile(r"#optionGroup:(\d+)")


def slash(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def parse_json_text(value: Any) -> Any:
    if not value:
        return {}
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def node_key(node_id: str) -> str:
    if ":" not in node_id:
        return node_id
    return node_id.split(":", 1)[1]


def compact_text(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def safe_filename(value: str) -> str:
    name = SAFE_FILENAME_RE.sub("_", value).strip("._")
    return name or "story"


def parse_story_filters(values: list[str] | None) -> list[str]:
    filters: list[str] = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                filters.append(item)
    return filters


def story_matches(story_key: str, filters: list[str]) -> bool:
    if not filters:
        return True
    lowered = story_key.lower()
    for item in filters:
        pattern = item.lower()
        if pattern == lowered:
            return True
        if any(ch in pattern for ch in "*?[]") and fnmatch.fnmatch(lowered, pattern):
            return True
        if pattern in lowered:
            return True
    return False


def group_index(group_name: str, group_data: dict[str, Any]) -> int:
    data_index = group_data.get("index") or group_data.get("g")
    if isinstance(data_index, int):
        return data_index
    match = GROUP_INDEX_RE.search(group_name or "")
    if match:
        return int(match.group(1))
    return 0


def option_sort_key(option: dict[str, Any]) -> tuple[int, str]:
    index = option.get("index")
    if isinstance(index, int):
        return (index, option["optionKey"])
    if isinstance(index, str) and index.isdigit():
        return (int(index), option["optionKey"])
    match = re.search(r"_(\d+)$", option["optionKey"])
    if match:
        return (int(match.group(1)), option["optionKey"])
    return (999999, option["optionKey"])


def target_ref(row: sqlite3.Row) -> dict[str, Any]:
    data = parse_json_text(row["dstData"])
    edge_data = parse_json_text(row["edgeData"])
    ref = {
        "id": row["dstId"],
        "key": node_key(row["dstId"]),
        "kind": row["dstKind"],
        "name": row["dstName"],
    }
    if isinstance(data, dict):
        text = compact_text(data.get("text"), 180)
        if text:
            ref["text"] = text
        actor = data.get("actor") or data.get("actorId")
        if actor:
            ref["actor"] = actor
    if isinstance(edge_data, dict) and edge_data:
        ref["edgeData"] = edge_data
    return ref


def gap(code: str, message: str, severity: str = "warning", **extra: Any) -> dict[str, Any]:
    payload = {"code": code, "severity": severity, "message": message}
    payload.update({key: value for key, value in extra.items() if value not in (None, "", [], {})})
    return payload


def score_option(option: dict[str, Any]) -> float:
    score = 0.15
    if option.get("anchorAfter"):
        score += 0.20
    if option.get("firstLines"):
        score += 0.20
    if option.get("pathLines"):
        score += 0.25
    if option.get("pathStories"):
        score += 0.15
    if option.get("entersStories"):
        score += 0.10
    if option.get("mergeLines"):
        score += 0.05
    severe_gaps = sum(1 for item in option["gaps"] if item["severity"] == "error")
    warning_gaps = len(option["gaps"]) - severe_gaps
    score -= severe_gaps * 0.20
    score -= warning_gaps * 0.05
    return round(max(0.0, min(score, 0.99)), 2)


def set_option_status(option: dict[str, Any]) -> None:
    has_route = bool(option["pathLines"] or option["pathStories"] or option["entersStories"])
    has_entry = bool(option["firstLines"] or option["entersStories"])
    if option["anchorAfter"] and has_entry and has_route and not option["gaps"]:
        option["status"] = "resolved"
    elif has_route or has_entry or option["anchorAfter"]:
        option["status"] = "partial"
    else:
        option["status"] = "unresolved"
    option["confidence"] = score_option(option)


def status_from_children(children: list[dict[str, Any]], own_gaps: list[dict[str, Any]]) -> str:
    if not children:
        return "unresolved"
    statuses = Counter(child["status"] for child in children)
    if statuses.get("unresolved") == len(children):
        return "unresolved"
    if own_gaps or statuses.get("partial") or statuses.get("unresolved"):
        return "partial"
    return "resolved"


def average_confidence(children: list[dict[str, Any]], fallback: float = 0.0) -> float:
    if not children:
        return fallback
    return round(sum(float(child.get("confidence", 0.0)) for child in children) / len(children), 2)


def fetch_groups(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            story.id AS storyId,
            story.name AS storyKey,
            story.data AS storyData,
            group_node.id AS groupId,
            group_node.name AS groupName,
            group_node.data AS groupData
        FROM edges edge
        JOIN nodes story ON story.id = edge.src
        JOIN nodes group_node ON group_node.id = edge.dst
        WHERE edge.kind = ?
          AND story.kind = 'story'
          AND group_node.kind = 'option_group'
        ORDER BY story.name, group_node.name, edge.id
        """,
        (GROUP_EDGE_KIND,),
    ).fetchall()
    groups: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if row["groupId"] in seen:
            continue
        seen.add(row["groupId"])
        story_data = parse_json_text(row["storyData"])
        group_data = parse_json_text(row["groupData"])
        groups.append(
            {
                "storyId": row["storyId"],
                "storyKey": row["storyKey"],
                "storyData": story_data if isinstance(story_data, dict) else {},
                "groupId": row["groupId"],
                "groupKey": node_key(row["groupId"]),
                "groupName": row["groupName"],
                "groupData": group_data if isinstance(group_data, dict) else {},
            }
        )
    return groups


def fetch_options(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        SELECT
            edge.src AS groupId,
            option_node.id AS optionId,
            option_node.name AS optionName,
            option_node.data AS optionData
        FROM edges edge
        JOIN nodes option_node ON option_node.id = edge.dst
        WHERE edge.kind = ?
          AND option_node.kind = 'option'
        ORDER BY edge.id
        """,
        (OPTION_EDGE_KIND,),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["groupId"], row["optionId"])
        if key in seen:
            continue
        seen.add(key)
        option_data = parse_json_text(row["optionData"])
        if not isinstance(option_data, dict):
            option_data = {}
        grouped[row["groupId"]].append(
            {
                "optionId": row["optionId"],
                "optionKey": node_key(row["optionId"]),
                "text": option_data.get("text") or row["optionName"],
                "icon": option_data.get("icon"),
                "index": option_data.get("index"),
                "graphEdges": Counter(),
                "anchorAfter": None,
                "anchorAfterCandidates": [],
                "firstLines": [],
                "pathLines": [],
                "pathStories": [],
                "mergeLines": [],
                "entersStories": [],
                "gaps": [],
                "status": "unresolved",
                "confidence": 0.0,
            }
        )
    for options in grouped.values():
        options.sort(key=option_sort_key)
    return grouped


def fetch_branch_edges(conn: sqlite3.Connection) -> dict[str, dict[str, list[dict[str, Any]]]]:
    placeholders = ",".join("?" for _ in BRANCH_EDGE_KINDS)
    rows = conn.execute(
        f"""
        SELECT
            edge.id AS edgeId,
            edge.src AS optionId,
            edge.kind AS edgeKind,
            edge.source AS edgeSource,
            edge.evidence AS edgeEvidence,
            edge.data AS edgeData,
            target.id AS dstId,
            target.kind AS dstKind,
            target.name AS dstName,
            target.data AS dstData
        FROM edges edge
        JOIN nodes target ON target.id = edge.dst
        WHERE edge.kind IN ({placeholders})
        ORDER BY edge.src, edge.kind, edge.id
        """,
        BRANCH_EDGE_KINDS,
    ).fetchall()
    by_option: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        ref = target_ref(row)
        key = (row["optionId"], row["edgeKind"], ref["id"])
        if key in seen:
            continue
        seen.add(key)
        ref["source"] = row["edgeSource"]
        by_option[row["optionId"]][row["edgeKind"]].append(ref)
    return by_option


def attach_option_edges(option: dict[str, Any], branch_edges: dict[str, list[dict[str, Any]]], group_anchor: str | None) -> None:
    option["graphEdges"] = {kind: len(branch_edges.get(kind, [])) for kind in BRANCH_EDGE_KINDS}
    option["anchorAfterCandidates"] = branch_edges.get("option_anchor_after", [])
    option["firstLines"] = branch_edges.get("option_first_line", [])
    option["pathLines"] = branch_edges.get("option_path_line", [])
    option["pathStories"] = branch_edges.get("option_path_story", [])
    option["mergeLines"] = branch_edges.get("option_merge_line", [])
    option["entersStories"] = branch_edges.get("option_enters_story", [])

    if option["anchorAfterCandidates"]:
        option["anchorAfter"] = option["anchorAfterCandidates"][0]["key"]
    elif group_anchor:
        option["anchorAfter"] = group_anchor

    if not option["anchorAfter"]:
        option["gaps"].append(gap("missing_anchor", "No option_anchor_after edge or group anchor is available.", "warning"))
    if group_anchor and option["anchorAfterCandidates"]:
        anchors = {item["key"] for item in option["anchorAfterCandidates"]}
        if group_anchor not in anchors:
            option["gaps"].append(
                gap(
                    "anchor_mismatch",
                    "The option anchor does not match the WebUI option group anchor.",
                    "warning",
                    groupAnchor=group_anchor,
                    optionAnchors=sorted(anchors),
                )
            )
    if not option["firstLines"] and not option["entersStories"]:
        option["gaps"].append(gap("missing_entry", "No option_first_line or option_enters_story edge was found.", "error"))
    if not option["pathLines"] and not option["pathStories"] and not option["entersStories"]:
        option["gaps"].append(gap("missing_path", "No option_path_line, option_path_story, or option_enters_story edge was found.", "error"))
    set_option_status(option)


def build_reports(conn: sqlite3.Connection, story_filters: list[str], limit: int | None) -> list[dict[str, Any]]:
    groups = fetch_groups(conn)
    options_by_group = fetch_options(conn)
    branch_edges_by_option = fetch_branch_edges(conn)

    stories: dict[str, dict[str, Any]] = {}
    story_order: list[str] = []
    for row in groups:
        story_key = row["storyKey"]
        if not story_matches(story_key, story_filters):
            continue
        if story_key not in stories:
            story_data = row["storyData"]
            stories[story_key] = {
                "storyKey": story_key,
                "storyId": row["storyId"],
                "lineCount": story_data.get("lineCount"),
                "mission": story_data.get("mission"),
                "scene": story_data.get("scene"),
                "preview": story_data.get("preview"),
                "optionGroups": [],
                "gaps": [],
                "status": "unresolved",
                "confidence": 0.0,
            }
            story_order.append(story_key)

        group_data = row["groupData"]
        group_anchor = group_data.get("after")
        group = {
            "groupId": row["groupId"],
            "groupKey": row["groupKey"],
            "index": group_index(row["groupName"], group_data),
            "anchorAfter": group_anchor,
            "risk": group_data.get("risk"),
            "riskReason": group_data.get("reason"),
            "riskDetail": group_data.get("riskDetail"),
            "riskSource": group_data.get("riskSource"),
            "candidateLineIds": group_data.get("candidateLineIds") or [],
            "commonContinuationLineId": group_data.get("commonContinuationLineId"),
            "options": [],
            "gaps": [],
            "status": "unresolved",
            "confidence": 0.0,
        }

        options = options_by_group.get(row["groupId"], [])
        if not options:
            group["gaps"].append(gap("missing_options", "The option group has no has_option edges.", "error"))
        for raw_option in options:
            option = dict(raw_option)
            option["graphEdges"] = dict(option["graphEdges"])
            attach_option_edges(option, branch_edges_by_option.get(option["optionId"], {}), group_anchor)
            group["options"].append(option)

        anchors = {option["anchorAfter"] for option in group["options"] if option.get("anchorAfter")}
        if len(anchors) > 1:
            group["gaps"].append(
                gap(
                    "inconsistent_option_anchors",
                    "Options in the same group resolve to different anchor lines.",
                    "warning",
                    anchors=sorted(anchors),
                )
            )
        if not group_anchor and not anchors:
            group["gaps"].append(gap("missing_group_anchor", "The option group has no resolved anchor line.", "warning"))
        if group["options"] and all(sum(option["graphEdges"].values()) == 0 for option in group["options"]):
            group["gaps"].append(gap("missing_scene_graph_edges", "Options have no branch edges from the scene graph.", "error"))

        group["status"] = status_from_children(group["options"], group["gaps"])
        group["confidence"] = average_confidence(group["options"], 0.0)
        stories[story_key]["optionGroups"].append(group)

        if limit is not None and limit > 0 and len(story_order) >= limit:
            # Keep scanning the already-started story but skip new ones.
            remaining = [item for item in groups if item["storyKey"] == story_key]
            if row is remaining[-1]:
                break

    selected_order = story_order[:limit] if limit is not None and limit > 0 else story_order
    reports = [stories[key] for key in selected_order]
    for story in reports:
        story["optionGroups"].sort(key=lambda item: (item["index"], item["groupKey"]))
        if not story["optionGroups"]:
            story["gaps"].append(gap("missing_groups", "No option groups were recovered for this story.", "error"))
        story["status"] = status_from_children(story["optionGroups"], story["gaps"])
        story["confidence"] = average_confidence(story["optionGroups"], 0.0)
    return reports


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    group_count = 0
    option_count = 0
    unresolved_gap_count = 0

    for story in reports:
        status_counts[story["status"]] += 1
        for item in story["gaps"]:
            gap_counts[item["code"]] += 1
            severity_counts[item["severity"]] += 1
            unresolved_gap_count += 1
        for group in story["optionGroups"]:
            group_count += 1
            for item in group["gaps"]:
                gap_counts[item["code"]] += 1
                severity_counts[item["severity"]] += 1
                unresolved_gap_count += 1
            for option in group["options"]:
                option_count += 1
                for item in option["gaps"]:
                    gap_counts[item["code"]] += 1
                    severity_counts[item["severity"]] += 1
                    unresolved_gap_count += 1

    return {
        "storyCount": len(reports),
        "optionGroupCount": group_count,
        "optionCount": option_count,
        "statusCounts": dict(sorted(status_counts.items())),
        "gapCounts": dict(gap_counts.most_common()),
        "severityCounts": dict(sorted(severity_counts.items())),
        "unresolvedGapCount": unresolved_gap_count,
    }


def branch_index_payload(
    reports: list[dict[str, Any]],
    summary: dict[str, Any],
    db_path: Path,
    out_dir: Path,
    story_filters: list[str],
    limit: int | None,
) -> dict[str, Any]:
    stories = []
    for story in reports:
        gap_count = sum(len(group["gaps"]) + sum(len(option["gaps"]) for option in group["options"]) for group in story["optionGroups"])
        gap_count += len(story["gaps"])
        stories.append(
            {
                "storyKey": story["storyKey"],
                "status": story["status"],
                "confidence": story["confidence"],
                "optionGroupCount": len(story["optionGroups"]),
                "optionCount": sum(len(group["options"]) for group in story["optionGroups"]),
                "unresolvedGapCount": gap_count,
                "report": f"stories/{safe_filename(story['storyKey'])}.json",
            }
        )
    return {
        "generated": int(time.time()),
        "tool": "tools/endfield_story_branch_resolver.py",
        "db": slash(db_path),
        "outDir": slash(out_dir),
        "filters": {"story": story_filters, "limit": limit},
        "edgeKinds": [GROUP_EDGE_KIND, OPTION_EDGE_KIND, *BRANCH_EDGE_KINDS],
        "summary": summary,
        "stories": stories,
    }


def write_summary_md(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Story Branch Recovery",
        "",
        f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(payload['generated']))}",
        f"- Database: `{payload['db']}`",
        f"- Output: `{payload['outDir']}`",
        f"- Stories: {summary['storyCount']}",
        f"- Option groups: {summary['optionGroupCount']}",
        f"- Options: {summary['optionCount']}",
        f"- Unresolved gaps: {summary['unresolvedGapCount']}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in summary["statusCounts"].items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Gap Counts", ""])
    if summary["gapCounts"]:
        for code, count in summary["gapCounts"].items():
            lines.append(f"- {code}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Story Index", "", "| Story | Status | Confidence | Groups | Options | Gaps |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for story in payload["stories"][:100]:
        lines.append(
            f"| `{story['storyKey']}` | {story['status']} | {story['confidence']:.2f} | "
            f"{story['optionGroupCount']} | {story['optionCount']} | {story['unresolvedGapCount']} |"
        )
    if len(payload["stories"]) > 100:
        lines.append(f"| ... | ... | ... | ... | ... | {len(payload['stories']) - 100} more stories omitted |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(
    reports: list[dict[str, Any]],
    db_path: Path,
    out_dir: Path,
    story_filters: list[str],
    limit: int | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stories_dir = out_dir / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)

    for story in reports:
        dump_json(stories_dir / f"{safe_filename(story['storyKey'])}.json", story)

    summary = summarize(reports)
    payload = branch_index_payload(reports, summary, db_path, out_dir, story_filters, limit)
    dump_json(out_dir / "branch_index.json", payload)
    write_summary_md(out_dir / "summary.md", payload)
    return payload


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recover Endfield story option branch reports from the source graph SQLite database.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"source graph database (default: {DEFAULT_DB})")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"report directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--story", action="append", help="story key, substring, glob, or comma-list filter")
    parser.add_argument("--limit", type=positive_int, help="maximum number of matching stories to emit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = args.db
    out_dir = args.out_dir
    story_filters = parse_story_filters(args.story)

    if not db_path.exists():
        parser.error(f"database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        reports = build_reports(conn, story_filters, args.limit)

    payload = write_reports(reports, db_path, out_dir, story_filters, args.limit)
    summary = payload["summary"]
    print(
        "wrote {stories} stories, {groups} groups, {options} options, {gaps} unresolved gaps to {out}".format(
            stories=summary["storyCount"],
            groups=summary["optionGroupCount"],
            options=summary["optionCount"],
            gaps=summary["unresolvedGapCount"],
            out=out_dir,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
