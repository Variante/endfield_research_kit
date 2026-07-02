#!/usr/bin/env python3
"""Replay saved FindTargetAction body-middle bytes against selector evidence.

`build_findtarget_selector_boundary_audit.py` stores the opaque middle bytes
that still block safe FindTargetAction chain consumption. This follow-up probe
does not rescan BuffData. It replays those saved byte shapes against the current
TargetSettings envelope helper and the IL2CPP selector formatter tag maps, then
records what is still only a hint versus what is an exact consume proof.

Output:

    reports/mission_order/findtarget_selector_replay_audit.json
    reports/mission_order/findtarget_selector_replay_audit.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

BUILD_DATA_INDEX = ROOT / "scripts" / "build_data_index.py"
REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_BOUNDARY_JSON = REPORT_DIR / "findtarget_selector_boundary_audit.json"
DEFAULT_TAG_JSON = REPORT_DIR / "selector_formatter_tag_audit.json"
DEFAULT_JSON = REPORT_DIR / "findtarget_selector_replay_audit.json"
DEFAULT_MD = REPORT_DIR / "findtarget_selector_replay_audit.md"

SELECTOR_ORDER_CANDIDATES = [
    {
        "id": "setter-prefix-post-validator-finder",
        "description": "SelectorData setter-call prefix from IL2CPP body audit",
        "families": ["postProcessor", "validator", "finder"],
    },
    {
        "id": "family-order-finder-validator-post",
        "description": "Finder/Validator/PostProcessor table order",
        "families": ["finder", "validator", "postProcessor"],
    },
]


def load_build_data_index() -> Any:
    spec = importlib.util.spec_from_file_location("endfield_build_data_index", BUILD_DATA_INDEX)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {BUILD_DATA_INDEX}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def hex_tag(value: int) -> str:
    return f"0x{value:04x}"


def offset_hex(value: int) -> str:
    return f"0x{value:x}"


def normalize_error(exc: BaseException) -> str:
    text = str(exc)
    if not text:
        return type(exc).__name__
    if ":unexpected-prefix=" in text:
        return "unexpected-prefix"
    if ":truncated-envelope" in text:
        return "truncated-envelope"
    if ":string-slot-length=" in text:
        return "string-slot-length"
    if ":envelope-limit=" in text:
        return "envelope-limit"
    if ":tail-u32=" in text:
        return "tail-u32"
    if ":unexpected-bytes=" in text:
        return "unexpected-bytes"
    if text.startswith("unsupported-union-tag-marker="):
        return "unsupported-union-tag-marker"
    if text.startswith("truncated-"):
        return text
    return text.split("=", 1)[0][:120]


def load_selector_tag_maps(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    maps: dict[str, dict[int, dict[str, Any]]] = {}
    summaries: dict[str, Any] = {}
    for table in payload.get("selectorTables") or []:
        family = str(table.get("id") or "")
        if not family:
            continue
        rows: dict[int, dict[str, Any]] = {}
        for row in table.get("formatterTags") or []:
            try:
                rows[int(row.get("tag"))] = row
            except (TypeError, ValueError):
                continue
        maps[family] = rows
        summaries[family] = table.get("summary") or {}
    return {
        "path": repo_rel(path),
        "available": bool(maps),
        "families": maps,
        "summary": summaries,
        "sourceSummary": (payload.get("summary") or {}),
    }


def tag_label(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("actionName") or row.get("formatterName") or row.get("typeName") or "")


def classify_tag(tag_maps: dict[str, dict[int, dict[str, Any]]], tag: int) -> list[dict[str, Any]]:
    matches = []
    for family, rows in tag_maps.items():
        row = rows.get(tag)
        if row is None:
            continue
        matches.append({"family": family, "tag": hex_tag(tag), "name": tag_label(row)})
    return matches


def read_union_tags(helper: Any, raw: bytes, offset: int, max_tags: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    tags = []
    cursor = offset
    for _index in range(max_tags):
        try:
            tag, next_cursor, width = helper.read_memorypack_union_tag(raw, cursor)
        except (ValueError, IndexError, struct.error) as exc:
            return tags, normalize_error(exc)
        tags.append(
            {
                "offset": offset_hex(cursor),
                "tag": tag,
                "tagHex": hex_tag(tag),
                "width": width,
                "nextOffset": offset_hex(next_cursor),
            }
        )
        cursor = next_cursor
    return tags, None


def order_matches(
    tags: list[dict[str, Any]],
    tag_maps: dict[str, dict[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    matches = []
    for candidate in SELECTOR_ORDER_CANDIDATES:
        families = candidate["families"]
        if len(tags) < len(families):
            continue
        resolved = []
        for tag_row, family in zip(tags, families):
            row = tag_maps.get(family, {}).get(int(tag_row["tag"]))
            if row is None:
                break
            resolved.append(
                {
                    "family": family,
                    "tag": tag_row["tagHex"],
                    "name": tag_label(row),
                }
            )
        else:
            matches.append(
                {
                    "id": candidate["id"],
                    "description": candidate["description"],
                    "resolved": resolved,
                }
            )
    return matches


def replay_target_settings(helper: Any, raw: bytes) -> dict[str, Any]:
    accepted = []
    failures: Counter[str] = Counter()
    exact_end_hits = 0
    for offset in range(len(raw)):
        try:
            decoded, end = helper.read_buff_target_settings_envelope_partial(
                raw,
                offset,
                len(raw),
                "findTargetAction.bodyMiddle.targetSettingsReplay",
            )
        except (ValueError, IndexError, struct.error, UnicodeDecodeError, TypeError, AttributeError) as exc:
            failures[normalize_error(exc)] += 1
            continue
        if end == len(raw):
            exact_end_hits += 1
        accepted.append(
            {
                "offset": offset_hex(offset),
                "end": offset_hex(end),
                "bytes": decoded.get("bytes"),
                "shape": decoded.get("shape"),
                "stringSlotValue": decoded.get("stringSlotValue"),
                "tailU32Candidate": decoded.get("tailU32Candidate"),
            }
        )
    return {
        "acceptedCount": len(accepted),
        "exactBodyMiddleEndHitCount": exact_end_hits,
        "acceptedCandidates": accepted,
        "failureReasons": dict(failures.most_common(12)),
    }


def replay_selector_tags(helper: Any, raw: bytes, tag_maps: dict[str, dict[int, dict[str, Any]]]) -> dict[str, Any]:
    union_hits = []
    union_hit_count = 0
    nonzero_union_hits = 0
    family_counts: Counter[str] = Counter()
    nonzero_family_counts: Counter[str] = Counter()
    family_tag_counts: Counter[str] = Counter()
    nonzero_family_tag_counts: Counter[str] = Counter()
    for offset in range(len(raw)):
        try:
            tag, next_offset, width = helper.read_memorypack_union_tag(raw, offset)
        except (ValueError, IndexError, struct.error):
            continue
        matches = classify_tag(tag_maps, tag)
        if not matches:
            continue
        union_hit_count += 1
        for match in matches:
            family = str(match.get("family") or "")
            key = f"{family}:{hex_tag(tag)}"
            family_counts[family] += 1
            family_tag_counts[key] += 1
            if tag:
                nonzero_family_counts[family] += 1
                nonzero_family_tag_counts[key] += 1
        if tag:
            nonzero_union_hits += 1
        if tag or len(union_hits) < 12:
            union_hits.append(
                {
                    "offset": offset_hex(offset),
                    "tag": hex_tag(tag),
                    "width": width,
                    "nextOffset": offset_hex(next_offset),
                    "families": matches,
                }
            )

    anchors = []
    for offset, value in enumerate(raw):
        if value != 3:
            continue
        tags, read_error = read_union_tags(helper, raw, offset + 1, max_tags=5)
        matches = order_matches(tags, tag_maps)
        anchors.append(
            {
                "memberCountOffset": offset_hex(offset),
                "tagStartOffset": offset_hex(offset + 1),
                "tagOnlyState": "header-only-no-payload-consumption",
                "tagsRead": len(tags),
                "readError": read_error,
                "zeroTagCount": sum(1 for row in tags if int(row.get("tag") or 0) == 0),
                "tags": [
                    {
                        **row,
                        "families": classify_tag(tag_maps, int(row["tag"])),
                    }
                    for row in tags
                ],
                "orderMatches": matches,
            }
        )

    plausible = [row for row in anchors if row.get("orderMatches")]
    nonzero_plausible = [
        row
        for row in plausible
        if any(int(tag.get("tag") or 0) != 0 for tag in (row.get("tags") or []))
    ]
    return {
        "unionTagHitCount": union_hit_count,
        "unionTagSampleCount": len(union_hits),
        "nonZeroUnionTagHitCount": nonzero_union_hits,
        "unionTagFamilyCounts": dict(family_counts.most_common()),
        "nonZeroUnionTagFamilyCounts": dict(nonzero_family_counts.most_common()),
        "unionTagFamilyTagCounts": dict(family_tag_counts.most_common(24)),
        "nonZeroUnionTagFamilyTagCounts": dict(nonzero_family_tag_counts.most_common(24)),
        "unionTagHitSamples": union_hits[:36],
        "memberCount3AnchorCount": len(anchors),
        "memberCount3Offsets": [row["memberCountOffset"] for row in anchors],
        "plausibleOrderAnchorCount": len(plausible),
        "nonZeroPlausibleOrderAnchorCount": len(nonzero_plausible),
        "zeroOnlyPlausibleOrderAnchorCount": len(plausible) - len(nonzero_plausible),
        "tagOnlyAnchorSamples": anchors[:24],
        "exactBoundaryProofCount": 0,
        "exactBoundaryProofStatus": "not-proven: selector formatter payloads are not consumed to a known end offset",
        "chainSafeFindTargetCount": 0,
    }


def shape_row(helper: Any, row: dict[str, Any], tag_maps: dict[str, dict[int, dict[str, Any]]]) -> dict[str, Any]:
    raw = bytes.fromhex(str(row.get("bodyMiddleHex") or ""))
    target_settings = replay_target_settings(helper, raw)
    selector = replay_selector_tags(helper, raw, tag_maps)
    return {
        "bodyMiddleSha256": row.get("bodyMiddleSha256"),
        "sampleCount": row.get("sampleCount"),
        "bodyMiddleBytes": row.get("bodyMiddleBytes"),
        "targetGroupKeys": row.get("targetGroupKeys") or [],
        "examplePath": row.get("examplePath"),
        "exampleRecordIndex": row.get("exampleRecordIndex"),
        "exampleItemOffset": row.get("exampleItemOffset"),
        "stringHits": row.get("stringHits") or [],
        "targetSettingsReplay": target_settings,
        "selectorReplay": selector,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    helper = load_build_data_index()
    boundary = read_json(args.boundary_json)
    tag_info = load_selector_tag_maps(args.tag_json)
    tag_maps = tag_info["families"]
    rows = [shape_row(helper, row, tag_maps) for row in boundary.get("uniqueBodyMiddleShapes") or []]

    target_settings_failures: Counter[str] = Counter()
    selector_family_counts: Counter[str] = Counter()
    selector_nonzero_family_counts: Counter[str] = Counter()
    selector_family_tag_counts: Counter[str] = Counter()
    selector_nonzero_family_tag_counts: Counter[str] = Counter()
    for row in rows:
        target_settings_failures.update(row.get("targetSettingsReplay", {}).get("failureReasons") or {})
        selector = row.get("selectorReplay") or {}
        selector_family_counts.update(selector.get("unionTagFamilyCounts") or {})
        selector_nonzero_family_counts.update(selector.get("nonZeroUnionTagFamilyCounts") or {})
        selector_family_tag_counts.update(selector.get("unionTagFamilyTagCounts") or {})
        selector_nonzero_family_tag_counts.update(selector.get("nonZeroUnionTagFamilyTagCounts") or {})

    summary = {
        "sourceBoundaryJson": repo_rel(args.boundary_json),
        "sourceTagJson": repo_rel(args.tag_json),
        "samplesAttempted": len(boundary.get("samples") or []),
        "uniqueBodyMiddleShapeCount": len(rows),
        "uniqueShapesAttempted": len(rows),
        "sourceDecodedFindTargetItemCount": (boundary.get("summary") or {}).get("decodedFindTargetItemCount"),
        "sourceAmbiguousFirstFindTargetRecordCount": (boundary.get("summary") or {}).get(
            "ambiguousFirstFindTargetRecordCount"
        ),
        "ambiguousRecordsAttempted": len(boundary.get("ambiguousFirstFindTargetRecords") or []),
        "targetSettingsAcceptedShapeCount": sum(
            1 for row in rows if int(row.get("targetSettingsReplay", {}).get("acceptedCount") or 0) > 0
        ),
        "targetSettingsAcceptedCandidateCount": sum(
            int(row.get("targetSettingsReplay", {}).get("acceptedCount") or 0) for row in rows
        ),
        "targetSettingsExactBodyMiddleEndHitCount": sum(
            int(row.get("targetSettingsReplay", {}).get("exactBodyMiddleEndHitCount") or 0) for row in rows
        ),
        "targetSettingsFailureReasons": dict(target_settings_failures.most_common(12)),
        "memberCount3AnchorShapeCount": sum(
            1 for row in rows if int(row.get("selectorReplay", {}).get("memberCount3AnchorCount") or 0) > 0
        ),
        "memberCount3AnchorCount": sum(
            int(row.get("selectorReplay", {}).get("memberCount3AnchorCount") or 0) for row in rows
        ),
        "selectorUnionTagHitCount": sum(
            int(row.get("selectorReplay", {}).get("unionTagHitCount") or 0) for row in rows
        ),
        "selectorNonZeroUnionTagHitCount": sum(
            int(row.get("selectorReplay", {}).get("nonZeroUnionTagHitCount") or 0) for row in rows
        ),
        "selectorUnionTagFamilyCounts": dict(selector_family_counts.most_common()),
        "selectorNonZeroUnionTagFamilyCounts": dict(selector_nonzero_family_counts.most_common()),
        "selectorUnionTagFamilyTagCounts": dict(selector_family_tag_counts.most_common(24)),
        "selectorNonZeroUnionTagFamilyTagCounts": dict(selector_nonzero_family_tag_counts.most_common(24)),
        "plausibleSelectorOrderAnchorCount": sum(
            int(row.get("selectorReplay", {}).get("plausibleOrderAnchorCount") or 0) for row in rows
        ),
        "nonZeroPlausibleSelectorOrderAnchorCount": sum(
            int(row.get("selectorReplay", {}).get("nonZeroPlausibleOrderAnchorCount") or 0) for row in rows
        ),
        "zeroOnlyPlausibleSelectorOrderAnchorCount": sum(
            int(row.get("selectorReplay", {}).get("zeroOnlyPlausibleOrderAnchorCount") or 0) for row in rows
        ),
        "exactBoundaryProofCount": 0,
        "chainSafeFindTargetCount": 0,
        "ambiguousRecordsExplained": 0,
    }

    return {
        "metadata": {
            "helper": repo_rel(BUILD_DATA_INDEX),
            "boundaryAudit": repo_rel(args.boundary_json),
            "selectorTagAudit": repo_rel(args.tag_json),
            "selectorTagSummary": tag_info["sourceSummary"],
        },
        "settings": {
            "markdownShapes": args.markdown_shapes,
            "selectorOrderCandidates": SELECTOR_ORDER_CANDIDATES,
        },
        "summary": summary,
        "interpretation": [
            "TargetSettings replay is exact: accepted candidates would use the same envelope helper as the WebUI data decoder.",
            "Selector replay is intentionally tag-only. Member-count and union-tag hits are useful priorities, but they do not consume formatter payloads or prove field boundaries.",
            "FindTargetAction chain consumption should remain disabled until SelectorData payload readers consume to a known boundary such as selectorOwner or item end.",
        ],
        "shapes": rows,
    }


def render_counts(value: dict[str, Any], limit: int = 6) -> str:
    items = list(value.items())[:limit]
    return ", ".join(f"{key}: {count}" for key, count in items) or "-"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    settings = payload.get("settings") or {}
    lines = [
        "# FindTarget Selector Replay Audit",
        "",
        f"- Source boundary JSON: `{md_escape(summary.get('sourceBoundaryJson'))}`",
        f"- Source tag JSON: `{md_escape(summary.get('sourceTagJson'))}`",
        f"- unique body-middle shapes: `{summary.get('uniqueBodyMiddleShapeCount')}`",
        f"- source decoded FindTarget items: `{summary.get('sourceDecodedFindTargetItemCount')}`",
        f"- source ambiguous first-FindTarget records: `{summary.get('sourceAmbiguousFirstFindTargetRecordCount')}`",
        f"- TargetSettings accepted candidates: `{summary.get('targetSettingsAcceptedCandidateCount')}`",
        f"- TargetSettings exact body-middle end hits: `{summary.get('targetSettingsExactBodyMiddleEndHitCount')}`",
        f"- member-count=3 anchors: `{summary.get('memberCount3AnchorCount')}`",
        f"- selector union-tag hits: `{summary.get('selectorUnionTagHitCount')}` "
        f"(nonzero `{summary.get('selectorNonZeroUnionTagHitCount')}`)",
        f"- plausible selector order anchors: `{summary.get('plausibleSelectorOrderAnchorCount')}` "
        f"(nonzero `{summary.get('nonZeroPlausibleSelectorOrderAnchorCount')}`, "
        f"zero-only `{summary.get('zeroOnlyPlausibleSelectorOrderAnchorCount')}`)",
        f"- exact boundary proofs: `{summary.get('exactBoundaryProofCount')}`",
        f"- chain-safe FindTarget consumptions: `{summary.get('chainSafeFindTargetCount')}`",
        f"- ambiguous records explained: `{summary.get('ambiguousRecordsExplained')}`",
        "",
        "## Interpretation",
        "",
    ]
    for item in payload.get("interpretation") or []:
        lines.append(f"- {md_escape(item)}")

    lines.extend(
        [
            "",
            "## TargetSettings Replay",
            "",
            f"- Accepted candidate count: `{summary.get('targetSettingsAcceptedCandidateCount')}`",
            f"- Exact body-middle end hits: `{summary.get('targetSettingsExactBodyMiddleEndHitCount')}`",
            f"- Top failure reasons: `{md_escape(render_counts(summary.get('targetSettingsFailureReasons') or {}))}`",
            "",
            "## Selector Tag Hints",
            "",
            f"- Family counts: `{md_escape(render_counts(summary.get('selectorUnionTagFamilyCounts') or {}))}`",
            f"- Nonzero family counts: `{md_escape(render_counts(summary.get('selectorNonZeroUnionTagFamilyCounts') or {}))}`",
            f"- Top nonzero family/tag counts: `{md_escape(render_counts(summary.get('selectorNonZeroUnionTagFamilyTagCounts') or {}, 10))}`",
            "",
            "## Shape Replay",
            "",
        ]
    )
    for row in (payload.get("shapes") or [])[: int(settings.get("markdownShapes") or 24)]:
        target_settings = row.get("targetSettingsReplay") or {}
        selector = row.get("selectorReplay") or {}
        keys = ", ".join(row.get("targetGroupKeys") or [])
        lines.append(
            f"- `{row.get('bodyMiddleSha256')}` count=`{row.get('sampleCount')}` "
            f"bytes=`{row.get('bodyMiddleBytes')}` targetGroups=`{md_escape(keys)}`"
        )
        lines.append(
            f"  - targetSettings accepted=`{target_settings.get('acceptedCount')}` "
            f"exactEnd=`{target_settings.get('exactBodyMiddleEndHitCount')}` "
            f"failures=`{md_escape(render_counts(target_settings.get('failureReasons') or {}, 4))}`"
        )
        lines.append(
            f"  - selector member3=`{selector.get('memberCount3AnchorCount')}` "
            f"plausibleOrders=`{selector.get('plausibleOrderAnchorCount')}` "
            f"nonzeroOrders=`{selector.get('nonZeroPlausibleOrderAnchorCount')}` "
            f"unionHits=`{selector.get('unionTagHitCount')}` "
            f"nonzeroUnionHits=`{selector.get('nonZeroUnionTagHitCount')}`"
        )
        sample_anchors = selector.get("tagOnlyAnchorSamples") or []
        for anchor in sample_anchors[:3]:
            tags = ", ".join(str(tag.get("tagHex")) for tag in (anchor.get("tags") or [])[:5])
            matches = ", ".join(match.get("id", "") for match in anchor.get("orderMatches") or [])
            lines.append(
                f"  - anchor `{anchor.get('memberCountOffset')}` tags=`{md_escape(tags)}` "
                f"matches=`{md_escape(matches or '-')}`"
            )

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary-json", type=Path, default=DEFAULT_BOUNDARY_JSON)
    parser.add_argument("--tag-json", type=Path, default=DEFAULT_TAG_JSON)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--markdown-shapes", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(f"FindTarget selector replay audit: {args.json}")
    print(f"FindTarget selector replay report: {args.markdown}")
    print(
        "uniqueShapes="
        f"{summary['uniqueBodyMiddleShapeCount']} "
        f"targetSettingsAccepted={summary['targetSettingsAcceptedCandidateCount']} "
        f"selectorOrderAnchors={summary['plausibleSelectorOrderAnchorCount']} "
        f"exactBoundaryProofs={summary['exactBoundaryProofCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
