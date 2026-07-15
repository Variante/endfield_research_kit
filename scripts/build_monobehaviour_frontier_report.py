#!/usr/bin/env python3
"""Summarize the current MonoBehaviour decoded-index recovery frontier."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "webui" / "data" / "decoded" / "index.json"
DEFAULT_JSON = ROOT / "reports" / "assets" / "diagnostics" / "monobehaviour_frontier_latest.json"
DEFAULT_MD = ROOT / "reports" / "assets" / "diagnostics" / "monobehaviour_frontier_latest.md"
LIST_LIMIT = 12


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX, help="Decoded index JSON to summarize.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON, help="Output JSON report path.")
    parser.add_argument("--md", type=Path, default=DEFAULT_MD, help="Output Markdown report path.")
    parser.add_argument("--top", type=int, default=40, help="Top residual groups to include in the Markdown table.")
    return parser.parse_args(argv)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix().replace("\\", "/")


def residual_count(group: dict[str, Any]) -> int:
    statuses = group.get("statuses") or {}
    return sum(int(count or 0) for status, count in statuses.items() if status != "decoded")


def add_counts(target: Counter[str], values: dict[str, Any], weight: int = 1) -> None:
    for key, count in (values or {}).items():
        if key:
            target[str(key)] += int(count or 0) if weight == 1 else weight


def top_dict(counter: Counter[str], limit: int = LIST_LIMIT) -> dict[str, int]:
    return dict(counter.most_common(limit))


def compact_counter(values: dict[str, Any], limit: int = LIST_LIMIT) -> dict[str, int]:
    counter = Counter({str(key): int(value or 0) for key, value in (values or {}).items() if key})
    return top_dict(counter, limit)


def group_record(group: dict[str, Any]) -> dict[str, Any]:
    residual = residual_count(group)
    return {
        "id": group.get("id"),
        "file": group.get("file"),
        "files": group.get("files"),
        "bytes": group.get("bytes"),
        "residualFiles": residual,
        "statuses": group.get("statuses") or {},
        "sources": group.get("sources") or {},
        "domains": group.get("domains") or {},
        "schemas": group.get("schemas") or {},
        "schemaGroups": group.get("schemaGroups") or {},
        "schemaKinds": group.get("schemaKinds") or {},
        "fieldSets": group.get("fieldSets") or {},
        "prefixes": compact_counter(group.get("prefixes") or {}),
        "families": compact_counter(group.get("families") or {}),
        "meanings": compact_counter(group.get("meanings") or {}),
        "tags": compact_counter(group.get("tags") or {}),
        "registries": group.get("registries") or {},
        "classes": compact_counter(group.get("classes") or {}),
        "layouts": compact_counter(group.get("layouts") or {}),
        "flags": group.get("flags") or {},
    }


def build_report(index_path: Path, top_limit: int) -> dict[str, Any]:
    payload = read_json(index_path)
    groups = payload.get("groups") or []
    residual_groups = [group for group in groups if residual_count(group)]
    residual_groups.sort(key=lambda group: (-residual_count(group), str(group.get("id") or "")))

    status_counts = Counter()
    residual_status_counts = Counter()
    schema_counts = Counter()
    domain_counts = Counter()
    registry_counts = Counter()
    source_counts = Counter()
    field_set_counts = Counter()
    family_counts = Counter()
    tag_counts = Counter()

    for group in groups:
        add_counts(status_counts, group.get("statuses") or {})
    for group in residual_groups:
        residual = residual_count(group)
        for status, count in (group.get("statuses") or {}).items():
            if status != "decoded":
                residual_status_counts[str(status)] += int(count or 0)
        add_counts(schema_counts, group.get("schemas") or {}, residual)
        add_counts(domain_counts, group.get("domains") or {}, residual)
        add_counts(registry_counts, group.get("registries") or {}, residual)
        add_counts(source_counts, group.get("sources") or {}, residual)
        add_counts(field_set_counts, group.get("fieldSets") or {}, residual)
        add_counts(family_counts, group.get("families") or {}, residual)
        add_counts(tag_counts, group.get("tags") or {}, residual)

    return {
        "generated": int(time.time()),
        "sourceIndex": rel(index_path),
        "sourceIndexGenerated": payload.get("generated"),
        "sourceRoot": payload.get("sourceRoot"),
        "exportRoot": payload.get("exportRoot"),
        "indexScope": payload.get("indexScope"),
        "sources": payload.get("sources") or [],
        "types": payload.get("types") or [],
        "counts": payload.get("counts") or {},
        "frontier": {
            "groupCount": len(residual_groups),
            "residualFiles": sum(residual_count(group) for group in residual_groups),
            "statusCounts": dict(sorted(residual_status_counts.items())),
            "schemaCounts": top_dict(schema_counts, 30),
            "domainCounts": top_dict(domain_counts, 30),
            "registryCounts": top_dict(registry_counts, 30),
            "sourceCounts": top_dict(source_counts, 30),
            "fieldSetCounts": top_dict(field_set_counts, 30),
            "familyCounts": top_dict(family_counts, 30),
            "tagCounts": top_dict(tag_counts, 30),
        },
        "groupCount": len(groups),
        "allStatusCounts": dict(sorted(status_counts.items())),
        "residualGroups": [group_record(group) for group in residual_groups],
        "topResidualGroups": [group_record(group) for group in residual_groups[:top_limit]],
    }


def write_markdown(path: Path, report: dict[str, Any], top_limit: int) -> None:
    frontier = report.get("frontier") or {}
    counts = report.get("counts") or {}
    lines = [
        "# MonoBehaviour Recovery Frontier",
        "",
        f"- Source index: `{report.get('sourceIndex')}`",
        f"- Export root: `{report.get('exportRoot')}`",
        f"- Total files: `{counts.get('files', 0)}`",
        f"- Total groups: `{report.get('groupCount', 0)}`",
        f"- Residual files: `{frontier.get('residualFiles', 0)}`",
        f"- Residual groups: `{frontier.get('groupCount', 0)}`",
        "",
        "## Status Counts",
        "",
    ]
    for key, value in (report.get("allStatusCounts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Frontier Status Counts", ""])
    for key, value in (frontier.get("statusCounts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    for title, key in (
        ("Schemas", "schemaCounts"),
        ("Domains", "domainCounts"),
        ("Registries", "registryCounts"),
        ("Field Sets", "fieldSetCounts"),
    ):
        lines.extend(["", f"## {title}", ""])
        for name, value in (frontier.get(key) or {}).items():
            lines.append(f"- `{name}`: `{value}`")
    lines.extend([
        "",
        f"## Top {top_limit} Residual Groups",
        "",
        "| Group | Residual | Statuses | Schemas | Domains | Registries |",
        "| --- | ---: | --- | --- | --- | --- |",
    ])
    for group in report.get("topResidualGroups") or []:
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                group.get("id"),
                group.get("residualFiles"),
                json.dumps(group.get("statuses") or {}, ensure_ascii=False, sort_keys=True),
                ", ".join(group.get("schemas") or {}),
                ", ".join(group.get("domains") or {}),
                ", ".join(group.get("registries") or {}),
            )
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.index, args.top)
    write_json(args.json, report)
    write_markdown(args.md, report, args.top)
    frontier = report["frontier"]
    print(
        "MonoBehaviour frontier:",
        f"{frontier['residualFiles']} residual file(s)",
        f"across {frontier['groupCount']} group(s)",
    )
    print(f"Wrote {rel(args.json)}")
    print(f"Wrote {rel(args.md)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
