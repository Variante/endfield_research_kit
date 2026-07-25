from __future__ import annotations

import sys
from pathlib import Path

from common import ROOT, read_json, write_report_json

SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scene_order_gap_shared import (
    build_scene_order_gap_summary as shared_build_scene_order_gap_summary,
    collect_scene_order_gap_rows as shared_collect_scene_order_gap_rows,
    render_scene_order_gap_markdown as shared_render_scene_order_gap_markdown,
)


def collect_scene_order_gap_rows(root: Path, conv_dir: Path) -> list[dict]:
    return shared_collect_scene_order_gap_rows(root, conv_dir)


def build_scene_order_gap_summary(rows: list[dict], language: str) -> dict:
    return shared_build_scene_order_gap_summary(rows, language)


def write_scene_order_gap_reports(
    root: Path,
    reports_dir: Path,
    language: str,
    conv_dir: Path,
    *,
    rows: list[dict] | None = None,
) -> dict:
    if rows is None:
        rows = collect_scene_order_gap_rows(root, conv_dir)
    summary = build_scene_order_gap_summary(rows, language)

    reports_dir.mkdir(parents=True, exist_ok=True)
    out_md = reports_dir / f"scene_order_gap_report_{language}.md"
    out_json = reports_dir / f"scene_order_gap_report_{language}.json"

    out_md.write_text(shared_render_scene_order_gap_markdown(summary, rows) + "\n", encoding="utf-8")
    write_report_json(out_json, {"summary": summary, "scenes": rows})

    print(f"  scene-order report: {out_md}")
    print(f"  scene-order data:   {out_json}")
    print(f"  flagged dlg scenes: {summary['totalFlaggedScenes']}")

    return {
        "summary": summary,
        "markdown": out_md,
        "json": out_json,
    }


def inferred_option_anchor_row(payload: dict, fallback_key: str = "") -> dict | None:
    """Return one inferred-anchor audit row from an in-memory conversation."""
    if not isinstance(payload, dict) or str(payload.get("kind") or "") != "dlg":
        return None
    warning = next(
        (
            item
            for item in (payload.get("warnings") or [])
            if isinstance(item, dict)
            and item.get("code") == "inferredOptionLayout"
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
    """Walk every dialog conv JSON and pull rows for option groups that landed
    on inferred fallback anchors. Used to audit how many
    scenes still rely on `pack_options` fallback after the build.
    """
    rows: list[dict] = []
    for path in sorted(conv_dir.glob("*.json")):
        payload = read_json(path, {})
        row = inferred_option_anchor_row(payload, path.stem)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: (row.get("mission") or "", row.get("scene") or 0, row.get("key") or ""))
    return rows


def write_inferred_option_anchors_report(
    reports_dir: Path,
    language: str,
    conv_dir: Path,
    *,
    rows: list[dict] | None = None,
) -> dict:
    if rows is None:
        rows = collect_inferred_option_anchor_rows(conv_dir)
    else:
        rows = list(rows)
        rows.sort(
            key=lambda row: (
                row.get("mission") or "",
                row.get("scene") or 0,
                row.get("key") or "",
            )
        )

    by_mode: dict[str, int] = {}
    for row in rows:
        for grp in row.get("inferredGroups") or []:
            mode = str(grp.get("mode") or "")
            if mode:
                by_mode[mode] = by_mode.get(mode, 0) + 1

    summary = {
        "language": language,
        "totalScenes": len(rows),
        "totalInferredGroups": sum(len(r.get("inferredGroups") or []) for r in rows),
        "groupsByMode": dict(sorted(by_mode.items())),
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    out_json = reports_dir / f"inferred_option_anchors_{language}.json"
    out_md = reports_dir / f"inferred_option_anchors_{language}.md"

    write_report_json(out_json, {"summary": summary, "scenes": rows})

    md_lines = [
        f"# Inferred option anchors — {language}",
        "",
        f"Scenes with at least one option group placed via fallback: **{summary['totalScenes']}**.",
        f"Total inferred groups: **{summary['totalInferredGroups']}**.",
        "",
        "## Counts by inference mode",
        "",
    ]
    for mode, count in summary["groupsByMode"].items():
        md_lines.append(f"- `{mode}`: {count}")
    md_lines.append("")
    md_lines.append("## Scenes")
    md_lines.append("")
    md_lines.append("| Scene | Lines | Groups | Inferred | Modes | Reason |")
    md_lines.append("| --- | ---: | ---: | ---: | --- | --- |")
    for row in rows:
        modes = sorted({str(g.get("mode") or "") for g in row.get("inferredGroups") or []})
        md_lines.append(
            f"| `{row.get('key', '')}` "
            f"| {row.get('lineCount', 0)} "
            f"| {row.get('groupCount', 0)} "
            f"| {len(row.get('inferredGroups') or [])} "
            f"| {', '.join(modes)} "
            f"| {row.get('reason') or ''} |"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"  inferred-anchors report: {out_md}")
    print(f"  inferred-anchors data:   {out_json}")
    print(f"  inferred-anchor scenes:  {summary['totalScenes']} ({summary['totalInferredGroups']} groups)")

    return {
        "summary": summary,
        "markdown": out_md,
        "json": out_json,
    }
