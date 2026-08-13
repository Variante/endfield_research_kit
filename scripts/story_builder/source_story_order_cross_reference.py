"""Compare strict source-order edges with OCR/manual lists without promoting them.

The source partial-order report is the only evidence input. Story-order
overrides and OCR proposals are diagnostic cross-references: agreement does not
upgrade an edge, disagreement does not automatically invalidate one, and no
cross-reference row is ever emitted as a source-order edge.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

try:
    from ..common import md_escape, safe_key
except ImportError:
    from common import md_escape, safe_key

from .mission_recovery import natural_key


SCHEMA = "sourceStoryOrderCrossReference.v1"


def _mission_orders(payload: Any) -> dict[str, list[str]]:
    missions = payload.get("missions") if isinstance(payload, dict) else {}
    if not isinstance(missions, dict):
        return {}
    out: dict[str, list[str]] = {}
    for mission, row in missions.items():
        if not isinstance(row, dict) or not isinstance(row.get("order"), list):
            continue
        order: list[str] = []
        for value in row["order"]:
            key = safe_key(value)
            if key and key not in order:
                order.append(key)
        if order:
            out[safe_key(mission)] = order
    return out


def _check_edge(edge: dict[str, Any], order: list[str]) -> dict[str, Any]:
    positions = {key: index for index, key in enumerate(order)}
    src = safe_key(edge.get("from"))
    dst = safe_key(edge.get("to"))
    if src not in positions or dst not in positions:
        return {
            "status": "uncovered",
            "missing": [key for key in (src, dst) if key not in positions],
        }
    return {
        "status": "agrees" if positions[src] < positions[dst] else "disagrees",
        "fromIndex": positions[src],
        "toIndex": positions[dst],
    }


def build_report(
    partial_order: dict[str, Any],
    override_payload: dict[str, Any],
    ocr_payload: dict[str, Any],
) -> dict[str, Any]:
    override_orders = _mission_orders(override_payload)
    ocr_orders = _mission_orders(ocr_payload)
    rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    kind_totals: dict[str, Counter[str]] = {}

    for mission_row in partial_order.get("missions") or []:
        if not isinstance(mission_row, dict):
            continue
        mission = safe_key(mission_row.get("mission"))
        strict_edges = [
            edge
            for edge in mission_row.get("directEdges") or []
            if isinstance(edge, dict) and safe_key(edge.get("tier")) == "strong"
        ]
        if not strict_edges:
            continue
        mission_results: list[dict[str, Any]] = []
        for edge in strict_edges:
            kind = safe_key(edge.get("kind")) or "sourceEdge"
            result = {
                "from": safe_key(edge.get("from")),
                "to": safe_key(edge.get("to")),
                "kind": kind,
                "source": edge.get("source"),
                "override": _check_edge(edge, override_orders.get(mission, [])),
                "ocr": _check_edge(edge, ocr_orders.get(mission, [])),
            }
            statuses = {
                result["override"]["status"],
                result["ocr"]["status"],
            }
            if statuses == {"agrees", "disagrees"}:
                result["crossReferenceConflict"] = True
                totals["crossReferenceConflicts"] += 1
            for reference in ("override", "ocr"):
                status = result[reference]["status"]
                totals[f"{reference}_{status}"] += 1
                kind_totals.setdefault(kind, Counter())[f"{reference}_{status}"] += 1
            mission_results.append(result)

        mission_counts = Counter(
            f"{reference}_{result[reference]['status']}"
            for result in mission_results
            for reference in ("override", "ocr")
        )
        rows.append({
            "mission": mission,
            "strictEdgeCount": len(strict_edges),
            "counts": dict(sorted(mission_counts.items())),
            "edges": mission_results,
        })
        totals["missions"] += 1
        totals["strictEdges"] += len(strict_edges)

    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "policy": {
            "evidenceInput": "source_story_partial_order directEdges with tier=strong",
            "crossReferences": [
                "webui/overrides/story_order.json",
                "webui/data/story_order_ocr.json",
            ],
            "promotionRule": "none; cross-reference agreement and disagreement are diagnostic only",
        },
        "inputs": {
            "partialOrderSchema": safe_key(partial_order.get("_schema")),
            "partialOrderGeneratedAt": safe_key(partial_order.get("_generatedAt")),
            "overrideSchema": safe_key(override_payload.get("_schema")),
            "ocrSchema": safe_key(ocr_payload.get("_schema")),
            "ocrGeneratedAt": safe_key(ocr_payload.get("_generatedAt")),
        },
        "summary": {
            **dict(totals),
            "edgeKinds": {
                kind: dict(sorted(counts.items()))
                for kind, counts in sorted(kind_totals.items())
            },
        },
        "missions": sorted(rows, key=lambda row: natural_key(row["mission"])),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Source Story Order Cross-reference",
        "",
        f"Generated: `{report['_generatedAt']}`",
        "",
        "Only strict edges from the source partial-order report are evidence.",
        "Manual override and OCR lists are fallible diagnostic cross-references;",
        "they never create, strengthen, weaken, or remove an ordering edge.",
        "",
        "## Summary",
        "",
        f"- missions with strict edges: `{summary.get('missions', 0)}`",
        f"- strict direct edges: `{summary.get('strictEdges', 0)}`",
        f"- override: `{summary.get('override_agrees', 0)}` agree, "
        f"`{summary.get('override_disagrees', 0)}` disagree, "
        f"`{summary.get('override_uncovered', 0)}` uncovered",
        f"- OCR: `{summary.get('ocr_agrees', 0)}` agree, "
        f"`{summary.get('ocr_disagrees', 0)}` disagree, "
        f"`{summary.get('ocr_uncovered', 0)}` uncovered",
        f"- override/OCR conflicts on the same strict edge: "
        f"`{summary.get('crossReferenceConflicts', 0)}`",
        "",
        "## Missions With Cross-reference Disagreements",
        "",
        "| mission | strict edges | override disagree | OCR disagree | reference conflicts |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    disagreement_rows = []
    for row in report["missions"]:
        counts = row.get("counts") or {}
        conflicts = sum(bool(edge.get("crossReferenceConflict")) for edge in row.get("edges") or [])
        if counts.get("override_disagrees", 0) or counts.get("ocr_disagrees", 0):
            disagreement_rows.append((
                row,
                counts.get("override_disagrees", 0),
                counts.get("ocr_disagrees", 0),
                conflicts,
            ))
    disagreement_rows.sort(
        key=lambda item: (-(item[1] + item[2]), natural_key(item[0]["mission"]))
    )
    if disagreement_rows:
        for row, override_disagree, ocr_disagree, conflicts in disagreement_rows:
            lines.append(
                f"| `{md_escape(row['mission'])}` | {row['strictEdgeCount']} | "
                f"{override_disagree} | {ocr_disagree} | {conflicts} |"
            )
    else:
        lines.append("| _(none)_ | 0 | 0 | 0 | 0 |")
    return "\n".join(lines) + "\n"


__all__ = ["SCHEMA", "build_report", "render_markdown"]
