#!/usr/bin/env python3
"""Trace compact terminal-branch LevelScript records.

The `0x0bed/0x00` record family carries property-like text and two tail
integers that resolve to local LevelScript action ids in observed files. This
audit follows those local ids through normal `nextId` edges, split lists
(`0x0463/0x09`), and nested terminal branches to show what each terminal gate
can activate.

Output:

    reports/mission_order/levelscript_terminal_branch_audit_CN.json
    reports/mission_order/levelscript_terminal_branch_audit_CN.md
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.context import LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import _load_levelscript_binding_data, classify_levelscript_record  # noqa: E402
from story_builder.levelscript_binary import (  # noqa: E402
    levelscript_action_map_membership,
    decode_levelscript_record_payload,
)


REPORT_DIR = ROOT / "reports" / "mission_order"
PLAY_CLASSES = {"play_cutscene", "play_radio", "play_dialog", "play_levelseq"}
STORY_PREFIXES = (
    "dlg_",
    "misc_dlg_",
    "radio_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "sns_",
    "video_cs_video_",
)
TERMINAL_BRANCH_KEY = (0x0BED, 0x00)


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def opcode_key(record: dict[str, Any]) -> str:
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return f"0x{code:04x}/0x{kind:02x}"
    return ""


def record_texts(record: dict[str, Any], decoded: dict[str, Any] | None = None) -> list[str]:
    out: list[str] = []
    for field in (decoded or {}).get("taggedFields") or []:
        if isinstance(field, dict) and field.get("type") == "string":
            text = safe_text(field.get("value"))
            if text and text not in out:
                out.append(text)
    for field_name in ("strings", "plainStrings"):
        for hit in record.get(field_name) or []:
            text = safe_text(hit.get("text") if isinstance(hit, dict) else hit)
            if text and text not in out:
                out.append(text)
    return out


def story_refs(texts: list[str]) -> list[str]:
    refs: list[str] = []
    for text in texts:
        if text.startswith(STORY_PREFIXES) and text not in refs:
            refs.append(text)
    return refs


def next_start_by_record_start(records: list[dict[str, Any]], data_len: int) -> dict[int, int | None]:
    starts: dict[int, int | None] = {}
    sorted_records = sorted(records, key=lambda row: int(row.get("start") or 0))
    for index, record in enumerate(sorted_records):
        start = int(record.get("start") or 0)
        starts[start] = (
            int(sorted_records[index + 1].get("start") or data_len)
            if index + 1 < len(sorted_records)
            else None
        )
    return starts


def action_map_record_metadata(
    data: bytes,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[int, int], dict[int, str]]:
    header, membership_by_start = levelscript_action_map_membership(data, records)
    return header, {}, membership_by_start


def compact_record(
    record: dict[str, Any],
    *,
    data: bytes,
    next_start: int | None,
    action_index_by_start: dict[int, int],
    action_role_by_start: dict[int, str],
) -> dict[str, Any]:
    start = int(record.get("start") or 0)
    decoded = decode_levelscript_record_payload(data, record, next_start=next_start) if data else {}
    texts = record_texts(record, decoded)
    action_role = action_role_by_start.get(start)
    action_map = action_role or "outside"
    row = {
        "offset": f"0x{start:x}",
        "start": start,
        "uid": safe_text(record.get("uid")),
        "localId": record.get("localId"),
        "nextId": record.get("nextId"),
        "opcode": opcode_key(record),
        "class": classify_levelscript_record(record) or "",
        "actionMap": action_map,
        "hint": safe_text(decoded.get("label")),
        "confidence": safe_text(decoded.get("confidence")),
        "propertyKeys": decoded.get("propertyKeys") or [],
        "branchLocalRefs": decoded.get("branchLocalRefs") or [],
        "localRecordRefs": decoded.get("localRecordRefs") or [],
        "storyRefs": story_refs(texts),
        "texts": texts[:10],
    }
    return {key: value for key, value in row.items() if value not in ("", None, [], {})}


def load_property_flow_lookup(language: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    payload = read_json(REPORT_DIR / f"levelscript_property_flow_{language}.json", {})
    lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not isinstance(payload, dict):
        return lookup
    for row in payload.get("rows") or []:
        if not isinstance(row, dict) or row.get("bridgeStatus") != "bridgeFound":
            continue
        map_id = safe_text(row.get("mapId"))
        script_id = safe_text(row.get("scriptId"))
        key = safe_text(row.get("key"))
        if map_id and script_id and key:
            lookup[(map_id, script_id, key)] = {
                "missions": row.get("checkerMissions") or [],
                "questChecks": [
                    {
                        "questId": checker.get("questId"),
                        "type": checker.get("conditionType") or checker.get("type"),
                        "value": checker.get("expectedValue"),
                    }
                    for checker in row.get("checkers") or []
                    if isinstance(checker, dict)
                ],
            }
    return lookup


def summarize_nodes(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    classes = Counter()
    opcodes = Counter()
    story: list[str] = []
    play: list[dict[str, Any]] = []
    missing: list[int] = []
    for node in nodes:
        if "missingLocalId" in node:
            missing.append(int(node.get("missingLocalId") or 0))
            continue
        classes[safe_text(node.get("class")) or "unknown"] += 1
        opcodes[safe_text(node.get("opcode")) or "unknown"] += 1
        for ref in node.get("storyRefs") or []:
            if ref not in story:
                story.append(ref)
        if node.get("class") in PLAY_CLASSES:
            play.append({
                "localId": node.get("localId"),
                "offset": node.get("offset"),
                "class": node.get("class"),
                "storyRefs": node.get("storyRefs") or [],
            })
    return {
        "classes": dict(classes.most_common(8)),
        "opcodes": dict(opcodes.most_common(8)),
        "storyRefs": story[:12],
        "playRecords": play[:12],
        "missingLocalIds": missing[:12],
    }


def walk_branch_targets(
    *,
    data: bytes,
    branch_refs: list[int],
    by_local_id: dict[int, list[dict[str, Any]]],
    next_by_start: dict[int, int | None],
    action_index_by_start: dict[int, int],
    action_role_by_start: dict[int, str],
    max_depth: int,
    max_nodes: int,
) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for branch_index, root_local_id in enumerate(branch_refs):
        queue: deque[tuple[int, str, int]] = deque([(int(root_local_id), "branch", 0)])
        seen_starts: set[int] = set()
        nodes: list[dict[str, Any]] = []
        while queue and len(nodes) < max_nodes:
            local_id, via, depth = queue.popleft()
            targets = by_local_id.get(local_id) or []
            if not targets:
                nodes.append({"missingLocalId": local_id, "via": via, "depth": depth})
                continue
            for target in targets[:4]:
                start = int(target.get("start") or 0)
                if start in seen_starts:
                    continue
                seen_starts.add(start)
                compact = compact_record(
                    target,
                    data=data,
                    next_start=next_by_start.get(start),
                    action_index_by_start=action_index_by_start,
                    action_role_by_start=action_role_by_start,
                )
                compact["via"] = via
                compact["depth"] = depth
                nodes.append(compact)
                if depth >= max_depth or len(nodes) >= max_nodes:
                    continue

                next_id = target.get("nextId")
                if isinstance(next_id, int) and next_id >= 0:
                    queue.append((next_id, "next", depth + 1))
                for ref in compact.get("localRecordRefs") or []:
                    if isinstance(ref, int):
                        queue.append((ref, "split", depth + 1))
                for ref in compact.get("branchLocalRefs") or []:
                    if isinstance(ref, int):
                        queue.append((ref, "nested-branch", depth + 1))
        paths.append({
            "branchIndex": branch_index,
            "rootLocalId": root_local_id,
            "nodes": nodes,
            "summary": summarize_nodes(nodes),
        })
    return paths


def analyze_file(
    *,
    level_id: str,
    file_info: dict[str, Any],
    property_flow_lookup: dict[tuple[str, str, str], dict[str, Any]],
    max_depth: int,
    max_nodes: int,
) -> list[dict[str, Any]]:
    file_path = Path(safe_text(file_info.get("file")))
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    try:
        data = file_path.read_bytes()
    except OSError:
        return []
    records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
    if not records:
        return []
    script_id = safe_text(file_info.get("fileStem")) or file_path.stem
    next_by_start = next_start_by_record_start(records, len(data))
    action_header, action_index_by_start, action_role_by_start = action_map_record_metadata(data, records)
    by_local_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        local_id = record.get("localId")
        if isinstance(local_id, int):
            by_local_id[local_id].append(record)

    rows: list[dict[str, Any]] = []
    for record in records:
        if (record.get("code"), record.get("kind")) != TERMINAL_BRANCH_KEY:
            continue
        start = int(record.get("start") or 0)
        compact = compact_record(
            record,
            data=data,
            next_start=next_by_start.get(start),
            action_index_by_start=action_index_by_start,
            action_role_by_start=action_role_by_start,
        )
        branch_refs = [int(ref) for ref in compact.get("branchLocalRefs") or [] if isinstance(ref, int)]
        if not branch_refs:
            continue
        bridge_matches: list[dict[str, Any]] = []
        bridge_missions: list[str] = []
        for key in compact.get("propertyKeys") or []:
            match = property_flow_lookup.get((level_id, script_id, safe_text(key)))
            if not match:
                continue
            bridge_matches.append({"key": key, **match})
            for mission in match.get("missions") or []:
                if mission not in bridge_missions:
                    bridge_missions.append(mission)
        branch_paths = walk_branch_targets(
            data=data,
            branch_refs=branch_refs,
            by_local_id=by_local_id,
            next_by_start=next_by_start,
            action_index_by_start=action_index_by_start,
            action_role_by_start=action_role_by_start,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
        all_nodes = [
            node
            for path in branch_paths
            for node in path.get("nodes") or []
            if isinstance(node, dict)
        ]
        target_summary = summarize_nodes(all_nodes)
        rows.append({
            "levelId": level_id,
            "scriptId": script_id,
            "file": repo_rel(file_path),
            "actionMap": {
                "status": action_header.get("status") or "",
                "recordCount": action_header.get("recordCount"),
                "listCounts": action_header.get("listCounts") or {},
            },
            "terminal": compact,
            "bridgeMatches": bridge_matches,
            "bridgeMissions": bridge_missions,
            "targetSummary": target_summary,
            "branchPaths": branch_paths,
        })
    return rows


def build_audit(
    *,
    language: str,
    level_filter: str | None,
    script_filter: str | None,
    max_depth: int,
    max_nodes: int,
) -> dict[str, Any]:
    property_flow_lookup = load_property_flow_lookup(language)
    rows: list[dict[str, Any]] = []
    level_ids = [
        path.name
        for path in LEVELSCRIPT_DIR.iterdir()
        if path.is_dir() and (not level_filter or path.name == level_filter)
    ]
    for level_id in sorted(level_ids):
        binding = _load_levelscript_binding_data(level_id)
        for file_info in binding.get("files") or []:
            script_id = safe_text(file_info.get("fileStem")) or Path(safe_text(file_info.get("file"))).stem
            if script_filter and script_id != script_filter:
                continue
            rows.extend(
                analyze_file(
                    level_id=level_id,
                    file_info=file_info,
                    property_flow_lookup=property_flow_lookup,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                )
            )

    class_counter = Counter()
    opcode_counter = Counter()
    bridge_mission_counter = Counter()
    rows_with_story = 0
    rows_with_play = 0
    for row in rows:
        summary = row.get("targetSummary") or {}
        class_counter.update(summary.get("classes") or {})
        opcode_counter.update(summary.get("opcodes") or {})
        for mission in row.get("bridgeMissions") or []:
            bridge_mission_counter[mission] += 1
        if summary.get("storyRefs"):
            rows_with_story += 1
        if summary.get("playRecords"):
            rows_with_play += 1

    rows.sort(key=lambda row: (
        0 if row.get("bridgeMatches") else 1,
        safe_text(row.get("levelId")),
        safe_text(row.get("scriptId")),
        int((row.get("terminal") or {}).get("start") or 0),
    ))
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRoot": repo_rel(LEVELSCRIPT_DIR),
        "language": language,
        "summary": {
            "terminalBranchRows": len(rows),
            "rowsWithPropertyFlowBridge": sum(1 for row in rows if row.get("bridgeMatches")),
            "rowsWithBridgeMissions": sum(1 for row in rows if row.get("bridgeMissions")),
            "rowsWithStoryTargets": rows_with_story,
            "rowsWithPlayTargets": rows_with_play,
            "targetClasses": dict(class_counter.most_common(12)),
            "targetOpcodes": dict(opcode_counter.most_common(12)),
            "bridgeMissions": dict(bridge_mission_counter.most_common(12)),
            "maxDepth": max_depth,
            "maxNodesPerBranch": max_nodes,
        },
        "rows": rows,
    }


def short_counts(values: dict[str, Any], limit: int = 6) -> str:
    if not values:
        return ""
    return ", ".join(f"{key}:{value}" for key, value in list(values.items())[:limit])


def brief_node_text(nodes: list[dict[str, Any]], limit: int = 5) -> str:
    parts: list[str] = []
    for node in nodes:
        if "missingLocalId" in node:
            parts.append(f"missing:{node.get('missingLocalId')}")
            continue
        cls = safe_text(node.get("class")) or safe_text(node.get("opcode"))
        local_id = node.get("localId")
        suffix = ""
        if node.get("storyRefs"):
            suffix = ":" + ",".join(str(ref) for ref in (node.get("storyRefs") or [])[:2])
        parts.append(f"{local_id}:{cls}{suffix}")
        if len(parts) >= limit:
            break
    return "; ".join(parts)


def markdown_report(payload: dict[str, Any], *, top_rows: int) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# LevelScript Terminal Branch Audit",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Terminal branch rows: `{summary.get('terminalBranchRows')}`",
        f"- Rows bridged from MissionRuntime property checks: `{summary.get('rowsWithPropertyFlowBridge')}`",
        f"- Rows with story-key targets after branch walk: `{summary.get('rowsWithStoryTargets')}`",
        f"- Rows with play-action targets after branch walk: `{summary.get('rowsWithPlayTargets')}`",
        f"- Target classes: `{md_escape(short_counts(summary.get('targetClasses') or {}, 8))}`",
        f"- Target opcodes: `{md_escape(short_counts(summary.get('targetOpcodes') or {}, 8))}`",
        "",
        "## Interpretation",
        "",
        "- `0x0bed/0x00` is now treated as a compact terminal branch candidate, not as setter proof.",
        "- Branch targets are local LevelScript action ids from the record tail; each branch is then walked through `nextId`, split-list refs, and nested branch refs.",
        "- MissionRuntime bridges show which quest/property checks point at the same key, but ordering still depends on the walked target records.",
        "",
        "## MissionRuntime-bridged Branches",
        "",
        "| map/script | local | key | missions | branches | target classes | story/play targets | first walked nodes |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    bridged = [row for row in payload.get("rows") or [] if row.get("bridgeMatches")]
    if not bridged:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |")
    for row in bridged[:top_rows]:
        terminal = row.get("terminal") or {}
        summary_row = row.get("targetSummary") or {}
        nodes = [
            node
            for path in row.get("branchPaths") or []
            for node in path.get("nodes") or []
            if isinstance(node, dict)
        ]
        story_play_bits = []
        if summary_row.get("storyRefs"):
            story_play_bits.append("story " + ", ".join(summary_row.get("storyRefs")[:4]))
        if summary_row.get("playRecords"):
            play_bits = [
                f"{play.get('localId')}:{play.get('class')}"
                for play in (summary_row.get("playRecords") or [])[:4]
            ]
            story_play_bits.append("play " + ", ".join(play_bits))
        lines.append(
            f"| `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}` "
            f"| `{terminal.get('localId')}` "
            f"| `{md_escape(', '.join(terminal.get('propertyKeys') or terminal.get('texts') or []))}` "
            f"| `{md_escape(', '.join(row.get('bridgeMissions') or []))}` "
            f"| `{md_escape(', '.join(str(ref) for ref in terminal.get('branchLocalRefs') or []))}` "
            f"| `{md_escape(short_counts(summary_row.get('classes') or {}, 5))}` "
            f"| `{md_escape('; '.join(story_play_bits))}` "
            f"| `{md_escape(brief_node_text(nodes))}` |"
        )

    rows_with_targets = [
        row
        for row in payload.get("rows") or []
        if (row.get("targetSummary") or {}).get("storyRefs")
        or (row.get("targetSummary") or {}).get("playRecords")
    ]
    lines.extend([
        "",
        "## Rows With Story Or Play Targets",
        "",
        "| map/script | local | key/text | branches | target classes | story/play targets |",
        "| --- | ---: | --- | --- | --- | --- |",
    ])
    if not rows_with_targets:
        lines.append("| _(none)_ |  |  |  |  |  |")
    for row in rows_with_targets[:top_rows]:
        terminal = row.get("terminal") or {}
        summary_row = row.get("targetSummary") or {}
        story_play_bits = []
        if summary_row.get("storyRefs"):
            story_play_bits.append("story " + ", ".join(summary_row.get("storyRefs")[:5]))
        if summary_row.get("playRecords"):
            play_bits = [
                f"{play.get('localId')}:{play.get('class')}"
                for play in (summary_row.get("playRecords") or [])[:5]
            ]
            story_play_bits.append("play " + ", ".join(play_bits))
        lines.append(
            f"| `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}` "
            f"| `{terminal.get('localId')}` "
            f"| `{md_escape(', '.join(terminal.get('propertyKeys') or terminal.get('texts') or []))}` "
            f"| `{md_escape(', '.join(str(ref) for ref in terminal.get('branchLocalRefs') or []))}` "
            f"| `{md_escape(short_counts(summary_row.get('classes') or {}, 5))}` "
            f"| `{md_escape('; '.join(story_play_bits))}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--level", default=None, help="Optional LevelScriptData level id to scan.")
    parser.add_argument("--script", default=None, help="Optional script id/file stem to scan.")
    parser.add_argument("--reports-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--max-nodes", type=int, default=32)
    parser.add_argument("--top-rows", type=int, default=80)
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_audit(
        language=args.language,
        level_filter=args.level,
        script_filter=args.script,
        max_depth=max(0, args.max_depth),
        max_nodes=max(1, args.max_nodes),
    )
    suffix = f"_{args.language}"
    if args.level:
        suffix += f"_{args.level}"
    if args.script:
        suffix += f"_{args.script}"
    out_json = args.reports_dir / f"levelscript_terminal_branch_audit{suffix}.json"
    out_md = args.reports_dir / f"levelscript_terminal_branch_audit{suffix}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload, top_rows=max(1, args.top_rows)))
    summary = payload.get("summary") or {}
    print(f"LevelScript terminal branch audit: {out_json}")
    print(f"LevelScript terminal branch report: {out_md}")
    print(
        f"rows={summary.get('terminalBranchRows')} "
        f"bridged={summary.get('rowsWithPropertyFlowBridge')} "
        f"storyTargets={summary.get('rowsWithStoryTargets')} "
        f"playTargets={summary.get('rowsWithPlayTargets')}"
    )


if __name__ == "__main__":
    main()
