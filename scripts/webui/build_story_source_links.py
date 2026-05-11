#!/usr/bin/env python3
"""Recover story source references from mission and level-script JSON.

The WebUI story builder already reconstructs the readable conversations from
tables and AnimeStudio assets. This helper builds the inverse index: where the
game data references each story scene id.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "export_full"
DATA_JSON_DIR = EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json"
DEFAULT_OUTPUT = EXPORT_ROOT / "recovered" / "story_source_links.json"
DEFAULT_REPORT_JSON = ROOT / "reports" / "story_source_links.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "story_source_links.md"

DEFAULT_SCAN_ROOTS = (
    DATA_JSON_DIR / "MissionRuntimeAsset",
    DATA_JSON_DIR / "LevelScriptData",
    DATA_JSON_DIR / "LevelScriptTemplateData",
)

ID_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("dialog", re.compile(r"\bdlg_[A-Za-z0-9_]{2,120}")),
    ("radio", re.compile(r"\bradio_[A-Za-z0-9_]{2,120}")),
    ("sns", re.compile(r"\bsns_[A-Za-z0-9_]{2,120}")),
    ("snsOption", re.compile(r"\boption_sns_[A-Za-z0-9_]{2,120}")),
    ("cutscene", re.compile(r"\b(?:cutscene|f_cutscene|m_cutscene|fm_cutscene|cs_video)_[A-Za-z0-9_]{2,120}")),
    ("remotecomm", re.compile(r"\bremotecomm_[A-Za-z0-9_]{2,120}")),
    ("readingPopup", re.compile(r"\brp_[A-Za-z0-9_]{2,120}")),
)

CONTEXT_FIELDS = (
    "questId",
    "flowIndex",
    "actionId",
    "actionType",
    "actionName",
    "clientActionId",
    "conditionId",
    "conditionType",
    "cutsceneName",
    "dialogId",
    "id",
    "levelId",
    "levelScriptId",
    "missionId",
    "name",
    "nodeId",
    "radioId",
    "snsDialogId",
    "type",
)


def slash(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_dialog_id(raw: str) -> str:
    parts = raw.removeprefix("dlg_").split("_")
    if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 3:
        parts = parts[:-1]
        if len(parts) >= 3 and parts[-1].isdigit():
            parts = parts[:-1]
    return "dlg_" + "_".join(parts)


def normalize_radio_id(raw: str) -> str:
    parts = raw.removeprefix("radio_").split("_")
    if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 3:
        parts = parts[:-1]
    return "radio_" + "_".join(parts)


def normalize_remotecomm_id(raw: str) -> str:
    parts = raw.removeprefix("remotecomm_").split("_")
    if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 3:
        parts = parts[:-1]
    return "remotecomm_" + "_".join(parts)


def normalize_sns_id(raw: str) -> str:
    value = raw.removeprefix("option_")
    match = re.match(r"^(sns_[A-Za-z0-9]+_\d+)", value)
    if match:
        return match.group(1)
    return value


def normalize_cutscene_id(raw: str) -> str:
    value = raw
    for prefix in ("f_", "m_", "fm_"):
        if value.startswith(prefix + "cutscene_"):
            value = value[len(prefix):]
            break
    if value.startswith("cs_video_"):
        value = "cutscene_" + value[len("cs_video_"):]
    return value


def normalize_reference(kind: str, raw: str) -> tuple[str, str]:
    if kind == "dialog":
        return "dlg", normalize_dialog_id(raw)
    if kind == "radio":
        return "radio", normalize_radio_id(raw)
    if kind in {"sns", "snsOption"}:
        return "sns", normalize_sns_id(raw)
    if kind == "cutscene":
        return "cutscene", normalize_cutscene_id(raw)
    if kind == "remotecomm":
        return "remotecomm", normalize_remotecomm_id(raw)
    if kind == "readingPopup":
        return "reading", raw
    return kind, raw


def classify_source(path: Path, root: Path) -> dict[str, str]:
    rel_parts = path.relative_to(root).parts
    source = {
        "source": root.name,
        "fileStem": path.stem,
    }
    if root.name == "MissionRuntimeAsset":
        source["source"] = "missionRuntime"
        if not path.stem.endswith("_meta"):
            source["mission"] = path.stem
    elif root.name == "LevelScriptData":
        source["source"] = "levelScript"
        if rel_parts:
            source["levelId"] = rel_parts[0]
        source["scriptId"] = path.stem
    elif root.name == "LevelScriptTemplateData":
        source["source"] = "levelScriptTemplate"
        if rel_parts:
            source["templateGroup"] = rel_parts[0] if len(rel_parts) > 1 else ""
        source["templateId"] = path.stem
    return source


def json_path(parts: tuple[str, ...]) -> str:
    if not parts:
        return "$"
    out = "$"
    for part in parts:
        if part.startswith("["):
            out += part
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
            out += "." + part
        else:
            out += "[" + json.dumps(part, ensure_ascii=False) + "]"
    return out


def compact_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return f"list[{len(value)}]"
    if isinstance(value, dict):
        return f"dict[{len(value)}]"
    return str(value)


def nearest_context(stack: tuple[tuple[str, Any], ...], field_name: str, text: str) -> dict:
    context: dict[str, Any] = {
        "field": field_name,
    }
    for _label, node in reversed(stack):
        if not isinstance(node, dict):
            continue
        picked = {
            key: compact_value(node.get(key))
            for key in CONTEXT_FIELDS
            if key in node and node.get(key) not in ("", None, [], {})
        }
        if picked:
            context["owner"] = picked
            break
    preview = re.sub(r"\s+", " ", text).strip()
    if len(preview) > 180:
        preview = preview[:177] + "..."
    if preview:
        context["text"] = preview
    return context


def iter_string_nodes(
    node: Any,
    path_parts: tuple[str, ...] = (),
    stack: tuple[tuple[str, Any], ...] = (),
):
    if isinstance(node, dict):
        next_stack = stack + ((path_parts[-1] if path_parts else "$", node),)
        for key, value in node.items():
            yield from iter_string_nodes(value, path_parts + (str(key),), next_stack)
    elif isinstance(node, list):
        next_stack = stack + ((path_parts[-1] if path_parts else "$", node),)
        for index, value in enumerate(node):
            yield from iter_string_nodes(value, path_parts + (f"[{index}]",), next_stack)
    elif isinstance(node, str):
        yield path_parts, stack, node


def iter_source_files(roots: list[Path]) -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            files.append((root, path))
    return files


def build_source_links(
    roots: list[Path] | None = None,
    *,
    output: Path = DEFAULT_OUTPUT,
    report_json: Path = DEFAULT_REPORT_JSON,
    report_md: Path = DEFAULT_REPORT_MD,
) -> dict:
    roots = roots or list(DEFAULT_SCAN_ROOTS)
    files = iter_source_files(roots)
    links: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str, str, str]] = set()
    files_with_matches: set[str] = set()
    stats_by_kind: Counter[str] = Counter()
    stats_by_source: Counter[str] = Counter()
    stats_by_root: Counter[str] = Counter()

    for root, path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        rel_file = slash(path)
        source_info = classify_source(path, root)
        matched_file = False
        for path_parts, stack, text in iter_string_nodes(payload):
            matches: list[tuple[str, str, str, str]] = []
            for pattern_kind, pattern in ID_PATTERNS:
                for match in pattern.finditer(text):
                    raw = match.group(0)
                    key_kind, key = normalize_reference(pattern_kind, raw)
                    matches.append((pattern_kind, raw, key_kind, key))
            if not matches:
                continue
            field_name = path_parts[-1] if path_parts else ""
            path_text = json_path(path_parts)
            context = nearest_context(stack, field_name, text)
            for pattern_kind, raw, key_kind, key in matches:
                dedupe_key = (key, raw, rel_file, path_text)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                matched_file = True
                stats_by_kind[key_kind] += 1
                stats_by_source[source_info["source"]] += 1
                stats_by_root[root.name] += 1
                record = {
                    "raw": raw,
                    "kind": key_kind,
                    "matchKind": pattern_kind,
                    "source": source_info["source"],
                    "file": rel_file,
                    "path": path_text,
                    "context": context,
                }
                for optional in ("mission", "levelId", "scriptId", "templateGroup", "templateId"):
                    if source_info.get(optional):
                        record[optional] = source_info[optional]
                links[key].append(record)
        if matched_file:
            files_with_matches.add(rel_file)

    sorted_links = {
        key: sorted(
            rows,
            key=lambda row: (
                row.get("source") or "",
                row.get("mission") or "",
                row.get("levelId") or "",
                row.get("file") or "",
                row.get("path") or "",
                row.get("raw") or "",
            ),
        )
        for key, rows in sorted(links.items())
    }
    summary = {
        "filesScanned": len(files),
        "filesWithMatches": len(files_with_matches),
        "keys": len(sorted_links),
        "references": sum(len(rows) for rows in sorted_links.values()),
        "byKind": dict(sorted(stats_by_kind.items())),
        "bySource": dict(sorted(stats_by_source.items())),
        "byRoot": dict(sorted(stats_by_root.items())),
    }
    output_payload = {
        "generated": int(time.time()),
        "roots": [slash(root) for root in roots if root.exists()],
        "summary": summary,
        "links": sorted_links,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report_payload = {
        "generated": output_payload["generated"],
        "output": slash(output),
        "summary": summary,
        "topKeys": [
            {"key": key, "references": len(rows), "kind": rows[0].get("kind") if rows else ""}
            for key, rows in sorted(sorted_links.items(), key=lambda item: (-len(item[1]), item[0]))[:80]
        ],
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(render_markdown_report(report_payload), encoding="utf-8")
    return output_payload


def render_markdown_report(report: dict) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Story Source Links",
        "",
        f"Output: `{report.get('output', '')}`",
        "",
        "## Summary",
        "",
        f"- Files scanned: `{summary.get('filesScanned', 0)}`",
        f"- Files with matches: `{summary.get('filesWithMatches', 0)}`",
        f"- Story keys: `{summary.get('keys', 0)}`",
        f"- References: `{summary.get('references', 0)}`",
        "",
        "## By Kind",
        "",
    ]
    for key, count in (summary.get("byKind") or {}).items():
        lines.append(f"- `{key}`: `{count}`")
    lines.extend(["", "## By Source", ""])
    for key, count in (summary.get("bySource") or {}).items():
        lines.append(f"- `{key}`: `{count}`")
    lines.extend(["", "## Top Referenced Keys", ""])
    for row in report.get("topKeys") or []:
        lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('references')}` refs)")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        default=[],
        help="Additional or replacement scan root. If provided, only these roots are scanned.",
    )
    parser.add_argument(
        "--include-level-data",
        action="store_true",
        help="Also scan Data/Json/LevelData. This is noisier and disabled by default.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots = list(args.root) if args.root else list(DEFAULT_SCAN_ROOTS)
    if args.include_level_data:
        roots.append(DATA_JSON_DIR / "LevelData")
    payload = build_source_links(
        roots,
        output=args.output,
        report_json=args.report_json,
        report_md=args.report_md,
    )
    summary = payload["summary"]
    print(
        "Story source links: "
        f"{summary['references']} refs, {summary['keys']} keys, "
        f"{summary['filesWithMatches']}/{summary['filesScanned']} files with matches"
    )
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report_json}")
    print(f"Wrote {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
