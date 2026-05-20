#!/usr/bin/env python3
"""Trace compact 0x0a03 LevelScript gate records.

The `0x0a03/0x00` family is a compact condition/gate shape. Many rows carry
an authored property key plus a post-key 0/1 flag, and some carry a trailing
small integer that resolves to a local LevelScript action id. This audit keeps
those fields diagnostic, walks the local refs when present, and cross-checks
MissionRuntime property conditions that point at the same `(level, script,
key)` triple.

Output:

    reports/mission_order/levelscript_gate_audit_CN.json
    reports/mission_order/levelscript_gate_audit_CN.md
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
GATE_KEY = (0x0A03, 0x00)
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
    "levelseq_",
)


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
    gate = (decoded or {}).get("compactGate")
    if isinstance(gate, dict):
        text = safe_text(gate.get("propertyKey"))
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
    gate = decoded.get("compactGate") if isinstance(decoded.get("compactGate"), dict) else {}
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
        "compactGate": gate,
        "gateLocalRefs": decoded.get("gateLocalRefs") or [],
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


def walk_local_targets(
    *,
    data: bytes,
    roots: list[int],
    by_local_id: dict[int, list[dict[str, Any]]],
    next_by_start: dict[int, int | None],
    action_index_by_start: dict[int, int],
    action_role_by_start: dict[int, str],
    root_kind: str,
    max_depth: int,
    max_nodes: int,
) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for root_index, root_local_id in enumerate(roots):
        queue: deque[tuple[int, str, int]] = deque([(int(root_local_id), root_kind, 0)])
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
                        queue.append((ref, "terminal-branch", depth + 1))
                for ref in compact.get("gateLocalRefs") or []:
                    if isinstance(ref, int):
                        queue.append((ref, "nested-gate", depth + 1))
        paths.append({
            "rootIndex": root_index,
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
        if (record.get("code"), record.get("kind")) != GATE_KEY:
            continue
        start = int(record.get("start") or 0)
        compact = compact_record(
            record,
            data=data,
            next_start=next_by_start.get(start),
            action_index_by_start=action_index_by_start,
            action_role_by_start=action_role_by_start,
        )
        gate = compact.get("compactGate") if isinstance(compact.get("compactGate"), dict) else {}
        keys = [
            safe_text(key)
            for key in compact.get("propertyKeys") or []
            if safe_text(key)
        ]
        gate_key = safe_text(gate.get("propertyKey"))
        if gate_key and gate_key not in keys:
            keys.append(gate_key)

        bridge_matches: list[dict[str, Any]] = []
        bridge_missions: list[str] = []
        for key in keys:
            match = property_flow_lookup.get((level_id, script_id, key))
            if not match:
                continue
            bridge_matches.append({"key": key, **match})
            for mission in match.get("missions") or []:
                if mission not in bridge_missions:
                    bridge_missions.append(mission)

        gate_refs = [int(ref) for ref in compact.get("gateLocalRefs") or [] if isinstance(ref, int)]
        gate_paths = walk_local_targets(
            data=data,
            roots=gate_refs,
            by_local_id=by_local_id,
            next_by_start=next_by_start,
            action_index_by_start=action_index_by_start,
            action_role_by_start=action_role_by_start,
            root_kind="gate-ref",
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
        next_id = compact.get("nextId")
        next_paths = walk_local_targets(
            data=data,
            roots=[next_id] if isinstance(next_id, int) and next_id >= 0 else [],
            by_local_id=by_local_id,
            next_by_start=next_by_start,
            action_index_by_start=action_index_by_start,
            action_role_by_start=action_role_by_start,
            root_kind="record-next",
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
        all_gate_nodes = [
            node
            for path in gate_paths
            for node in path.get("nodes") or []
            if isinstance(node, dict)
        ]
        all_next_nodes = [
            node
            for path in next_paths
            for node in path.get("nodes") or []
            if isinstance(node, dict)
        ]
        rows.append({
            "levelId": level_id,
            "scriptId": script_id,
            "file": repo_rel(file_path),
            "actionMap": {
                "status": action_header.get("status") or "",
                "recordCount": action_header.get("recordCount"),
                "listCounts": action_header.get("listCounts") or {},
            },
            "gate": compact,
            "bridgeMatches": bridge_matches,
            "bridgeMissions": bridge_missions,
            "gateTargetSummary": summarize_nodes(all_gate_nodes),
            "nextTargetSummary": summarize_nodes(all_next_nodes),
            "gatePaths": gate_paths,
            "nextPaths": next_paths,
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

    schema_counter = Counter()
    type_counter = Counter()
    post_flag_counter = Counter()
    gate_class_counter = Counter()
    next_class_counter = Counter()
    bridge_mission_counter = Counter()
    for row in rows:
        gate = (row.get("gate") or {}).get("compactGate") or {}
        schema_counter[safe_text(gate.get("schema")) or "unknown"] += 1
        type_counter[safe_text(gate.get("typeCode")) or "none"] += 1
        post_flag_counter[safe_text(gate.get("postFlag")) or "none"] += 1
        gate_class_counter.update((row.get("gateTargetSummary") or {}).get("classes") or {})
        next_class_counter.update((row.get("nextTargetSummary") or {}).get("classes") or {})
        for mission in row.get("bridgeMissions") or []:
            bridge_mission_counter[mission] += 1

    def has_story_or_play(summary: dict[str, Any]) -> bool:
        return bool(summary.get("storyRefs") or summary.get("playRecords"))

    rows.sort(key=lambda row: (
        0 if row.get("bridgeMatches") else 1,
        0 if has_story_or_play(row.get("gateTargetSummary") or {}) else 1,
        safe_text(row.get("levelId")),
        safe_text(row.get("scriptId")),
        int((row.get("gate") or {}).get("start") or 0),
    ))
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRoot": repo_rel(LEVELSCRIPT_DIR),
        "language": language,
        "summary": {
            "gateRows": len(rows),
            "rowsWithPropertyKey": sum(1 for row in rows if ((row.get("gate") or {}).get("compactGate") or {}).get("propertyKey")),
            "rowsWithGateLocalRefs": sum(1 for row in rows if (row.get("gate") or {}).get("gateLocalRefs")),
            "rowsWithPropertyFlowBridge": sum(1 for row in rows if row.get("bridgeMatches")),
            "rowsWithGateStoryTargets": sum(1 for row in rows if (row.get("gateTargetSummary") or {}).get("storyRefs")),
            "rowsWithGatePlayTargets": sum(1 for row in rows if (row.get("gateTargetSummary") or {}).get("playRecords")),
            "rowsWithNextStoryTargets": sum(1 for row in rows if (row.get("nextTargetSummary") or {}).get("storyRefs")),
            "rowsWithNextPlayTargets": sum(1 for row in rows if (row.get("nextTargetSummary") or {}).get("playRecords")),
            "schemas": dict(schema_counter.most_common(8)),
            "typeCodes": dict(type_counter.most_common(8)),
            "postFlags": dict(post_flag_counter.most_common(8)),
            "gateTargetClasses": dict(gate_class_counter.most_common(8)),
            "nextTargetClasses": dict(next_class_counter.most_common(8)),
            "bridgeMissions": dict(bridge_mission_counter.most_common(12)),
            "maxDepth": max_depth,
            "maxNodesPerPath": max_nodes,
        },
        "rows": rows,
    }


def short_counts(values: dict[str, Any], limit: int = 6) -> str:
    if not values:
        return ""
    return ", ".join(f"{key}:{value}" for key, value in list(values.items())[:limit])


def target_bits(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    if summary.get("storyRefs"):
        parts.append("story " + ", ".join(summary.get("storyRefs")[:4]))
    if summary.get("playRecords"):
        play_bits = [
            f"{play.get('localId')}:{play.get('class')}"
            for play in (summary.get("playRecords") or [])[:4]
        ]
        parts.append("play " + ", ".join(play_bits))
    if summary.get("missingLocalIds") and not parts:
        parts.append("missing " + ",".join(str(value) for value in summary.get("missingLocalIds")[:4]))
    return "; ".join(parts)


def markdown_report(payload: dict[str, Any], *, top_rows: int) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# LevelScript 0x0a03 Gate Audit",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Gate rows: `{summary.get('gateRows')}`",
        f"- Rows with decoded property key: `{summary.get('rowsWithPropertyKey')}`",
        f"- Rows with trailing gate local refs: `{summary.get('rowsWithGateLocalRefs')}`",
        f"- Rows bridged from MissionRuntime property checks: `{summary.get('rowsWithPropertyFlowBridge')}`",
        f"- Gate-ref walks with story/play targets: `{summary.get('rowsWithGateStoryTargets')}` / `{summary.get('rowsWithGatePlayTargets')}`",
        f"- Record-next walks with story/play targets: `{summary.get('rowsWithNextStoryTargets')}` / `{summary.get('rowsWithNextPlayTargets')}`",
        f"- Schemas: `{md_escape(short_counts(summary.get('schemas') or {}, 8))}`",
        f"- Type codes: `{md_escape(short_counts(summary.get('typeCodes') or {}, 8))}`",
        f"- Post flags: `{md_escape(short_counts(summary.get('postFlags') or {}, 8))}`",
        "",
        "## Interpretation",
        "",
        "- `0x0a03/0x00` is a compact condition/gate shape, not setter proof.",
        "- The trailing small int, when present, is walked as a local action ref; `nextId` is reported separately because it is less specific.",
        "- MissionRuntime bridges prove that a quest checks the same key in the same script, but a gate walk only becomes timeline evidence if it reaches concrete play/story actions.",
        "",
        "## MissionRuntime-bridged Gate Rows",
        "",
        "| map/script | local | key | type/post | gate refs | missions | gate targets | next targets |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    bridged = [row for row in payload.get("rows") or [] if row.get("bridgeMatches")]
    if not bridged:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |")
    for row in bridged[:top_rows]:
        gate_record = row.get("gate") or {}
        gate = gate_record.get("compactGate") or {}
        key_text = gate.get("propertyKey") or ", ".join(gate_record.get("propertyKeys") or gate_record.get("texts") or [])
        lines.append(
            f"| `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}` "
            f"| `{gate_record.get('localId')}` "
            f"| `{md_escape(key_text)}` "
            f"| `{md_escape(str(gate.get('typeCode')) + '/' + str(gate.get('postFlag')) )}` "
            f"| `{md_escape(', '.join(str(ref) for ref in gate_record.get('gateLocalRefs') or []))}` "
            f"| `{md_escape(', '.join(row.get('bridgeMissions') or []))}` "
            f"| `{md_escape(target_bits(row.get('gateTargetSummary') or {}))}` "
            f"| `{md_escape(target_bits(row.get('nextTargetSummary') or {}))}` |"
        )

    target_rows = [
        row
        for row in payload.get("rows") or []
        if target_bits(row.get("gateTargetSummary") or {})
    ]
    lines.extend([
        "",
        "## Gate Refs With Targets",
        "",
        "| map/script | local | key | type/post | refs | classes | targets |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ])
    if not target_rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |")
    for row in target_rows[:top_rows]:
        gate_record = row.get("gate") or {}
        gate = gate_record.get("compactGate") or {}
        key_text = gate.get("propertyKey") or ", ".join(gate_record.get("propertyKeys") or gate_record.get("texts") or [])
        gate_summary = row.get("gateTargetSummary") or {}
        lines.append(
            f"| `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}` "
            f"| `{gate_record.get('localId')}` "
            f"| `{md_escape(key_text)}` "
            f"| `{md_escape(str(gate.get('typeCode')) + '/' + str(gate.get('postFlag')) )}` "
            f"| `{md_escape(', '.join(str(ref) for ref in gate_record.get('gateLocalRefs') or []))}` "
            f"| `{md_escape(short_counts(gate_summary.get('classes') or {}, 5))}` "
            f"| `{md_escape(target_bits(gate_summary))}` |"
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
    out_json = args.reports_dir / f"levelscript_gate_audit{suffix}.json"
    out_md = args.reports_dir / f"levelscript_gate_audit{suffix}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload, top_rows=max(1, args.top_rows)))
    summary = payload.get("summary") or {}
    print(f"LevelScript gate audit: {out_json}")
    print(f"LevelScript gate report: {out_md}")
    print(
        f"rows={summary.get('gateRows')} "
        f"bridged={summary.get('rowsWithPropertyFlowBridge')} "
        f"gateRefs={summary.get('rowsWithGateLocalRefs')} "
        f"gateStory={summary.get('rowsWithGateStoryTargets')} "
        f"gatePlay={summary.get('rowsWithGatePlayTargets')}"
    )


if __name__ == "__main__":
    main()
