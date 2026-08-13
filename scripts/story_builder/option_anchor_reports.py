from __future__ import annotations

from pathlib import Path

if __package__ == "story_builder":
    from common import read_json, write_report_json
elif __package__ == "scripts.story_builder":
    from ..common import read_json, write_report_json
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.story_builder.option_anchor_reports")


def inferred_option_anchor_row(payload: dict, fallback_key: str = "") -> dict | None:
    """Build one audit row for a dialog using inferred option placement."""
    if not isinstance(payload, dict) or str(payload.get("kind") or "") != "dlg":
        return None
    warning = next(
        (
            item
            for item in (payload.get("warnings") or [])
            if isinstance(item, dict) and item.get("code") == "inferredOptionLayout"
        ),
        None,
    )
    if not isinstance(warning, dict):
        return None
    inferred = [
        detail
        for detail in (warning.get("groupDetails") or [])
        if isinstance(detail, dict)
        and detail.get("status") == "fallbackAfter"
        and detail.get("inferredAnchorMode")
    ]
    if not inferred:
        return None
    return {
        "key": payload.get("key") or fallback_key,
        "mission": payload.get("mission") or "",
        "scene": payload.get("scene"),
        "lineCount": len(payload.get("lines") or []),
        "groupCount": len(payload.get("optionGroups") or []),
        "inferredGroups": [
            {
                "g": detail.get("group"),
                "after": detail.get("after"),
                "mode": detail.get("inferredAnchorMode"),
                "optionIds": detail.get("optionIds") or [],
            }
            for detail in inferred
        ],
        "reason": warning.get("reason") or "",
    }


def collect_inferred_option_anchor_rows(conv_dir: Path) -> list[dict]:
    """Collect inferred-option rows from generated dialog conversations."""
    rows: list[dict] = []
    for path in sorted(conv_dir.glob("*.json")):
        row = inferred_option_anchor_row(read_json(path, {}), path.stem)
        if row is not None:
            rows.append(row)
    return _sorted_rows(rows)


def _sorted_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("mission") or "",
            row.get("scene") or 0,
            row.get("key") or "",
        ),
    )


def write_inferred_option_anchors_report(
    reports_dir: Path,
    language: str,
    conv_dir: Path,
    *,
    rows: list[dict] | None = None,
) -> dict:
    rows = (
        collect_inferred_option_anchor_rows(conv_dir)
        if rows is None
        else _sorted_rows(list(rows))
    )

    by_mode: dict[str, int] = {}
    for row in rows:
        for group in row.get("inferredGroups") or []:
            mode = str(group.get("mode") or "")
            if mode:
                by_mode[mode] = by_mode.get(mode, 0) + 1

    summary = {
        "language": language,
        "totalScenes": len(rows),
        "totalInferredGroups": sum(
            len(row.get("inferredGroups") or []) for row in rows
        ),
        "groupsByMode": dict(sorted(by_mode.items())),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_json = reports_dir / f"inferred_option_anchors_{language}.json"
    out_md = reports_dir / f"inferred_option_anchors_{language}.md"
    write_report_json(out_json, {"summary": summary, "scenes": rows})

    lines = [
        f"# Inferred option anchors — {language}",
        "",
        f"Scenes with at least one option group placed via fallback: **{summary['totalScenes']}**.",
        f"Total inferred groups: **{summary['totalInferredGroups']}**.",
        "",
        "## Counts by inference mode",
        "",
    ]
    lines.extend(
        f"- `{mode}`: {count}" for mode, count in summary["groupsByMode"].items()
    )
    lines.extend(
        [
            "",
            "## Scenes",
            "",
            "| Scene | Lines | Groups | Inferred | Modes | Reason |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in rows:
        modes = sorted(
            {str(group.get("mode") or "") for group in row.get("inferredGroups") or []}
        )
        lines.append(
            f"| `{row.get('key', '')}` "
            f"| {row.get('lineCount', 0)} "
            f"| {row.get('groupCount', 0)} "
            f"| {len(row.get('inferredGroups') or [])} "
            f"| {', '.join(modes)} "
            f"| {row.get('reason') or ''} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"  inferred-anchors report: {out_md}")
    print(f"  inferred-anchors data:   {out_json}")
    print(
        f"  inferred-anchor scenes:  {summary['totalScenes']} "
        f"({summary['totalInferredGroups']} groups)"
    )
    return {"summary": summary, "markdown": out_md, "json": out_json}
