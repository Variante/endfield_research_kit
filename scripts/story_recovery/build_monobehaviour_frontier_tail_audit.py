#!/usr/bin/env python3
"""Rank MonoBehaviour frontier tails against IL2CPP field evidence.

This report is intentionally read-only. It correlates the residual
MonoBehaviour frontier groups with focused IL2CPP metadata/body-target catalogs
so the next AnimeStudio parser work can start from repeated byte shapes and
known field order instead of broad guessing.

Output:

    reports/monobehaviour_frontier_tail_audit.json
    reports/monobehaviour_frontier_tail_audit.md
"""
from __future__ import annotations

import argparse
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

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

DEFAULT_FRONTIER_JSON = ROOT / "reports" / "monobehaviour_frontier_latest.json"
DEFAULT_METADATA_JSON = ROOT / "tmp" / "monobehaviour_frontier_runtime_metadata_targets.json"
DEFAULT_BODY_JSON = ROOT / "tmp" / "monobehaviour_frontier_body_targets_gameassembly.json"
DEFAULT_JSON = ROOT / "reports" / "monobehaviour_frontier_tail_audit.json"
DEFAULT_MD = ROOT / "reports" / "monobehaviour_frontier_tail_audit.md"

FOCUS_SIMPLE_NAMES = {
    "ProjectileTemplateData",
    "AbilityEntityTemplateData",
    "EnemyTemplateData",
    "CharacterTemplateData",
    "AbilitySystemData",
    "SkillDataBundle",
    "EffectActionCfg",
    "ProjectileComponentData",
}

HIGH_VALUE_SIMPLE_NAMES = {
    "AbilitySystemData",
    "SkillDataBundle",
    "EffectActionCfg",
    "ProjectileTemplateData",
    "AbilityEntityTemplateData",
    "EnemyTemplateData",
    "CharacterTemplateData",
}

ERROR_IMPOSSIBLE_STRING_RE = re.compile(
    r"ReadAlignedString requests (?P<requested>\d+) bytes at offset (?P<offset>0x[0-9a-f]+), but only (?P<remaining>\d+) bytes remain",
    re.IGNORECASE,
)


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def simple_name(full_name: str) -> str:
    value = str(full_name or "")
    if not value:
        return ""
    return value.rsplit(".", 1)[-1].split("+", 1)[0]


