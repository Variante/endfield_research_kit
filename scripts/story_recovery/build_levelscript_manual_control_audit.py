#!/usr/bin/env python3
"""Audit ManualStartLevelScript / ManualEndLevelScript records.

The ActionBase union table names `0x02f1/0x0a` as ManualStartLevelScript and
`0x02ec/0x0a` as ManualEndLevelScript. This report checks how those records
appear in exported LevelScriptData and whether they carry recoverable target
`levelId + scriptId` constants or script-id operands.

Output:

    reports/mission_order/levelscript_manual_control_audit.json
    reports/mission_order/levelscript_manual_control_audit.md
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, rel_path, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.context import LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import _load_levelscript_binding_data  # noqa: E402
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_action_map_header,
    decode_levelscript_record_payload,
)
from build_levelscript_opcode_shape_audit import record_texts  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"

MANUAL_OPCODES = {
    (0x02F1, 0x0A): ("manual-start", "ManualStartLevelScript"),
    (0x02EC, 0x0A): ("manual-end", "ManualEndLevelScript"),
}
EXPECTED_PREV_HINT = {
    "manual-start": "script-event-on-leader-enter-trigger-volume",
    "manual-end": "script-event-on-leader-leave-trigger-volume",
}
STORY_PREFIXES = (
    "dlg_",
    "radio_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "misc_dlg_",
    "levelseq_",
)


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def opcode_key(record: dict[str, Any]) -> str:
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return f"0x{code:04x}/0x{kind:02x}"
    return ""


def payload_window(data: bytes, record: dict[str, Any], next_start: int | None) -> bytes:
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start >= len(data):
        return b""
    if next_start is None or next_start <= payload_start or next_start > len(data):
        next_start = min(len(data), payload_start + 160)
    return data[payload_start:next_start]


def prepare_script_id_bytes(level_ids: set[str]) -> dict[str, list[tuple[str, bytes, bytes]]]:
    out: dict[str, list[tuple[str, bytes, bytes]]] = {}
    for level_id in level_ids:
        rows: list[tuple[str, bytes, bytes]] = []
        level_dir = LEVELSCRIPT_DIR / level_id
        if level_dir.is_dir():
            for path in level_dir.glob("*.json"):
                if not path.stem.isdigit():
                    continue
                value = int(path.stem)
                rows.append((path.stem, struct.pack("<I", value & 0xFFFFFFFF), struct.pack("<Q", value)))
        out[level_id] = rows
    return out


def literal_targets(
    *,
    level_id: str,
    texts: list[str],
    payload: bytes,
    level_ids: set[str],
    script_id_bytes: dict[str, list[tuple[str, bytes, bytes]]],
) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    level_texts = [text for text in texts if text in level_ids]
    search_levels = level_texts or [level_id]
    for candidate_level in search_levels:
        for script_id, raw_u32, raw_u64 in script_id_bytes.get(candidate_level) or []:
            if script_id in texts or raw_u32 in payload[:160] or raw_u64 in payload[:160]:
                hits.append({"levelId": candidate_level, "scriptId": script_id})
                if len(hits) >= 12:
                    return hits
    return hits


def adjacent_record_info(
    *,
    data: bytes,
    records: list[dict[str, Any]],
    starts: list[int],
    by_local: dict[int, int],
    local_id: int | None,
) -> dict[str, Any]:
    if local_id is None or local_id not in by_local:
        return {}
    index = by_local[local_id]
    record = records[index]
    next_start = starts[index + 1] if index + 1 < len(starts) else None
    decoded = decode_levelscript_record_payload(data, record, next_start=next_start)
    return {
        "localId": record.get("localId"),
        "opcode": opcode_key(record),
        "hint": decoded.get("label") or "",
        "nextId": record.get("nextId"),
        "texts": record_texts(record, decoded)[:8],
    }


def collect_story_texts(
    *,
    data: bytes,
    records: list[dict[str, Any]],
    starts: list[int],
) -> list[str]:
    out: list[str] = []
    for index, record in enumerate(records):
        next_start = starts[index + 1] if index + 1 < len(starts) else None
        decoded = decode_levelscript_record_payload(data, record, next_start=next_start)
        for text in record_texts(record, decoded):
            if text.startswith(STORY_PREFIXES) and text not in out:
                out.append(text)
    return out


def build_audit(*, level_filter: str | None = None, sample_limit: int = 200) -> dict[str, Any]:
    level_ids = {
        path.name
        for path in LEVELSCRIPT_DIR.iterdir()
        if path.is_dir() and (not level_filter or path.name == level_filter)
    }
    script_id_bytes = prepare_script_id_bytes(level_ids)

    rows: list[dict[str, Any]] = []
    payload_patterns: Counter[str] = Counter()
    counters = Counter()

    for level_id in sorted(level_ids):
        binding = _load_levelscript_binding_data(level_id)
        for file_info in binding.get("files") or []:
            file_path_text = safe_text(file_info.get("file"))
            file_path = Path(file_path_text)
            if not file_path.is_absolute():
                file_path = ROOT / file_path
            try:
                data = file_path.read_bytes()
            except OSError:
                continue
            records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
            if not records:
                continue
            starts = [int(record.get("start") or 0) for record in records]
            by_local = {
                int(record.get("localId")): index
                for index, record in enumerate(records)
                if isinstance(record.get("localId"), int)
            }
            action_header = decode_levelscript_action_map_header(data)
            action_count = (
                int(action_header.get("recordCount"))
                if action_header.get("status") == "present"
                and isinstance(action_header.get("recordCount"), int)
                else None
            )
            story_texts = collect_story_texts(data=data, records=records, starts=starts)

            for index, record in enumerate(records):
                role_action = MANUAL_OPCODES.get((record.get("code"), record.get("kind")))
                if not role_action:
                    continue
                role, action_name = role_action
                next_start = starts[index + 1] if index + 1 < len(starts) else None
                decoded = decode_levelscript_record_payload(data, record, next_start=next_start)
                payload = payload_window(data, record, next_start)
                manual_control = decoded.get("manualControl") or {}
                payload_shape = safe_text(manual_control.get("payloadShape")) or "unknown"
                payload_patterns[payload[:46].hex(" ")] += 1
                counters["rows"] += 1
                counters[role] += 1
                counters[f"shape:{payload_shape}"] += 1

                local_id = record.get("localId") if isinstance(record.get("localId"), int) else None
                prev_record = adjacent_record_info(
                    data=data,
                    records=records,
                    starts=starts,
                    by_local=by_local,
                    local_id=(local_id - 1) if local_id is not None else None,
                )
                next_record = adjacent_record_info(
                    data=data,
                    records=records,
                    starts=starts,
                    by_local=by_local,
                    local_id=(local_id + 1) if local_id is not None else None,
                )
                expected_prev_hint = EXPECTED_PREV_HINT.get(role)
                activation_pair = bool(expected_prev_hint and prev_record.get("hint") == expected_prev_hint)
                if activation_pair:
                    counters["activationPairs"] += 1
                literal_hits = literal_targets(
                    level_id=level_id,
                    texts=record_texts(record, decoded),
                    payload=payload,
                    level_ids=level_ids,
                    script_id_bytes=script_id_bytes,
                )
                if literal_hits:
                    counters["literalTargets"] += 1
                    script_id = Path(file_path_text).stem
                    if any(
                        hit.get("levelId") == level_id and hit.get("scriptId") == script_id
                        for hit in literal_hits
                    ):
                        counters["literalSelfTargets"] += 1
                    if any(
                        hit.get("levelId") != level_id or hit.get("scriptId") != script_id
                        for hit in literal_hits
                    ):
                        counters["literalCrossTargets"] += 1
                if story_texts:
                    counters["rowsWithStoryTextsInFile"] += 1

                rows.append(
                    {
                        "levelId": level_id,
                        "scriptId": Path(file_path_text).stem,
                        "file": rel_path(file_path),
                        "recordIndex": index,
                        "actionMapRecordCount": action_count,
                        "inActionMap": action_count is not None and index < action_count,
                        "opcode": opcode_key(record),
                        "action": action_name,
                        "role": role,
                        "localId": record.get("localId"),
                        "nextId": record.get("nextId"),
                        "activationPair": activation_pair,
                        "previousLocal": prev_record,
                        "nextLocal": next_record,
                        "literalTargets": literal_hits,
                        "manualControl": manual_control,
                        "storyTextsInFile": story_texts[:12],
                        "payloadLength": len(payload),
                        "payloadHexPrefix": payload[:64].hex(" "),
                    }
                )

    rows.sort(key=lambda row: (row.get("levelId", ""), row.get("scriptId", ""), row.get("localId") or -1))
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRoot": rel_path(LEVELSCRIPT_DIR),
        "summary": {
            "rows": counters.get("rows", 0),
            "manualStartRows": counters.get("manual-start", 0),
            "manualEndRows": counters.get("manual-end", 0),
            "activationPairs": counters.get("activationPairs", 0),
            "literalTargetRows": counters.get("literalTargets", 0),
            "literalSelfTargetRows": counters.get("literalSelfTargets", 0),
            "literalCrossTargetRows": counters.get("literalCrossTargets", 0),
            "rowsWithStoryTextsInFile": counters.get("rowsWithStoryTextsInFile", 0),
            "payloadShapes": {
                key.split(":", 1)[1]: value
                for key, value in counters.items()
                if key.startswith("shape:")
            },
            "payloadPatternCount": len(payload_patterns),
            "topPayloadPatterns": [
                {"count": count, "payloadHexPrefix": payload}
                for payload, count in payload_patterns.most_common(8)
            ],
        },
        "interpretation": [
            "ManualStartLevelScript and ManualEndLevelScript are present as ActionBase records.",
            "Most payloads do not contain literal target levelId/scriptId constants; a few carry a script-id operand without a literal level id.",
            "The currently decoded literal script-id operands are self-targets, not cross-script edges.",
            "Most rows are paired with the preceding trigger-volume enter/leave ScriptEvent by local id; this is script activation evidence, not a cross-script timeline edge.",
        ],
        "rows": rows[:sample_limit],
    }


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# LevelScript Manual Control Audit",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- Manual control rows: `{summary.get('rows')}`",
        f"- ManualStart rows: `{summary.get('manualStartRows')}`",
        f"- ManualEnd rows: `{summary.get('manualEndRows')}`",
        f"- Trigger-adjacent activation pairs: `{summary.get('activationPairs')}`",
        f"- Rows with literal script-id operands: `{summary.get('literalTargetRows')}`",
        f"- Literal script-id self-target rows: `{summary.get('literalSelfTargetRows')}`",
        f"- Literal script-id cross-target rows: `{summary.get('literalCrossTargetRows')}`",
        f"- Rows whose file also contains story/playback text: `{summary.get('rowsWithStoryTextsInFile')}`",
        f"- Payload shapes: `{summary.get('payloadShapes')}`",
        f"- Distinct payload prefixes: `{summary.get('payloadPatternCount')}`",
        "",
        "## Interpretation",
        "",
    ]
    for note in payload.get("interpretation") or []:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| file | local | action | activation pair | previous local | next local | story texts in file |",
            "| --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload.get("rows") or []:
        prev = row.get("previousLocal") or {}
        nxt = row.get("nextLocal") or {}
        prev_text = (
            f"{prev.get('localId')} {prev.get('opcode')} {prev.get('hint')}".strip()
            if prev
            else ""
        )
        next_text = (
            f"{nxt.get('localId')} {nxt.get('opcode')} {nxt.get('hint')}".strip()
            if nxt
            else ""
        )
        lines.append(
            "| "
            + " | ".join(
                md_escape(value)
                for value in [
                    f"{row.get('levelId')}/{row.get('scriptId')}",
                    row.get("localId"),
                    row.get("action"),
                    "yes" if row.get("activationPair") else "",
                    prev_text,
                    next_text,
                    ", ".join(row.get("storyTextsInFile") or []),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Payload Prefixes", ""])
    lines.append("| count | prefix |")
    lines.append("| ---: | --- |")
    for row in summary.get("topPayloadPatterns") or []:
        lines.append(f"| {row.get('count')} | `{md_escape(row.get('payloadHexPrefix'))}` |")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default=None, help="Optional LevelScriptData level id filter")
    parser.add_argument("--sample-limit", type=int, default=200)
    parser.add_argument(
        "--json",
        type=Path,
        default=REPORT_DIR / "levelscript_manual_control_audit.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=REPORT_DIR / "levelscript_manual_control_audit.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_audit(level_filter=args.level, sample_limit=args.sample_limit)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, markdown_report(payload))
    summary = payload.get("summary") or {}
    print(
        "wrote "
        f"{rel_path(args.json)} and {rel_path(args.markdown)} "
        f"(rows={summary.get('rows')}, activationPairs={summary.get('activationPairs')}, "
        f"literalScriptTargets={summary.get('literalTargetRows')})"
    )


if __name__ == "__main__":
    main()
