#!/usr/bin/env python3
"""Scan MemoryPack formatter cctors for generated union tag tables.

The ActionBase audit proves that many LevelScript action record `code` values
are MemoryPack union tags. This broader index searches the generated formatter
static constructors for other tag tables, especially candidates that might
explain the high LevelScript event/gate/terminal family.

Output:

    reports/story/recovery/memorypack_union_formatter_tag_audit.json
    reports/story/recovery/memorypack_union_formatter_tag_audit.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402
import build_levelscript_actionbase_tag_audit as actionbase_audit  # noqa: E402

REPORT_DIR = ROOT / "reports" / "story" / "recovery"
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
BODY_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAMEASSEMBLY = actionbase_audit.DEFAULT_GAMEASSEMBLY
DEFAULT_CODE_REGISTRATION = actionbase_audit.DEFAULT_CODE_REGISTRATION
DEFAULT_IMAGE = "MemoryPack.Beyond.dll"
DEFAULT_OPCODE_AUDIT = ROOT / "reports" / "mission_order" / "levelscript_opcode_shape_audit.json"

KEYWORD_RE = re.compile(
    r"(LevelScript|ScriptEvent|Trigger|Condition|Gate|Terminal|Listener|Property|Mission|Scene)",
    re.IGNORECASE,
)
ACTION_HEADER_DERIVED_BASES = tuple(
    {
        "tableDisplayName": "Beyond_Gameplay_Actions_ActionHeader",
        "baseCode": base,
        "kind": 0x00,
        "band": f"action-header-bank-0x{base >> 8:02x}",
        "requireHeaderList": True,
    }
    for base in range(0x0E00, 0x1900, 0x100)
)
DERIVED_OPCODE_BASES = (
    {
        "tableDisplayName": "Beyond_Gameplay_Actions_ScriptEventHeader",
        "baseCode": 0x129E,
        "kind": 0x00,
        "band": "script-event-runtime-band-a",
    },
    {
        "tableDisplayName": "Beyond_Gameplay_Actions_ScriptEventHeader",
        "baseCode": 0x139E,
        "kind": 0x00,
        "band": "script-event-runtime-band-b",
    },
) + ACTION_HEADER_DERIVED_BASES


def repo_rel(path: Path | str) -> str:
    return actionbase_audit.repo_rel(path)


def load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def formatter_display_name(type_name: str) -> str:
    clean = type_name[:-1] if type_name.endswith("&") else type_name
    if "+" in clean:
        clean = clean.split("+", 1)[0]
    for suffix in ("_ForMemoryPack", "ForMemoryPack"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
            break
    return clean


def selected_opcode_codes() -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for opcode in actionbase_audit.SELECTED_OPCODE_KEYS:
        parsed = actionbase_audit.parse_opcode_key(opcode)
        if not parsed:
            continue
        out.setdefault(parsed[0], []).append(opcode)
    return out


def selected_high_opcode_keys() -> list[str]:
    keys: list[str] = []
    for opcode in actionbase_audit.SELECTED_OPCODE_KEYS:
        parsed = actionbase_audit.parse_opcode_key(opcode)
        if parsed and parsed[0] >= 0x0A00:
            keys.append(opcode)
    return keys


def load_opcode_audit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def iter_formatter_cctors(md: Any, *, image_filter: str) -> list[tuple[Any, Any, str, str]]:
    rows: list[tuple[Any, Any, str, str]] = []
    for type_def in md.types:
        full_name = md.type_full_name(type_def)
        if "ForMemoryPack" not in full_name or "Formatter" not in full_name:
            continue
        image_name = md.image_name_by_type_index.get(type_def.index, "")
        if image_filter and image_name != image_filter:
            continue
        for method in md.methods_for(type_def):
            if md.string(method.name_index) == ".cctor":
                rows.append((type_def, method, image_name, full_name))
                break
    return rows


def edge_samples(tag_rows: list[dict[str, Any]], *, size: int = 4) -> list[dict[str, Any]]:
    if len(tag_rows) <= size * 2:
        sample = tag_rows
    else:
        sample = tag_rows[:size] + tag_rows[-size:]
    return [
        {
            "tagHex": row.get("tagHex"),
            "name": row.get("actionName") or formatter_display_name(str(row.get("typeName") or "")),
            "typeName": row.get("typeName"),
        }
        for row in sample
    ]


def scan_formatter_table(
    *,
    pe: Any,
    md: Any,
    body_helper: Any,
    ranges: dict[str, dict[str, int]],
    pointers_by_image: dict[str, list[int]],
    sorted_all_pointers: list[int],
    max_scan_bytes: int,
    full_tag_limit: int,
    selected_codes: dict[int, list[str]],
    type_def: Any,
    method: Any,
    image_name: str,
    full_name: str,
) -> dict[str, Any] | None:
    pointer, slot = actionbase_audit.method_pointer_for(
        method=method,
        image_name=image_name,
        ranges=ranges,
        pointers_by_image=pointers_by_image,
        target_name=f"{full_name}..cctor",
    )
    scan_size, next_pointer = body_helper.estimate_scan_size(pointer, sorted_all_pointers, max_scan_bytes)
    tag_rows, diagnostics = actionbase_audit.extract_formatter_tags(
        pe=pe,
        md=md,
        body_helper=body_helper,
        pointer=pointer,
        scan_size=scan_size,
    )
    if not tag_rows:
        return None

    duplicate_tags, missing_tags, summary = actionbase_audit.tag_table_summary(tag_rows, diagnostics)
    by_tag = {int(row["tag"]): row for row in tag_rows}
    selected_matches: list[dict[str, Any]] = []
    for code, opcodes in selected_codes.items():
        row = by_tag.get(code)
        if not row:
            continue
        selected_matches.append(
            {
                "codeHex": f"0x{code:04x}",
                "opcodes": opcodes,
                "name": row.get("actionName") or formatter_display_name(str(row.get("typeName") or "")),
                "typeName": row.get("typeName"),
                "formatterName": row.get("formatterName"),
            }
        )

    interesting = bool(selected_matches or KEYWORD_RE.search(full_name) or summary.get("tagCount", 0) >= 100)
    table = {
        "type": full_name,
        "displayName": formatter_display_name(full_name),
        "image": image_name,
        "typeIndex": type_def.index,
        "typeToken": f"0x{type_def.token:08x}",
        "methodIndex": method.index,
        "methodToken": f"0x{method.token:08x}",
        "moduleMethodSlot": slot,
        "methodPointerVa": f"0x{pointer:x}",
        "scanBytes": scan_size,
        "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else "",
        "summary": summary,
        "duplicateTags": duplicate_tags,
        "missingTagsInsideRange": missing_tags[:40],
        "keywordCandidate": bool(KEYWORD_RE.search(full_name)),
        "interesting": interesting,
        "selectedOpcodeMatches": selected_matches,
        "tagSamples": edge_samples(tag_rows),
    }
    if selected_matches or int(summary.get("tagCount") or 0) <= full_tag_limit or "Header" in full_name:
        table["tagRows"] = tag_rows
    return table


def derived_opcode_mappings(tables: list[dict[str, Any]], opcode_audit: dict[str, Any]) -> list[dict[str, Any]]:
    row_by_opcode = {
        str(row.get("opcode") or ""): row
        for row in opcode_audit.get("opcodeRows") or []
    }
    table_by_display = {
        str(table.get("displayName") or ""): table
        for table in tables
    }
    out: list[dict[str, Any]] = []
    for spec in DERIVED_OPCODE_BASES:
        table = table_by_display.get(str(spec["tableDisplayName"]))
        if not table:
            continue
        for tag_row in table.get("tagRows") or []:
            tag = int(tag_row.get("tag") or 0)
            code = int(spec["baseCode"]) + tag
            kind = int(spec["kind"])
            opcode = f"0x{code:04x}/0x{kind:02x}"
            opcode_row = row_by_opcode.get(opcode)
            if not opcode_row:
                continue
            header_list_count = sum(
                int(count or 0)
                for role, count in (opcode_row.get("actionMapRoles") or {}).items()
                if str(role).startswith("headerList")
            )
            if spec.get("requireHeaderList") and header_list_count <= 0:
                continue
            out.append(
                {
                    "opcode": opcode,
                    "count": opcode_row.get("count"),
                    "headerListCount": header_list_count,
                    "band": spec.get("band"),
                    "baseCodeHex": f"0x{int(spec['baseCode']):04x}",
                    "headerTagHex": tag_row.get("tagHex"),
                    "headerName": tag_row.get("actionName"),
                    "headerTable": table.get("displayName"),
                    "hints": opcode_row.get("hints") or {},
                    "fieldSignatures": opcode_row.get("fieldSignatures") or {},
                    "actionMapRoles": opcode_row.get("actionMapRoles") or {},
                }
            )
    out.sort(key=lambda row: (str(row.get("band") or ""), str(row.get("opcode") or "")))
    return out


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog_helper = load_module(CATALOG_HELPER, "endfield_catalog_option_flow")
    body_helper = load_module(BODY_HELPER, "endfield_body_targets")
    metadata_path = catalog_helper.resolve_metadata_path(args.metadata, prefer_cache=True)
    md = catalog_helper.Metadata(metadata_path)
    pe = body_helper.PeImage(args.gameassembly)
    code_reg = actionbase_audit.parse_int(args.code_registration)
    modules = body_helper.parse_codegen_modules(pe, code_reg)
    ranges = body_helper.image_method_ranges(md)
    pointers_by_image, _method_by_pointer = body_helper.build_pointer_indexes(pe, md, modules, ranges)
    sorted_all_pointers = sorted(
        {
            pointer
            for pointers in pointers_by_image.values()
            for pointer in pointers
            if pointer
        }
    )
    cctors = iter_formatter_cctors(md, image_filter=args.image)
    selected_codes = selected_opcode_codes()
    errors: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []

    for type_def, method, image_name, full_name in cctors:
        try:
            table = scan_formatter_table(
                pe=pe,
                md=md,
                body_helper=body_helper,
                ranges=ranges,
                pointers_by_image=pointers_by_image,
                sorted_all_pointers=sorted_all_pointers,
                max_scan_bytes=args.max_scan_bytes,
                full_tag_limit=args.full_tag_limit,
                selected_codes=selected_codes,
                type_def=type_def,
                method=method,
                image_name=image_name,
                full_name=full_name,
            )
        except Exception as exc:  # pragma: no cover - report diagnostics only
            errors.append({"type": full_name, "error": str(exc)})
            continue
        if table:
            tables.append(table)

    opcode_audit = load_opcode_audit(args.opcode_audit)
    tables.sort(
        key=lambda table: (
            not bool(table.get("selectedOpcodeMatches")),
            -int((table.get("summary") or {}).get("maxTag") or -1),
            -int((table.get("summary") or {}).get("tagCount") or 0),
            str(table.get("type") or ""),
        )
    )
    selected_matches = [
        {
            "table": table.get("type"),
            "displayName": table.get("displayName"),
            "methodPointerVa": table.get("methodPointerVa"),
            **match,
        }
        for table in tables
        for match in table.get("selectedOpcodeMatches") or []
    ]
    selected_match_counter = Counter(
        opcode
        for match in selected_matches
        for opcode in match.get("opcodes") or []
    )
    high_opcode_keys = selected_high_opcode_keys()
    matched_high_opcode_keys = sorted(
        {
            opcode
            for match in selected_matches
            for opcode in match.get("opcodes") or []
            if opcode in high_opcode_keys
        }
    )
    max_observed_tag = max(
        (int((table.get("summary") or {}).get("maxTag") or -1) for table in tables),
        default=-1,
    )
    derived_mappings = derived_opcode_mappings(tables, opcode_audit)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metadata": {
            "metadataPath": str(metadata_path),
            "gameAssembly": str(args.gameassembly),
            "imageBase": f"0x{pe.image_base:x}",
            "codeRegistration": f"0x{code_reg:x}",
        },
        "settings": {
            "image": args.image,
            "maxScanBytes": args.max_scan_bytes,
            "selectedOpcodes": list(actionbase_audit.SELECTED_OPCODE_KEYS),
            "fullTagLimit": args.full_tag_limit,
            "opcodeAudit": repo_rel(args.opcode_audit),
        },
        "summary": {
            "candidateFormatterCctors": len(cctors),
            "tablesWithUnionTags": len(tables),
            "interestingTables": sum(1 for table in tables if table.get("interesting")),
            "selectedOpcodeMatchCount": len(selected_matches),
            "selectedOpcodeMatchCounts": dict(sorted(selected_match_counter.items())),
            "selectedHighOpcodeMatchCount": len(matched_high_opcode_keys),
            "selectedHighOpcodesAbsent": [
                opcode for opcode in high_opcode_keys
                if opcode not in matched_high_opcode_keys
            ],
            "derivedOpcodeMappingCount": len(derived_mappings),
            "errorCount": len(errors),
            "maxObservedTag": max_observed_tag if max_observed_tag >= 0 else None,
            "maxObservedTagHex": f"0x{max_observed_tag:04x}" if max_observed_tag >= 0 else "",
        },
        "derivedOpcodeMappings": derived_mappings,
        "selectedOpcodeMatches": selected_matches,
        "tables": tables,
        "errors": errors[:40],
    }
    return payload


def markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join(md_escape(value) for value in values) + " |"


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    lines: list[str] = [
        "# MemoryPack Union Formatter Tag Audit",
        "",
        "## Summary",
        "",
        f"- Metadata: `{md_escape(payload['metadata'].get('metadataPath', ''))}`",
        f"- GameAssembly: `{md_escape(payload['metadata'].get('gameAssembly', ''))}`",
        f"- Image filter: `{md_escape(payload['settings'].get('image', ''))}`",
        f"- Formatter cctors scanned: `{summary.get('candidateFormatterCctors')}`",
        f"- Tables with extracted union tags: `{summary.get('tablesWithUnionTags')}`",
        f"- Selected opcode matches: `{summary.get('selectedOpcodeMatchCount')}`",
        f"- Selected high opcode matches: `{summary.get('selectedHighOpcodeMatchCount')}`",
        f"- Derived opcode/header mappings: `{summary.get('derivedOpcodeMappingCount')}`",
        f"- Max observed tag: `{summary.get('maxObservedTagHex')}`",
        f"- Errors: `{summary.get('errorCount')}`",
        "",
        "## Derived Opcode/Header Mappings",
        "",
    ]
    derived = payload.get("derivedOpcodeMappings") or []
    if derived:
        lines.append(markdown_table_row(["opcode", "count", "header rows", "band", "base", "header tag", "header name", "hints"]))
        lines.append(markdown_table_row(["---", "---:", "---:", "---", "---:", "---:", "---", "---"]))
        for row in derived:
            lines.append(
                markdown_table_row(
                    [
                        row.get("opcode", ""),
                        row.get("count", ""),
                        row.get("headerListCount", ""),
                        row.get("band", ""),
                        row.get("baseCodeHex", ""),
                        row.get("headerTagHex", ""),
                        row.get("headerName", ""),
                        ", ".join(f"{k}:{v}" for k, v in (row.get("hints") or {}).items()),
                    ]
                )
            )
    else:
        lines.append("- No observed LevelScript opcode rows matched the configured derived header bases.")

    lines.extend(
        [
            "",
            "## Selected Opcode Matches",
            "",
        ]
    )
    selected = payload.get("selectedOpcodeMatches") or []
    if selected:
        lines.append(markdown_table_row(["opcode(s)", "code", "registered name", "table", "method VA"]))
        lines.append(markdown_table_row(["---", "---:", "---", "---", "---:"]))
        for row in selected:
            lines.append(
                markdown_table_row(
                    [
                        ", ".join(row.get("opcodes") or []),
                        row.get("codeHex", ""),
                        row.get("name", ""),
                        row.get("displayName", ""),
                        row.get("methodPointerVa", ""),
                    ]
                )
            )
    else:
        lines.append("- None of the selected LevelScript opcode codes were found in other extracted MemoryPack union tables.")

    absent_high = summary.get("selectedHighOpcodesAbsent") or []
    if absent_high:
        lines.extend(
            [
                "",
                "Exact high opcode codes absent from raw extracted MemoryPack union tags "
                "(derived header mappings above may still name them): "
                + ", ".join(f"`{md_escape(opcode)}`" for opcode in absent_high)
                + ".",
            ]
        )

    lines.extend(["", "## Largest / Keyword Tables", ""])
    interesting_tables = [
        table for table in payload.get("tables") or []
        if table.get("interesting")
    ]
    if interesting_tables:
        lines.append(markdown_table_row(["table", "tags", "max tag", "keyword", "selected matches", "samples"]))
        lines.append(markdown_table_row(["---", "---:", "---:", "---", "---", "---"]))
        for table in interesting_tables[:80]:
            table_summary = table.get("summary") or {}
            matches = ", ".join(
                match.get("codeHex", "")
                for match in table.get("selectedOpcodeMatches") or []
            )
            samples = ", ".join(
                f"{row.get('tagHex')}:{row.get('name')}"
                for row in table.get("tagSamples") or []
            )
            lines.append(
                markdown_table_row(
                    [
                        table.get("displayName", ""),
                        table_summary.get("tagCount", ""),
                        table_summary.get("maxTagHex", ""),
                        "yes" if table.get("keywordCandidate") else "",
                        matches,
                        samples,
                    ]
                )
            )
    else:
        lines.append("- No interesting tables were extracted.")

    write_text_if_changed(path, "\n".join(lines).rstrip() + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--code-registration", default=DEFAULT_CODE_REGISTRATION)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--max-scan-bytes", type=int, default=0x40000)
    parser.add_argument("--full-tag-limit", type=int, default=32)
    parser.add_argument(
        "--opcode-audit",
        type=Path,
        default=DEFAULT_OPCODE_AUDIT,
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=REPORT_DIR / "memorypack_union_formatter_tag_audit.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=REPORT_DIR / "memorypack_union_formatter_tag_audit.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_report(args)
    write_report_json(args.json, payload)
    write_markdown(args.markdown, payload)
    summary = payload.get("summary") or {}
    print(
        "wrote "
        f"{repo_rel(args.json)} and {repo_rel(args.markdown)} "
        f"(cctors={summary.get('candidateFormatterCctors')}, "
        f"tables={summary.get('tablesWithUnionTags')}, "
        f"selectedMatches={summary.get('selectedOpcodeMatchCount')})"
    )


if __name__ == "__main__":
    main()