def normalize_error(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = ERROR_IMPOSSIBLE_STRING_RE.search(text)
    if match:
        return "ReadAlignedString:impossible-length"
    if ":" in text:
        return text.split(":", 1)[0][:80]
    return text[:80]


def first_values(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def load_metadata_types(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path, default={}) or {}
    by_name: dict[str, dict[str, Any]] = {}
    for section in ("matchedTypes", "focusTypes", "memberOnlyTypes"):
        for row in payload.get(section) or []:
            full_name = str(row.get("fullName") or "")
            if full_name and full_name not in by_name:
                by_name[full_name] = row
    return by_name


def load_body_targets(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = read_json(path, default={}) or {}
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("bodyTargets") or []:
        type_name = str(row.get("type") or "")
        if type_name:
            by_type[type_name].append(row)
    return dict(by_type)


def group_base(frontier: dict[str, Any], fallback: Path) -> Path:
    source_index = frontier.get("sourceIndex")
    if source_index:
        return (ROOT / source_index).parent
    return fallback


def group_path(base: Path, group_row: dict[str, Any]) -> Path:
    file_value = str(group_row.get("file") or "")
    path = Path(file_value)
    if path.is_absolute():
        return path
    return base / path


def metadata_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    fields = [str(field.get("name") or "") for field in row.get("fields") or [] if field.get("name")]
    methods = [str(method.get("name") or "") for method in row.get("methods") or [] if method.get("name")]
    matched_by = row.get("matchedBy") or {}
    return {
        "image": row.get("image"),
        "typeIndex": row.get("index"),
        "token": row.get("token"),
        "fieldCount": len(fields),
        "methodCount": len(methods),
        "fields": fields[:80],
        "methods": methods[:80],
        "matchedBy": matched_by,
    }


def body_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append(
            {
                "method": row.get("method"),
                "methodIndex": row.get("methodIndex"),
                "token": row.get("token"),
                "mappingStatus": row.get("mappingStatus"),
                "methodPointerVa": row.get("methodPointerVa"),
                "directCallCount": len(row.get("directCalls") or []),
                "unresolvedDirectCallCount": row.get("unresolvedDirectCallCount"),
            }
        )
    return out


def sample_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": entry.get("name"),
        "path": entry.get("p"),
        "schema": entry.get("schema"),
        "status": entry.get("status"),
        "registry": entry.get("registry"),
        "rawSize": entry.get("rawSize"),
        "refCount": entry.get("refCount"),
        "flags": entry.get("flags") or {},
        "errorKind": normalize_error(entry.get("error")),
        "error": entry.get("error"),
    }


def audit_group(
    group_row: dict[str, Any],
    path: Path,
    metadata_by_name: dict[str, dict[str, Any]],
    body_targets_by_type: dict[str, list[dict[str, Any]]],
    *,
    sample_limit: int,
) -> dict[str, Any]:
    payload = read_json(path, default={}) or {}
    entries = payload.get("entries") or []

    class_counts: Counter[str] = Counter()
    layout_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    registry_counts: Counter[str] = Counter()
    raw_size_counts: Counter[str] = Counter()
    sample_entries: list[dict[str, Any]] = []

    for entry in entries:
        class_counts.update(str(value) for value in entry.get("classes") or [] if value)
        layout_counts.update(str(value) for value in entry.get("layouts") or [] if value)
        registry = str(entry.get("registry") or "")
        if registry:
            registry_counts[registry] += 1
        error_kind = normalize_error(entry.get("error"))
        if error_kind:
            error_counts[error_kind] += 1
        for key, value in (entry.get("flags") or {}).items():
            try:
                flag_counts[str(key)] += int(value)
            except (TypeError, ValueError):
                continue
        raw_size = entry.get("rawSize")
        if raw_size is not None:
            raw_size_counts[str(raw_size)] += 1
        if len(sample_entries) < sample_limit:
            sample_entries.append(sample_entry(entry))

    focus_layouts = []
    metadata_matches = []
    body_matches = []
    for layout, count in layout_counts.most_common():
        simple = simple_name(layout)
        if simple not in FOCUS_SIMPLE_NAMES and layout not in metadata_by_name:
            continue
        meta = metadata_summary(metadata_by_name.get(layout))
        bodies = body_summary(body_targets_by_type.get(layout, []))
        focus_layouts.append(
            {
                "layout": layout,
                "simpleName": simple,
                "count": count,
                "metadataFieldCount": (meta or {}).get("fieldCount", 0),
                "bodyTargetCount": len(bodies),
            }
        )
        if meta:
            metadata_matches.append({"layout": layout, **meta})
        if bodies:
            body_matches.append({"layout": layout, "bodyTargets": bodies})

    residual_files = int(group_row.get("residualFiles") or group_row.get("files") or len(entries))
    partial_refs = flag_counts.get("partial", 0)
    error_refs = sum(error_counts.values())
    metadata_field_total = sum(int(row.get("metadataFieldCount") or 0) for row in focus_layouts)
    body_target_total = sum(int(row.get("bodyTargetCount") or 0) for row in focus_layouts)
    repeatability_bonus = max((count for _size, count in raw_size_counts.items()), default=0)
    high_value_bonus = sum(
        row["count"]
        for row in focus_layouts
        if row["simpleName"] in HIGH_VALUE_SIMPLE_NAMES
    )
    priority_score = (
        residual_files * 10
        + partial_refs
        + error_refs * 2
        + metadata_field_total
        + body_target_total * 25
        + repeatability_bonus
        + high_value_bonus
    )

    top_error = error_counts.most_common(1)[0][0] if error_counts else ""
    recommendation = "metadata-first tail audit"
    if top_error == "ReadAlignedString:impossible-length":
        recommendation = "find pre-string binary block boundary before adding string reads"
    if body_target_total:
        recommendation += "; inspect mapped method body evidence"

    return {
        "id": group_row.get("id"),
        "path": repo_rel(path),
        "exists": path.exists(),
        "residualFiles": residual_files,
        "entryCount": len(entries),
        "schemas": group_row.get("schemas") or {},
        "domains": group_row.get("domains") or {},
        "registries": group_row.get("registries") or {},
        "classes": first_values(class_counts, 12),
        "layouts": first_values(layout_counts, 16),
        "focusLayouts": focus_layouts,
        "metadataMatches": metadata_matches[:12],
        "bodyMatches": body_matches[:12],
        "flags": dict(flag_counts),
        "errorKinds": first_values(error_counts, 8),
        "rawSizes": first_values(raw_size_counts, 8),
        "sampleEntries": sample_entries,
        "priorityScore": priority_score,
        "recommendation": recommendation,
    }


def aggregate_types(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for group in groups:
        for layout in group.get("focusLayouts") or []:
            type_name = layout["layout"]
            row = rows.setdefault(
                type_name,
                {
                    "layout": type_name,
                    "simpleName": layout.get("simpleName"),
                    "groupCount": 0,
                    "residualFiles": 0,
                    "entryCount": 0,
                    "layoutRefs": 0,
                    "metadataFieldCount": layout.get("metadataFieldCount") or 0,
                    "bodyTargetCount": layout.get("bodyTargetCount") or 0,
                    "groups": [],
                    "errorKinds": Counter(),
                    "schemas": Counter(),
                },
            )
            row["groupCount"] += 1
            row["residualFiles"] += int(group.get("residualFiles") or 0)
            row["entryCount"] += int(group.get("entryCount") or 0)
            row["layoutRefs"] += int(layout.get("count") or 0)
            row["groups"].append({"id": group.get("id"), "residualFiles": group.get("residualFiles")})
            row["errorKinds"].update({item["value"]: item["count"] for item in group.get("errorKinds") or []})
            row["schemas"].update({str(k): int(v) for k, v in (group.get("schemas") or {}).items()})

    out = []
    for row in rows.values():
        body_target_count = int(row.get("bodyTargetCount") or 0)
        field_count = int(row.get("metadataFieldCount") or 0)
        score = (
            int(row["residualFiles"]) * 10
            + int(row["layoutRefs"]) * 2
            + field_count
            + body_target_count * 50
            + (200 if row.get("simpleName") in {"AbilitySystemData", "SkillDataBundle"} else 0)
        )
        recommendation = "rank repeated payload offsets against metadata field order"
        if row.get("simpleName") in {"AbilitySystemData", "SkillDataBundle"}:
            recommendation = "highest shared tail; audit byte blocks before semantic parser changes"
        elif body_target_count:
            recommendation = "use mapped method body as supporting evidence"
        out.append(
            {
                "layout": row["layout"],
                "simpleName": row.get("simpleName"),
                "priorityScore": score,
                "groupCount": row["groupCount"],
                "residualFiles": row["residualFiles"],
                "entryCount": row["entryCount"],
                "layoutRefs": row["layoutRefs"],
                "metadataFieldCount": field_count,
                "bodyTargetCount": body_target_count,
                "topSchemas": first_values(row["schemas"], 6),
                "topErrorKinds": first_values(row["errorKinds"], 4),
                "groups": row["groups"][:12],
                "recommendation": recommendation,
            }
        )
    return sorted(out, key=lambda item: (-int(item["priorityScore"]), str(item["layout"])))


def build_audit(
    *,
    frontier_json: Path,
    metadata_json: Path,
    body_json: Path,
    sample_limit: int,
) -> dict[str, Any]:
    frontier = read_json(frontier_json, default={}) or {}
    metadata_by_name = load_metadata_types(metadata_json)
    body_targets_by_type = load_body_targets(body_json)
    base = group_base(frontier, frontier_json.parent)

    groups = []
    for group_row in frontier.get("residualGroups") or frontier.get("topResidualGroups") or []:
        path = group_path(base, group_row)
        groups.append(
            audit_group(
                group_row,
                path,
                metadata_by_name,
                body_targets_by_type,
                sample_limit=sample_limit,
            )
        )

    groups.sort(key=lambda item: (-int(item.get("priorityScore") or 0), str(item.get("id") or "")))
    type_rows = aggregate_types(groups)

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "frontierJson": repo_rel(frontier_json),
            "metadataJson": repo_rel(metadata_json),
            "bodyJson": repo_rel(body_json),
            "groupBase": repo_rel(base),
        },
        "summary": {
            "frontierResidualFiles": (frontier.get("frontier") or {}).get("residualFiles"),
            "frontierResidualGroups": (frontier.get("frontier") or {}).get("groupCount"),
            "auditedGroupCount": len(groups),
            "rankedTypeCount": len(type_rows),
            "metadataTypeCount": len(metadata_by_name),
            "bodyTargetTypeCount": len(body_targets_by_type),
        },
        "rankedTypes": type_rows,
        "rankedGroups": groups,
    }


def render_markdown(audit: dict[str, Any], *, top_n: int) -> str:
    lines = [
        "# MonoBehaviour Frontier Tail Audit",
        "",
        "## Summary",
        "",
    ]
    summary = audit.get("summary") or {}
    inputs = audit.get("inputs") or {}
    lines.extend(
        [
            f"- Frontier residual files: `{summary.get('frontierResidualFiles')}`",
            f"- Frontier residual groups: `{summary.get('frontierResidualGroups')}`",
            f"- Audited groups: `{summary.get('auditedGroupCount')}`",
            f"- Ranked focus types: `{summary.get('rankedTypeCount')}`",
            f"- Metadata input: `{md_escape(inputs.get('metadataJson'))}`",
            f"- Body-map input: `{md_escape(inputs.get('bodyJson'))}`",
            "",
            "## Top Type Targets",
            "",
            "| Type | Score | Residual files | Groups | Refs | Metadata fields | Body targets | Top errors | Recommendation |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in (audit.get("rankedTypes") or [])[:top_n]:
        errors = ", ".join(f"{item['value']} ({item['count']})" for item in row.get("topErrorKinds") or []) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{md_escape(row.get('layout'))}`",
                    str(row.get("priorityScore")),
                    str(row.get("residualFiles")),
                    str(row.get("groupCount")),
                    str(row.get("layoutRefs")),
                    str(row.get("metadataFieldCount")),
                    str(row.get("bodyTargetCount")),
                    md_escape(errors),
                    md_escape(row.get("recommendation")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Top Residual Groups",
            "",
            "| Group | Score | Residual files | Entries | Focus layouts | Top errors | Recommendation |",
            "| --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for group in (audit.get("rankedGroups") or [])[:top_n]:
        layouts = ", ".join(f"`{item['simpleName']}` ({item['count']})" for item in group.get("focusLayouts") or []) or "-"
        errors = ", ".join(f"{item['value']} ({item['count']})" for item in group.get("errorKinds") or []) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{md_escape(group.get('id'))}`",
                    str(group.get("priorityScore")),
                    str(group.get("residualFiles")),
                    str(group.get("entryCount")),
                    md_escape(layouts),
                    md_escape(errors),
                    md_escape(group.get("recommendation")),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Metadata Fields For Top Types", ""])
    metadata_by_layout = {}
    for group in audit.get("rankedGroups") or []:
        for meta in group.get("metadataMatches") or []:
            metadata_by_layout.setdefault(meta.get("layout"), meta)
    for row in (audit.get("rankedTypes") or [])[: min(top_n, 12)]:
        layout = row.get("layout")
        meta = metadata_by_layout.get(layout)
        if not meta:
            continue
        fields = ", ".join(f"`{md_escape(field)}`" for field in (meta.get("fields") or [])[:30]) or "-"
        lines.extend(
            [
                f"### `{md_escape(layout)}`",
                "",
                f"- Fields shown: {fields}",
                f"- Methods: {', '.join(f'`{md_escape(method)}`' for method in (meta.get('methods') or [])[:20]) or '-'}",
                "",
            ]
        )

    lines.append("## Next Step")
    lines.append("")
    lines.append(
        "Start with `AbilitySystemData` and `SkillDataBundle`: they recur across the largest Projectile, AbilityEntity, Enemy, and Character residual groups. The repeated `ReadAlignedString:impossible-length` failures mean the next parser work should first locate binary block boundaries before adding or reordering string reads."
    )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontier-json", type=Path, default=DEFAULT_FRONTIER_JSON)
    parser.add_argument("--metadata-json", type=Path, default=DEFAULT_METADATA_JSON)
    parser.add_argument("--body-json", type=Path, default=DEFAULT_BODY_JSON)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--sample-limit", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(
        frontier_json=args.frontier_json,
        metadata_json=args.metadata_json,
        body_json=args.body_json,
        sample_limit=max(0, args.sample_limit),
    )
    write_report_json(args.json, audit)
    write_text_if_changed(args.markdown, render_markdown(audit, top_n=max(1, args.top_n)))
    print(f"wrote JSON: {repo_rel(args.json)}")
    print(f"wrote Markdown: {repo_rel(args.markdown)}")


if __name__ == "__main__":
    main()
