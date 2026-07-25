#!/usr/bin/env python3
"""Audit the physical ActionSerializedMap list blocks in LevelScriptData.

The shared LevelScript binary helper now splits each serialized action map into
three UID-record lists. This report keeps that split honest by comparing the
physical list positions against the IL2CPP type evidence and observed opcode
content signatures.

Output:

    reports/mission_order/levelscript_action_map_list_audit.json
    reports/mission_order/levelscript_action_map_list_audit.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.context import LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    _load_levelscript_binding_data,
    classify_levelscript_record,
)
from story_builder.levelscript_binary import (  # noqa: E402
    ACTION_SERIALIZED_MAP_LIST_ORDER,
    ACTION_SERIALIZED_MAP_ORDER_EVIDENCE,
    decode_levelscript_action_map_lists,
    decode_levelscript_record_payload,
    LEVELSCRIPT_NATIVE_HEADER_NAMES,
)

OUTPUT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_UNION_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "memorypack_union_formatter_tag_audit.json"
)
SELECTED_OPCODES = (
    "0x0a03/0x00",
    "0x0bed/0x00",
    "0x12ba/0x00",
    "0x12be/0x00",
    "0x12c0/0x00",
    "0x1355/0x00",
    "0x1385/0x00",
)
TARGET_UNION_TABLES = {
    "Beyond_Gameplay_Actions_ActionBase",
    "Beyond_Gameplay_Actions_PureGetter",
    "Beyond_Gameplay_Actions_ActionHeader",
    "Beyond_Gameplay_Actions_ScriptEventHeader",
}


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join(md_escape(value) for value in values) + " |"


def opcode_key(record: dict[str, Any]) -> str:
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return f"0x{code:04x}/0x{kind:02x}"
    return "unknown"


def load_union_tables(path: Path) -> dict[str, dict[int, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, dict[int, str]] = {}
    for table in payload.get("tables") or []:
        display_name = str(table.get("displayName") or "")
        if display_name not in TARGET_UNION_TABLES:
            continue
        rows: dict[int, str] = {}
        for row in table.get("tagRows") or []:
            tag = row.get("tag")
            if not isinstance(tag, int):
                continue
            name = str(row.get("actionName") or row.get("formatterName") or "")
            rows[tag] = name
        out[display_name] = rows
    return out


def derived_script_event_name(
    *,
    code: int,
    kind: int,
    tables: dict[str, dict[int, str]],
) -> str:
    if kind != 0:
        return ""
    return LEVELSCRIPT_NATIVE_HEADER_NAMES.get((code, kind), "")


def expected_union_name(
    *,
    list_name: str,
    code: int | None,
    kind: int | None,
    tables: dict[str, dict[int, str]],
) -> str:
    if not isinstance(code, int) or not isinstance(kind, int):
        return ""
    if list_name == "actionList":
        name = (tables.get("Beyond_Gameplay_Actions_ActionBase") or {}).get(code)
        return f"ActionBase:{name}" if name else ""
    if list_name == "getterList":
        name = (tables.get("Beyond_Gameplay_Actions_PureGetter") or {}).get(code)
        if name:
            return f"PureGetter:{name}"
        derived = derived_script_event_name(code=code, kind=kind, tables=tables)
        return f"ActionHeader:{derived} (current native)" if derived else ""
    if list_name == "headerList":
        derived = derived_script_event_name(code=code, kind=kind, tables=tables)
        if derived:
            return f"ActionHeader:{derived} (current native)"
        name = (tables.get("Beyond_Gameplay_Actions_ActionHeader") or {}).get(code)
        return f"ActionHeader:{name}" if name else ""
    return ""


def next_record_start(records: list[dict[str, Any]], index: int, data_len: int) -> int:
    if index + 1 < len(records):
        try:
            return int(records[index + 1].get("start") or data_len)
        except (TypeError, ValueError):
            return data_len
    return data_len


def build_report(*, union_audit: Path, top_limit: int) -> dict[str, Any]:
    union_tables = load_union_tables(union_audit)
    list_stats: dict[str, dict[str, Any]] = {}
    selected_by_list: dict[str, Counter[str]] = defaultdict(Counter)
    physical_counts: Counter[str] = Counter()
    files_with_three_rows = 0
    files_with_three_present_lists = 0
    files_with_inferred_omitted_getter = 0
    list_status_counts: Counter[str] = Counter()
    decoded_files = 0
    total_records = 0
    sample_files: list[dict[str, Any]] = []

    def ensure_list(name: str, rank: int) -> dict[str, Any]:
        if name not in list_stats:
            list_stats[name] = {
                "name": name,
                "physicalRank": rank,
                "recordCount": 0,
                "opcodeCounts": Counter(),
                "hintCounts": Counter(),
                "classCounts": Counter(),
                "expectedUnionCounts": Counter(),
                "expectedByOpcode": defaultdict(Counter),
                "scriptEventDerivedCount": 0,
                "samplesByOpcode": defaultdict(list),
            }
        return list_stats[name]

    for level_dir in sorted(path for path in LEVELSCRIPT_DIR.iterdir() if path.is_dir()):
        level_id = level_dir.name
        info = _load_levelscript_binding_data(level_id)
        for file_info in info.get("files") or []:
            records = sorted(
                list(file_info.get("records") or []),
                key=lambda record: int(record.get("start") or 0),
            )
            if not records:
                continue
            path = ROOT / str(file_info.get("file") or "")
            try:
                data = path.read_bytes()
            except OSError:
                continue

            action_map = decode_levelscript_action_map_lists(data, records)
            serialized_lists = [
                row
                for row in action_map.get("serializedLists") or []
                if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
            ]
            if not serialized_lists:
                continue
            decoded_files += 1
            for row in serialized_lists:
                list_status_counts[f"{row.get('name')}:{row.get('status')}"] += 1
            present_list_names = {
                str(row.get("name") or "")
                for row in serialized_lists
                if row.get("status") == "present" and int(row.get("decodedRecordCount") or 0) > 0
            }
            if set(ACTION_SERIALIZED_MAP_LIST_ORDER).issubset(present_list_names):
                files_with_three_present_lists += 1
            if any(
                row.get("name") == "getterList"
                and row.get("status") == "omitted-or-empty-before-headerList"
                for row in serialized_lists
            ):
                files_with_inferred_omitted_getter += 1
            if len(serialized_lists) >= 3:
                files_with_three_rows += 1
                if len(sample_files) < 8:
                    sample_files.append(
                        {
                            "levelId": level_id,
                            "scriptId": file_info.get("fileStem"),
                            "file": file_info.get("file"),
                            "lists": [
                                {
                                    "rank": index + 1,
                                    "name": row.get("name"),
                                    "count": row.get("count"),
                                    "recordIndexStart": row.get("recordIndexStart"),
                                    "recordIndexEnd": row.get("recordIndexEnd"),
                                    "countOffset": row.get("countOffset"),
                                }
                                for index, row in enumerate(serialized_lists[:3])
                            ],
                        }
                    )

            for rank, list_info in enumerate(serialized_lists[:3], start=1):
                list_name = str(list_info.get("name") or f"physical#{rank}")
                stats = ensure_list(list_name, rank)
                start_index = int(list_info.get("recordIndexStart") or 0)
                end_index = int(list_info.get("recordIndexEnd") or start_index)
                physical_counts[f"physical#{rank}:{list_name}"] += max(0, end_index - start_index)
                for index in range(start_index, min(end_index, len(records))):
                    record = records[index]
                    key = opcode_key(record)
                    decoded = decode_levelscript_record_payload(
                        data,
                        record,
                        next_start=next_record_start(records, index, len(data)),
                    )
                    hint = str(decoded.get("label") or "-")
                    cls = classify_levelscript_record(record) or "-"
                    code = record.get("code")
                    kind = record.get("kind")
                    expected = expected_union_name(
                        list_name=list_name,
                        code=code if isinstance(code, int) else None,
                        kind=kind if isinstance(kind, int) else None,
                        tables=union_tables,
                    )
                    derived = (
                        derived_script_event_name(
                            code=code,
                            kind=kind,
                            tables=union_tables,
                        )
                        if isinstance(code, int) and isinstance(kind, int)
                        else ""
                    )

                    stats["recordCount"] += 1
                    total_records += 1
                    stats["opcodeCounts"][key] += 1
                    stats["hintCounts"][hint] += 1
                    stats["classCounts"][cls] += 1
                    if expected:
                        stats["expectedUnionCounts"][expected] += 1
                        stats["expectedByOpcode"][key][expected] += 1
                    if derived:
                        stats["scriptEventDerivedCount"] += 1
                    if key in SELECTED_OPCODES:
                        selected_by_list[key][list_name] += 1
                    samples = stats["samplesByOpcode"][key]
                    if len(samples) < 3:
                        samples.append(
                            {
                                "levelId": level_id,
                                "scriptId": file_info.get("fileStem"),
                                "offset": f"0x{int(record.get('start') or 0):x}",
                                "localId": record.get("localId"),
                                "nextId": record.get("nextId"),
                                "hint": hint,
                                "expectedUnion": expected,
                            }
                        )

    list_rows: list[dict[str, Any]] = []
    for list_name in ACTION_SERIALIZED_MAP_LIST_ORDER:
        stats = list_stats.get(list_name)
        if not stats:
            continue
        opcode_counts: Counter[str] = stats["opcodeCounts"]
        list_rows.append(
            {
                "name": list_name,
                "physicalRank": stats["physicalRank"],
                "recordCount": stats["recordCount"],
                "topOpcodes": [
                    {
                        "opcode": key,
                        "count": count,
                        "expectedUnions": dict(
                            stats["expectedByOpcode"].get(key, Counter()).most_common(3)
                        ),
                        "samples": stats["samplesByOpcode"].get(key) or [],
                    }
                    for key, count in opcode_counts.most_common(top_limit)
                ],
                "topHints": dict(stats["hintCounts"].most_common(top_limit)),
                "topClasses": dict(stats["classCounts"].most_common(8)),
                "topExpectedUnions": dict(stats["expectedUnionCounts"].most_common(top_limit)),
                "scriptEventDerivedCount": stats["scriptEventDerivedCount"],
            }
        )

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "levelScriptDir": str(LEVELSCRIPT_DIR),
        "unionAudit": repo_rel(union_audit),
        "listOrder": list(ACTION_SERIALIZED_MAP_LIST_ORDER),
        "listOrderEvidence": ACTION_SERIALIZED_MAP_ORDER_EVIDENCE,
        "summary": {
            "decodedFiles": decoded_files,
            "filesWithThreeListRows": files_with_three_rows,
            "filesWithThreePresentLists": files_with_three_present_lists,
            "filesWithInferredOmittedGetter": files_with_inferred_omitted_getter,
            "serializedRecords": total_records,
            "physicalCounts": dict(physical_counts),
            "listStatusCounts": dict(list_status_counts),
        },
        "keyFindings": [
            (
                "Keep the split as actionList, getterList, headerList: "
                "GameAssembly dispatches set___actionList__, set___getterList__, "
                "then set___headerList__; MetadataRegistration resolves those fields "
                "to List<ActionBase>, List<PureGetter>, and List<ActionHeader>; and "
                "the second/third physical blocks match getter/header content signatures."
            ),
            (
                "Some two-block files omit an empty getterList and carry a final "
                "header-shaped block; those are inferred as headerList. A smaller "
                "set of ambiguous post-action blocks remains, but the current scan "
                "keeps derived ScriptEventHeader-band rows out of getterList."
            ),
            (
                "0x0a03/0x00 sits in getterList, consistent with a compact property "
                "gate/read family; 0x0bed/0x00 sits in actionList, consistent with a "
                "terminal action-branch family."
            ),
        ],
        "lists": list_rows,
        "selectedOpcodesByList": {
            opcode: dict(counter)
            for opcode, counter in selected_by_list.items()
        },
        "sampleFiles": sample_files,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# LevelScript Action Map List Audit",
        "",
        f"Generated: {payload.get('generatedAt')}",
        "",
        "## Summary",
        "",
        f"- LevelScriptData root: `{md_escape(payload.get('levelScriptDir'))}`",
        f"- Union audit: `{md_escape(payload.get('unionAudit'))}`",
        f"- Decoded files: `{summary.get('decodedFiles')}`",
        f"- Files with three list rows: `{summary.get('filesWithThreeListRows')}`",
        f"- Files with all three lists present: `{summary.get('filesWithThreePresentLists')}`",
        f"- Files with inferred omitted getterList: `{summary.get('filesWithInferredOmittedGetter')}`",
        f"- Serialized UID records in first three lists: `{summary.get('serializedRecords')}`",
        f"- Decoded list order: `{', '.join(payload.get('listOrder') or [])}`",
        "",
        "## Key Findings",
        "",
    ]
    for finding in payload.get("keyFindings") or []:
        lines.append(f"- {finding}")

    lines.extend(["", "## Lists", ""])
    lines.append(markdown_table_row(["rank", "list", "records", "derived ScriptEvent rows", "top hints"]))
    lines.append(markdown_table_row(["---:", "---", "---:", "---:", "---"]))
    for row in payload.get("lists") or []:
        top_hints = ", ".join(
            f"{key}:{value}"
            for key, value in (row.get("topHints") or {}).items()
        )
        lines.append(
            markdown_table_row(
                [
                    row.get("physicalRank"),
                    row.get("name"),
                    row.get("recordCount"),
                    row.get("scriptEventDerivedCount"),
                    top_hints,
                ]
            )
        )

    lines.extend(["", "## Selected Opcodes", ""])
    lines.append(markdown_table_row(["opcode", "actionList", "getterList", "headerList"]))
    lines.append(markdown_table_row(["---", "---:", "---:", "---:"]))
    selected = payload.get("selectedOpcodesByList") or {}
    for opcode in SELECTED_OPCODES:
        counts = selected.get(opcode) or {}
        lines.append(
            markdown_table_row(
                [
                    opcode,
                    counts.get("actionList", 0),
                    counts.get("getterList", 0),
                    counts.get("headerList", 0),
                ]
            )
        )

    for row in payload.get("lists") or []:
        lines.extend(["", f"## Top Opcodes: {row.get('name')}", ""])
        lines.append(markdown_table_row(["opcode", "count", "expected union/name samples", "samples"]))
        lines.append(markdown_table_row(["---", "---:", "---", "---"]))
        for opcode_row in row.get("topOpcodes") or []:
            expected_text = ", ".join(
                f"{key}:{value}"
                for key, value in (opcode_row.get("expectedUnions") or {}).items()
            )
            samples = "; ".join(
                f"{sample.get('levelId')}/{sample.get('scriptId')}@{sample.get('offset')}"
                for sample in opcode_row.get("samples") or []
            )
            lines.append(
                markdown_table_row(
                    [
                        opcode_row.get("opcode"),
                        opcode_row.get("count"),
                        expected_text,
                        samples,
                    ]
                )
            )

    lines.extend(["", "## Sample File Boundaries", ""])
    lines.append(markdown_table_row(["levelId", "scriptId", "lists"]))
    lines.append(markdown_table_row(["---", "---", "---"]))
    for row in payload.get("sampleFiles") or []:
        list_text = "; ".join(
            f"#{item.get('rank')} {item.get('name')} count={item.get('count')} offset={item.get('countOffset')}"
            for item in row.get("lists") or []
        )
        lines.append(markdown_table_row([row.get("levelId"), row.get("scriptId"), list_text]))

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--union-audit", type=Path, default=DEFAULT_UNION_AUDIT)
    parser.add_argument(
        "--json",
        type=Path,
        default=OUTPUT_DIR / "levelscript_action_map_list_audit.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=OUTPUT_DIR / "levelscript_action_map_list_audit.md",
    )
    parser.add_argument("--top-limit", type=int, default=18)
    args = parser.parse_args()

    payload = build_report(union_audit=args.union_audit, top_limit=max(1, args.top_limit))
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    print(
        "wrote",
        repo_rel(args.json),
        "and",
        repo_rel(args.markdown),
        "records=",
        (payload.get("summary") or {}).get("serializedRecords"),
    )


if __name__ == "__main__":
    main()
