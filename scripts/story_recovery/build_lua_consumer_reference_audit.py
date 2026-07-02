#!/usr/bin/env python3
"""Audit extracted Lua consumers for table, enum, CS, and UI/media references.

The VFS Lua block is already decrypted into plaintext under the structured
export roots. This report turns those scripts into a compact recovery map so
story/UI/table relationships can be prioritized without changing the normal
WebUI export path.

Output:

    reports/mission_order/lua_consumer_reference_audit.json
    reports/mission_order/lua_consumer_reference_audit.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_JSON = REPORT_DIR / "lua_consumer_reference_audit.json"
DEFAULT_MD = REPORT_DIR / "lua_consumer_reference_audit.md"
DEFAULT_LUA_ROOTS = (
    ROOT / "export_full" / "structured" / "Persistent" / "Lua",
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Lua",
)
DEFAULT_TABLE_ROOTS = (
    ROOT / "export_full" / "structured" / "Persistent" / "Table",
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Table",
)

REFERENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("tables", re.compile(r"\bTables\.([A-Za-z_]\w*)")),
    ("gEnums", re.compile(r"\bGEnums\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)")),
    ("csBeyond", re.compile(r"\bCS\.Beyond(?:\.[A-Za-z_]\w*)+")),
    ("contentParam", re.compile(r"\bcontentParam\s*\[\s*([^\]\r\n]+?)\s*\]")),
    ("dialogContentData", re.compile(r"\bdialogContentData\b")),
    ("remoteCommonData", re.compile(r"\bRemoteCommonData\b")),
    ("middleId", re.compile(r"\bmiddleId\b")),
    ("loadSprite", re.compile(r"\b(?:LoadSprite|LoadSpriteAsync|UIUtils\.getSpritePath)\b")),
    ("videoHelper", re.compile(r"\b(?:Video|PlayVideo|OpenVideo|SetVideo|Timeline)\w*\b", re.IGNORECASE)),
    ("audioHelper", re.compile(r"\b(?:Audio|PlayAudio|PostEvent|PlayVoice|voiceId|audioId)\w*\b", re.IGNORECASE)),
)

FOCUS_PATTERNS: dict[str, re.Pattern[str]] = {
    "sns": re.compile(
        r"\bSNS\b|PhaseSNS|SNSUtils|sNS(?:Dialog|Chat)Table|\bfriend\b|\bFriend\b|\bmoment\b",
        re.IGNORECASE,
    ),
    "remotecomm": re.compile(r"RemoteComm|REMOTE_COMM|remote\s*_?\s*comm|\bradio\b|\b[Rr]adio[A-Za-z_]\w*|radioTable", re.IGNORECASE),
    "dialog": re.compile(r"\bDialog\b|\bDIALOG\b|dialogue|contentParam|middleId|dialogContentData|DialogConst", re.IGNORECASE),
    "mapmark": re.compile(r"map\s*_?\s*mark|mapmark|MarkType|MapResource|MapUtils|UI_SPRITE_MAP_MARK", re.IGNORECASE),
    "mission": re.compile(r"\bMission\b|\bMISSION\b|missionTable|MissionSystem|\bquest\b|\btask\b|TaskTrack", re.IGNORECASE),
}


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def parse_csv(values: str) -> list[str]:
    out: list[str] = []
    for value in values.split(","):
        item = value.strip().lower()
        if item and item not in out:
            out.append(item)
    return out


def root_label(root: Path) -> str:
    parts = root.resolve().parts
    for name in ("Persistent", "StreamingAssets"):
        if name in parts:
            return name
    return root.name


def lua_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("**/*.lua"))


def table_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def module_key(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return repo_rel(path)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def line_text(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end < 0:
        end = len(text)
    return text[start:end].strip()[:240]


def add_example(bucket: list[dict[str, Any]], row: dict[str, Any], limit: int) -> None:
    if len(bucket) >= limit:
        return
    bucket.append(row)


def scan_references(
    text: str,
    *,
    rel: str,
    example_limit: int,
) -> tuple[dict[str, Counter[str]], dict[str, list[dict[str, Any]]]]:
    counts: dict[str, Counter[str]] = {name: Counter() for name, _pattern in REFERENCE_PATTERNS}
    examples: dict[str, list[dict[str, Any]]] = {name: [] for name, _pattern in REFERENCE_PATTERNS}
    for category, pattern in REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            value = value.strip()
            counts[category][value] += 1
            add_example(
                examples[category],
                {
                    "path": rel,
                    "line": line_number(text, match.start()),
                    "value": value,
                    "context": line_text(text, match.start()),
                },
                example_limit,
            )
    return counts, examples


def focus_hits(text: str, rel: str, focus_names: list[str], example_limit: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in focus_names:
        pattern = FOCUS_PATTERNS.get(name)
        if not pattern:
            continue
        path_matches = list(pattern.finditer(rel))
        text_matches = list(pattern.finditer(text))
        if not path_matches and not text_matches:
            continue
        examples = []
        for match in path_matches[:example_limit]:
            examples.append(
                {
                    "line": None,
                    "term": match.group(0),
                    "context": f"[path] {rel}",
                }
            )
        for match in text_matches[: max(0, example_limit - len(examples))]:
            examples.append(
                {
                    "line": line_number(text, match.start()),
                    "term": match.group(0),
                    "context": line_text(text, match.start()),
                }
            )
        out[name] = {"hitCount": len(path_matches) + len(text_matches), "examples": examples}
    return out


def counter_rows(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def build_table_index(table_roots: list[Path]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    summaries = []
    for root in table_roots:
        files = table_files(root)
        label = root_label(root)
        summaries.append({"root": repo_rel(root), "label": label, "fileCount": len(files)})
        for path in files:
            stem = path.stem
            key = stem.casefold()
            row = index.setdefault(key, {"table": stem, "roots": [], "paths": []})
            row["roots"].append(label)
            row["paths"].append(repo_rel(path))
    return index, summaries


def table_reference_availability(
    table_refs: Counter[str],
    table_index: dict[str, dict[str, Any]],
    *,
    limit: int,
) -> dict[str, Any]:
    matched = []
    unmatched = []
    for value, count in table_refs.most_common():
        row = table_index.get(value.casefold())
        out = {"value": value, "count": count}
        if row:
            out.update({"table": row["table"], "roots": sorted(set(row["roots"])), "paths": row["paths"][:4]})
            matched.append(out)
        else:
            unmatched.append(out)
    return {
        "availableTableCount": len(table_index),
        "referencedTableCount": len(table_refs),
        "matchedReferencedTableCount": len(matched),
        "unmatchedReferencedTableCount": len(unmatched),
        "matchedReferenceUseCount": sum(int(row["count"]) for row in matched),
        "unmatchedReferenceUseCount": sum(int(row["count"]) for row in unmatched),
        "topMatched": matched[:limit],
        "topUnmatched": unmatched[:limit],
    }


def merge_counter_dicts(target: dict[str, Counter[str]], source: dict[str, Counter[str]]) -> None:
    for category, counter in source.items():
        target[category].update(counter)


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    focus_names = parse_csv(args.focus)
    unknown_focus = sorted(name for name in focus_names if name not in FOCUS_PATTERNS)
    focus_names = [name for name in focus_names if name in FOCUS_PATTERNS]

    lua_roots = [root.resolve() for root in (args.lua_root or list(DEFAULT_LUA_ROOTS))]
    table_roots = [root.resolve() for root in (args.table_root or list(DEFAULT_TABLE_ROOTS))]
    table_index, table_root_summaries = build_table_index(table_roots)
    modules: dict[str, dict[str, Any]] = {}
    root_summaries = []
    read_errors = []

    for root in lua_roots:
        files = lua_files(root)
        label = root_label(root)
        byte_total = 0
        for path in files:
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8-sig", errors="replace")
            except OSError as exc:
                read_errors.append({"path": repo_rel(path), "error": str(exc)})
                continue
            byte_total += len(raw)
            rel = module_key(path, root)
            sha = hashlib.sha256(raw).hexdigest()
            row = modules.setdefault(
                rel,
                {
                    "module": rel,
                    "roots": [],
                    "sha256ByRoot": {},
                    "byteLengthByRoot": {},
                    "text": text,
                    "canonicalPath": repo_rel(path),
                    "canonicalSha256": sha,
                },
            )
            row["roots"].append(label)
            row["sha256ByRoot"][label] = sha
            row["byteLengthByRoot"][label] = len(raw)
            if label == "Persistent" or "Persistent" not in row["roots"]:
                row["text"] = text
                row["canonicalPath"] = repo_rel(path)
                row["canonicalSha256"] = sha
        root_summaries.append(
            {
                "root": repo_rel(root),
                "label": label,
                "fileCount": len(files),
                "byteLength": byte_total,
            }
        )

    global_counts: dict[str, Counter[str]] = {name: Counter() for name, _pattern in REFERENCE_PATTERNS}
    global_examples: dict[str, list[dict[str, Any]]] = {name: [] for name, _pattern in REFERENCE_PATTERNS}
    focus_counters: dict[str, dict[str, Counter[str]]] = {
        name: {category: Counter() for category, _pattern in REFERENCE_PATTERNS}
        for name in focus_names
    }
    focus_module_counts: Counter[str] = Counter()
    focus_files: dict[str, list[dict[str, Any]]] = {name: [] for name in focus_names}
    module_findings = []

    for rel, row in sorted(modules.items()):
        text = str(row.get("text") or "")
        counts, examples = scan_references(text, rel=rel, example_limit=args.example_limit)
        merge_counter_dicts(global_counts, counts)
        for category, rows in examples.items():
            for item in rows:
                add_example(global_examples[category], item, args.example_limit)

        hits = focus_hits(text, rel, focus_names, args.focus_example_limit)
        if hits:
            for focus_name in hits:
                focus_module_counts[focus_name] += 1
                merge_counter_dicts(focus_counters[focus_name], counts)
                focus_files[focus_name].append(
                    {
                        "module": rel,
                        "path": row.get("canonicalPath"),
                        "roots": sorted(row.get("roots") or []),
                        "hitCount": hits[focus_name]["hitCount"],
                        "topTables": counter_rows(counts["tables"], 8),
                        "topEnums": counter_rows(counts["gEnums"], 8),
                        "topCsBeyond": counter_rows(counts["csBeyond"], 8),
                        "examples": hits[focus_name]["examples"],
                    }
                )
            module_findings.append(
                {
                    "module": rel,
                    "path": row.get("canonicalPath"),
                    "roots": sorted(row.get("roots") or []),
                    "focus": {name: data["hitCount"] for name, data in sorted(hits.items())},
                    "referenceCounts": {category: sum(counter.values()) for category, counter in counts.items()},
                    "topTables": counter_rows(counts["tables"], 8),
                    "topEnums": counter_rows(counts["gEnums"], 8),
                    "topCsBeyond": counter_rows(counts["csBeyond"], 8),
                }
            )

    module_findings.sort(
        key=lambda row: (
            -sum(int(value) for value in (row.get("focus") or {}).values()),
            str(row.get("module") or ""),
        )
    )

    focus_payload = {}
    for name in focus_names:
        top_focus_files = sorted(
            focus_files[name],
            key=lambda row: (-int(row.get("hitCount") or 0), str(row.get("module") or "")),
        )[: args.max_focus_files]
        focus_payload[name] = {
            "fileCount": focus_module_counts[name],
            "topFiles": top_focus_files,
            "topReferences": {
                category: counter_rows(counter, args.top_limit)
                for category, counter in focus_counters[name].items()
                if counter
            },
        }

    table_availability = table_reference_availability(global_counts["tables"], table_index, limit=args.top_limit)

    duplicate_modules = [
        {
            "module": rel,
            "roots": sorted(row.get("roots") or []),
            "sha256ByRoot": row.get("sha256ByRoot"),
            "sameContent": len(set((row.get("sha256ByRoot") or {}).values())) == 1,
        }
        for rel, row in sorted(modules.items())
        if len(row.get("roots") or []) > 1
    ]
    same_content_count = sum(1 for row in duplicate_modules if row["sameContent"])

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "luaRoots": [repo_rel(root) for root in lua_roots],
            "tableRoots": [repo_rel(root) for root in table_roots],
            "focus": focus_names,
            "unknownFocus": unknown_focus,
        },
        "settings": {
            "topLimit": args.top_limit,
            "exampleLimit": args.example_limit,
            "focusExampleLimit": args.focus_example_limit,
            "maxFocusFiles": args.max_focus_files,
            "maxModuleFindings": args.max_module_findings,
        },
        "summary": {
            "rootCount": len(lua_roots),
            "rootFileCount": sum(row["fileCount"] for row in root_summaries),
            "uniqueModuleCount": len(modules),
            "duplicateModuleCount": len(duplicate_modules),
            "duplicateSameContentCount": same_content_count,
            "readErrorCount": len(read_errors),
            "referenceCounts": {category: sum(counter.values()) for category, counter in global_counts.items()},
            "matchedTableReferenceCount": table_availability["matchedReferencedTableCount"],
            "unmatchedTableReferenceCount": table_availability["unmatchedReferencedTableCount"],
            "focusFileCounts": {name: focus_module_counts[name] for name in focus_names},
        },
        "rootSummaries": root_summaries,
        "tableRootSummaries": table_root_summaries,
        "tableReferenceAvailability": table_availability,
        "topReferences": {
            category: counter_rows(counter, args.top_limit)
            for category, counter in global_counts.items()
            if counter
        },
        "examples": global_examples,
        "focusAreas": focus_payload,
        "moduleFindings": module_findings[: args.max_module_findings],
        "duplicateModulesSample": duplicate_modules[: args.top_limit],
        "readErrors": read_errors[:100],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    settings = payload.get("settings") or {}
    top_limit = int(settings.get("topLimit") or 20)
    lines = [
        "# Lua Consumer Reference Audit",
        "",
        f"- Lua roots scanned: `{summary.get('rootCount')}`",
        f"- Lua files scanned across roots: `{summary.get('rootFileCount')}`",
        f"- unique Lua modules: `{summary.get('uniqueModuleCount')}`",
        f"- duplicate modules with identical bytes: `{summary.get('duplicateSameContentCount')}` / `{summary.get('duplicateModuleCount')}`",
        f"- read errors: `{summary.get('readErrorCount')}`",
        "",
        "## Focus Areas",
        "",
    ]

    focus_counts = summary.get("focusFileCounts") or {}
    for name, count in focus_counts.items():
        lines.append(f"- `{md_escape(name)}` files: `{count}`")

    table_availability = payload.get("tableReferenceAvailability") or {}
    lines.extend(["", "## Table Reference Availability", ""])
    lines.append(f"- Exported table files indexed: `{table_availability.get('availableTableCount')}`")
    lines.append(f"- Referenced Lua table names: `{table_availability.get('referencedTableCount')}`")
    lines.append(f"- Matched referenced table names: `{table_availability.get('matchedReferencedTableCount')}`")
    lines.append(f"- Unmatched referenced table names: `{table_availability.get('unmatchedReferencedTableCount')}`")
    unmatched = table_availability.get("topUnmatched") or []
    if unmatched:
        compact_unmatched = ", ".join(f"{item['value']} ({item['count']})" for item in unmatched[:10])
        lines.append(f"- Top unmatched: {md_escape(compact_unmatched)}")

    lines.extend(["", "## Top References", ""])
    for category, rows in (payload.get("topReferences") or {}).items():
        compact = ", ".join(f"{item['value']} ({item['count']})" for item in rows[:10])
        lines.append(f"- `{md_escape(category)}`: {md_escape(compact)}")

    for name, area in (payload.get("focusAreas") or {}).items():
        lines.extend(["", f"## Focus: {md_escape(name)}", ""])
        lines.append(f"- Files: `{area.get('fileCount')}`")
        refs = area.get("topReferences") or {}
        for category in ("tables", "gEnums", "csBeyond", "contentParam", "loadSprite", "videoHelper", "audioHelper"):
            rows = refs.get(category) or []
            if not rows:
                continue
            compact = ", ".join(f"{item['value']} ({item['count']})" for item in rows[:8])
            lines.append(f"- `{category}`: {md_escape(compact)}")
        lines.append("")
        lines.append("Top files:")
        for row in (area.get("topFiles") or [])[:top_limit]:
            focus_examples = "; ".join(
                f"{'path' if ex.get('line') is None else 'L' + str(ex.get('line'))} {ex.get('term')}"
                for ex in (row.get("examples") or [])[:3]
            )
            lines.append(
                f"- `{md_escape(row.get('module', ''))}` hits=`{row.get('hitCount')}` "
                f"roots=`{','.join(row.get('roots') or [])}`"
            )
            if focus_examples:
                lines.append(f"  - examples: {md_escape(focus_examples)}")

    lines.extend(["", "## Interpretation", ""])
    lines.append(
        "- Lua scripts provide concrete consumer evidence for table rows, enum branches, CS API calls, and UI/media helpers. "
        "This report does not alter WebUI export behavior; it identifies where source graph or Story/WebUI builders can add edges next."
    )
    lines.append(
        "- Persistent and StreamingAssets Lua modules are expected to duplicate heavily. Use unique module counts for semantic coverage and root file counts for VFS coverage."
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lua-root", type=Path, action="append", help="Lua root to scan; repeatable")
    parser.add_argument("--table-root", type=Path, action="append", help="Exported Table JSON root for Tables.* availability checks; repeatable")
    parser.add_argument("--focus", default="sns,remotecomm,dialog,mapmark,mission")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--top-limit", type=int, default=30)
    parser.add_argument("--example-limit", type=int, default=20)
    parser.add_argument("--focus-example-limit", type=int, default=4)
    parser.add_argument("--max-focus-files", type=int, default=30)
    parser.add_argument("--max-module-findings", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(f"Lua consumer reference audit: {args.json}")
    print(f"Lua consumer reference report: {args.markdown}")
    print(
        "uniqueModules="
        f"{summary['uniqueModuleCount']} "
        f"rootFiles={summary['rootFileCount']} "
        f"focusFiles={json.dumps(summary['focusFileCounts'], sort_keys=True)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
