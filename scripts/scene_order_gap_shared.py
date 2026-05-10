from __future__ import annotations

import json
import re
from pathlib import Path


AUTHORED_LINE_ORDER_MODES = {
    "authoredBlend",
    "dialogTimeline",
    "dialogTree",
    "dialogTreeExtraConfig",
    "dialogTreeFragment",
}

OPTION_LAYOUT_REASON_TITLES = {
    "noTreeReference": "no AnimeStudio option reference",
    "noAuthoredGroupAnchor": "no authored group anchor",
    "partialAuthoredCoverage": "partial authored group coverage",
    "inferredOptionLayout": "inferred option placement",
    "ok": "authored option anchors",
    "notNeeded": "not needed",
}

OPTION_LAYOUT_REASON_DESCRIPTIONS = {
    "noTreeReference": (
        "no AnimeStudio tree references any option id for this scene, so every "
        "option group's position is unanchored; fallback candidates are "
        "reported only as diagnostics"
    ),
    "noAuthoredGroupAnchor": (
        "tree data exists for some options, but no group received an authored "
        "`after` or `pre` anchor; fallback candidates are reported only as diagnostics"
    ),
    "partialAuthoredCoverage": (
        "some option groups stayed on authored anchors while others only have "
        "diagnostic fallback candidates"
    ),
    "inferredOptionLayout": "option placement is inferred rather than fully anchored",
}

LINE_ORDER_PATTERN_TITLES = {
    "ok": "authored order",
    "notNeeded": "not needed",
    "partialAuthoredCoverage": "partial authored coverage",
    "numericSuffixFallback": "numeric-suffix fallback",
    "missingBlockButSuffixSortable": "missing block, suffix-sortable",
    "missingBlockNoSafeFallback": "missing block, unsafe raw ids",
    "otherFallbackMode": "other fallback mode",
    "fallbackWithoutMode": "fallback without mode",
}

LINE_ORDER_PATTERN_DESCRIPTIONS = {
    "partialAuthoredCoverage": (
        "authored line-order data exists, but it does not cover every scene "
        "line, so the uncovered lines still rely on raw table order."
    ),
    "numericSuffixFallback": (
        "authored line order is missing, so the report keeps this scene in the "
        "generic fallback-order bucket. This broad bucket covers cinematic-only "
        "trees, missing-tree scenes, and other unsupported authored-order cases."
    ),
    "missingBlockButSuffixSortable": (
        "the builder omitted `_debug.lineOrder`, but the raw line ids still look "
        "safe to sort by numeric suffix."
    ),
    "missingBlockNoSafeFallback": (
        "the builder omitted `_debug.lineOrder`, and the raw line ids do not "
        "support a safe numeric-suffix fallback."
    ),
    "otherFallbackMode": (
        "the builder recorded a fallback mode other than the standard numeric-"
        "suffix emulation."
    ),
    "fallbackWithoutMode": (
        "a fallback line-order block exists, but it does not declare which mode "
        "produced it."
    ),
}

OPTION_POSITION_PATTERN_TITLES = {
    "ok": "authored positions",
    "notNeeded": "not needed",
    "syntheticAfterAllGroups": "all groups have fallback candidates",
    "mixedAuthoredAndSyntheticAfter": "mixed authored + fallback candidates",
    "unanchoredAllGroups": "all groups unanchored",
    "mixedSyntheticAfterAndUnanchored": "mixed fallback candidates + unanchored",
    "mixedAuthoredAndUnanchored": "mixed authored + unanchored",
    "mixedAuthoredFallbackAndUnanchored": "mixed authored + candidates + unanchored",
    "genericInferredPositions": "generic inferred positions",
}

OPTION_POSITION_PATTERN_DESCRIPTIONS = {
    "syntheticAfterAllGroups": (
        "every meaningful option group lacked an authored position, so the "
        "report lists fallback `after` candidates without treating them as authored."
    ),
    "mixedAuthoredAndSyntheticAfter": (
        "some option groups keep authored positions while the remaining groups "
        "only have fallback `after` candidates."
    ),
    "unanchoredAllGroups": (
        "no option group has a usable authored position or fallback "
        "anchor, so every group remains unanchored."
    ),
    "mixedSyntheticAfterAndUnanchored": (
        "some option groups have fallback `after` candidates, while "
        "others still remain unanchored."
    ),
    "mixedAuthoredAndUnanchored": (
        "some option groups keep authored positions, while others remain "
        "unanchored."
    ),
    "mixedAuthoredFallbackAndUnanchored": (
        "the scene mixes authored option positions, fallback `after` candidates, "
        "and fully unanchored groups."
    ),
    "genericInferredPositions": (
        "option positions were inferred, but the missing-position pattern did not "
        "fit the standard simplified buckets."
    ),
}


def has_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_line_ids(values) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out


def _line_id_suffix(line_id: str) -> int | None:
    match = re.search(r"_(\d+)$", line_id)
    return int(match.group(1)) if match else None


def _summarize_items(values: list[str], limit: int = 5) -> str:
    clean = [str(value) for value in values if str(value).strip()]
    if not clean:
        return ""
    if len(clean) <= limit:
        return ", ".join(clean)
    return ", ".join(clean[:limit]) + f", +{len(clean) - limit} more"


def _escape_table_text(text: str) -> str:
    return str(text).replace("|", "\\|")


def _as_int(value, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _count_meaningful_lines(conv: dict) -> int:
    return sum(
        1
        for line in (conv.get("lines") or [])
        if isinstance(line, dict)
        and (
            has_text(line.get("actor"))
            or has_text(line.get("text"))
            or has_text(line.get("hint"))
        )
    )


def has_meaningful_lines(conv: dict) -> bool:
    return _count_meaningful_lines(conv) > 0 and len(conv.get("lines") or []) > 1


def _count_meaningful_options(conv: dict) -> int:
    return sum(
        1
        for group in (conv.get("optionGroups") or [])
        if isinstance(group, dict)
        for option in (group.get("options") or [])
        if isinstance(option, dict) and has_text(option.get("text"))
    )


def has_meaningful_options(conv: dict) -> bool:
    return _count_meaningful_options(conv) > 0


def _line_order_input_ids(conv: dict, line_order: dict | None) -> list[str]:
    if isinstance(line_order, dict):
        original = _normalize_line_ids(line_order.get("originalLineIds"))
        if original:
            return original
    return _normalize_line_ids([
        line.get("id")
        for line in (conv.get("lines") or [])
        if isinstance(line, dict)
    ])


def _line_order_output_ids(conv: dict, line_order: dict | None) -> list[str]:
    if isinstance(line_order, dict):
        ordered = _normalize_line_ids(line_order.get("orderedLineIds"))
        if ordered:
            return ordered
    return _line_order_input_ids(conv, line_order)


def _moved_line_ids(original_ids: list[str], ordered_ids: list[str]) -> list[str]:
    original_index = {line_id: idx for idx, line_id in enumerate(original_ids)}
    return [
        line_id
        for idx, line_id in enumerate(ordered_ids)
        if original_index.get(line_id) != idx
    ]


def _line_id_suffix_diagnostics(line_ids: list[str]) -> dict:
    missing_suffix_ids: list[str] = []
    suffix_map: dict[int, list[str]] = {}
    for line_id in line_ids:
        suffix = _line_id_suffix(line_id)
        if suffix is None:
            missing_suffix_ids.append(line_id)
            continue
        suffix_map.setdefault(suffix, []).append(line_id)
    duplicate_suffixes = [
        {
            "suffix": suffix,
            "lineIds": ids,
        }
        for suffix, ids in sorted(suffix_map.items())
        if len(ids) > 1
    ]
    usable = bool(line_ids) and not missing_suffix_ids and not duplicate_suffixes
    return {
        "usable": usable,
        "missingSuffixLineIds": missing_suffix_ids,
        "duplicateSuffixes": duplicate_suffixes,
    }


def _summarize_line_order_source(source: dict, line_count: int) -> dict:
    kind = str(source.get("kind") or "unknown")
    source_key = str(source.get("sourceKey") or "")
    file_path = str(source.get("file") or "")
    matched_line_ids = _normalize_line_ids(source.get("matchedLineIds"))
    added_line_ids = _normalize_line_ids(source.get("addedLineIds")) or matched_line_ids
    coverage = source.get("coverage")
    if not isinstance(coverage, int):
        coverage = len(matched_line_ids)

    detail_parts = [kind]
    if source_key:
        detail_parts.append(f"source={source_key}")
    detail_parts.append(f"covers {coverage}/{line_count} line(s)")
    if added_line_ids:
        detail_parts.append(f"adds {len(added_line_ids)} line(s)")
    elif matched_line_ids:
        detail_parts.append(f"matches {len(matched_line_ids)} line id(s)")
    if file_path:
        detail_parts.append(f"file={file_path}")

    return {
        "kind": kind,
        "sourceKey": source_key,
        "file": file_path,
        "coverage": coverage,
        "matchedLineIds": matched_line_ids,
        "addedLineIds": added_line_ids,
        "detail": "; ".join(detail_parts),
    }


def analyze_line_order(conv: dict) -> dict:
    total_line_count = len(conv.get("lines") or [])
    meaningful_line_count = _count_meaningful_lines(conv)
    debug = conv.get("_debug") or {}
    line_order = debug.get("lineOrder") if isinstance(debug, dict) else None
    input_line_ids = _line_order_input_ids(conv, line_order if isinstance(line_order, dict) else None)
    ordered_line_ids = _line_order_output_ids(conv, line_order if isinstance(line_order, dict) else None)

    if not has_meaningful_lines(conv):
        return {
            "status": "direct",
            "statusLabel": "not needed",
            "reasonCode": "notNeeded",
            "reason": "not needed (no multi-line spoken content)",
            "detail": (
                f"scene has {meaningful_line_count} meaningful line(s) across "
                f"{total_line_count} stored line(s), so explicit line-order recovery "
                "is not needed"
            ),
            "evidence": [],
            "mode": "",
            "sources": [],
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
        }

    if not isinstance(line_order, dict):
        suffix_diag = _line_id_suffix_diagnostics(input_line_ids)
        evidence = [
            f"{meaningful_line_count} meaningful line(s) across {total_line_count} stored line(s)",
        ]
        if suffix_diag["missingSuffixLineIds"]:
            evidence.append(
                "numeric suffix fallback unavailable because some line ids lack "
                "an `_NNN` suffix"
            )
        if suffix_diag["duplicateSuffixes"]:
            evidence.append(
                "numeric suffix fallback unavailable because suffixes are not unique"
            )
        if input_line_ids and suffix_diag["usable"]:
            evidence.append(
                "raw line ids appear suffix-sortable, so the missing line-order "
                "block is unexpected"
            )
            detail = (
                "builder produced no `_debug.lineOrder` even though the raw line ids "
                "look compatible with numeric suffix fallback"
            )
        else:
            detail = (
                "builder produced no `_debug.lineOrder`, and the raw line ids do not "
                "provide a safe numeric suffix fallback"
            )
        return {
            "status": "missing",
            "statusLabel": "missing line order",
            "reasonCode": "noLineOrderBlock",
            "reason": "no recovered line-order block",
            "detail": detail,
            "evidence": evidence,
            "mode": "",
            "sources": [],
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
        }

    mode = str(line_order.get("mode") or "")
    line_count = len(ordered_line_ids)
    sources = [
        _summarize_line_order_source(source, line_count)
        for source in (line_order.get("sources") or [])
        if isinstance(source, dict)
    ]
    moved_line_ids = _moved_line_ids(input_line_ids, ordered_line_ids)
    evidence = [
        f"{meaningful_line_count} meaningful line(s) across {total_line_count} stored line(s)",
        f"builder emitted {line_count} ordered line id(s)",
    ]
    if moved_line_ids:
        evidence.append(
            f"{len(moved_line_ids)} line(s) moved relative to the raw table order"
        )
    elif input_line_ids and ordered_line_ids:
        evidence.append("final order matches the raw line table order")
    for source in sources:
        evidence.append(source["detail"])

    covered_line_ids: list[str] = []
    seen_covered: set[str] = set()
    for source in sources:
        for line_id in _normalize_line_ids(source.get("matchedLineIds")):
            if line_id not in seen_covered:
                seen_covered.add(line_id)
                covered_line_ids.append(line_id)
    uncovered_line_ids = [
        line_id
        for line_id in input_line_ids
        if line_id and line_id not in seen_covered
    ]
    if uncovered_line_ids:
        evidence.append(
            f"{len(uncovered_line_ids)} line(s) not covered by authored sources: "
            f"{_summarize_items(uncovered_line_ids, limit=8)}"
        )

    if mode in AUTHORED_LINE_ORDER_MODES:
        if uncovered_line_ids:
            detail = (
                f"authored line order recovered through `{mode}`, but "
                f"{len(uncovered_line_ids)} line(s) were not covered: "
                f"{_summarize_items(uncovered_line_ids, limit=8)}"
            )
            return {
                "status": "partial",
                "statusLabel": "partial authored line order",
                "reasonCode": "partialAuthoredCoverage",
                "reason": "partial authored line order",
                "detail": detail,
                "evidence": evidence,
                "mode": mode,
                "sources": sources,
                "orderedLineIds": ordered_line_ids,
                "originalLineIds": input_line_ids,
                "coveredLineIds": covered_line_ids,
                "uncoveredLineIds": uncovered_line_ids,
                "coveredLineCount": len(covered_line_ids),
                "uncoveredLineCount": len(uncovered_line_ids),
            }
        reason = "direct dialogTree order" if mode == "dialogTree" else f"authored order via {mode}"
        detail = (
            "own AnimeStudio tree supplies the full line order"
            if mode == "dialogTree"
            else f"authored line order recovered through `{mode}`"
        )
        return {
            "status": "direct",
            "statusLabel": "has line order",
            "reasonCode": mode,
            "reason": reason,
            "detail": detail,
            "evidence": evidence,
            "mode": mode,
            "sources": sources,
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
            "coveredLineIds": covered_line_ids,
            "uncoveredLineIds": uncovered_line_ids,
            "coveredLineCount": len(covered_line_ids),
            "uncoveredLineCount": len(uncovered_line_ids),
        }

    if mode == "lineIdSuffix":
        detail = (
            "no authored line-order source matched this scene"
        )
        return {
            "status": "fallback",
            "statusLabel": "fallback line order",
            "reasonCode": "lineIdSuffix",
            "reason": "fallback line order",
            "detail": detail,
            "evidence": evidence,
            "mode": mode,
            "sources": sources,
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
            "coveredLineIds": covered_line_ids,
            "uncoveredLineIds": uncovered_line_ids,
            "coveredLineCount": len(covered_line_ids),
            "uncoveredLineCount": len(uncovered_line_ids),
        }

    if mode:
        return {
            "status": "fallback",
            "statusLabel": "fallback line order",
            "reasonCode": f"fallback:{mode}",
            "reason": f"fallback order via {mode}",
            "detail": f"line-order block exists, but it uses fallback mode `{mode}`",
            "evidence": evidence,
            "mode": mode,
            "sources": sources,
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
            "coveredLineIds": covered_line_ids,
            "uncoveredLineIds": uncovered_line_ids,
            "coveredLineCount": len(covered_line_ids),
            "uncoveredLineCount": len(uncovered_line_ids),
        }

    return {
        "status": "fallback",
        "statusLabel": "fallback line order",
        "reasonCode": "fallback:unknown",
        "reason": "fallback order",
        "detail": "line-order block exists, but it does not declare a recovery mode",
        "evidence": evidence,
        "mode": "",
        "sources": sources,
        "orderedLineIds": ordered_line_ids,
        "originalLineIds": input_line_ids,
        "coveredLineIds": covered_line_ids,
        "uncoveredLineIds": uncovered_line_ids,
        "coveredLineCount": len(covered_line_ids),
        "uncoveredLineCount": len(uncovered_line_ids),
    }


def inferred_option_warning(conv: dict) -> dict | None:
    if not has_meaningful_options(conv):
        return None
    for warning in (conv.get("warnings") or []):
        if isinstance(warning, dict) and warning.get("code") == "inferredOptionLayout":
            return warning
    return None


def _normalize_group_details(conv: dict, warning: dict | None) -> list[dict]:
    if isinstance(warning, dict):
        raw_group_details = warning.get("groupDetails") or []
        normalized: list[dict] = []
        for raw in raw_group_details:
            if not isinstance(raw, dict):
                continue
            group_value = raw.get("group")
            label = f"g{group_value}" if isinstance(group_value, int) else "g?"
            normalized.append({
                "group": group_value,
                "label": label,
                "status": str(raw.get("status") or "unknown"),
                "after": str(raw.get("after") or raw.get("fallbackAnchorId") or ""),
                "position": str(raw.get("position") or ""),
                "inferredAnchorMode": str(raw.get("inferredAnchorMode") or ""),
                "optionIds": _normalize_line_ids(raw.get("optionIds")),
                "authoredOptionIds": _normalize_line_ids(raw.get("authoredOptionIds")),
                "unauthoredOptionIds": _normalize_line_ids(raw.get("unauthoredOptionIds")),
                "treeAfterOptionIds": _normalize_line_ids(raw.get("treeAfterOptionIds")),
                "sceneLinkAfterOptionIds": _normalize_line_ids(raw.get("sceneLinkAfterOptionIds")),
                "timelineAfterOptionIds": _normalize_line_ids(raw.get("timelineAfterOptionIds")),
                "cinematicAfterOptionIds": _normalize_line_ids(raw.get("cinematicAfterOptionIds")),
                "textAliasAfterOptionIds": _normalize_line_ids(raw.get("textAliasAfterOptionIds")),
                "textAliasPreOptionIds": _normalize_line_ids(raw.get("textAliasPreOptionIds")),
                "textAliasSourceOptionIds": _normalize_line_ids(raw.get("textAliasSourceOptionIds")),
                "preOptionIds": _normalize_line_ids(raw.get("preOptionIds")),
                "timelinePreOptionIds": _normalize_line_ids(raw.get("timelinePreOptionIds")),
                "cinematicSources": _normalize_line_ids(raw.get("cinematicSources")),
                "textAliasSources": _normalize_line_ids(raw.get("textAliasSources")),
            })
        if normalized:
            return normalized

    fallback_labels = {
        str(label)
        for label in ((warning or {}).get("fallbackGroups") or [])
        if str(label).strip()
    }
    details: list[dict] = []
    for group in (conv.get("optionGroups") or []):
        if not isinstance(group, dict):
            continue
        group_value = group.get("g")
        label = f"g{group_value}" if isinstance(group_value, int) else "g?"
        option_ids = [
            str(option.get("id") or "")
            for option in (group.get("options") or [])
            if isinstance(option, dict) and option.get("id")
        ]
        if label in fallback_labels and group.get("after"):
            status = "fallbackAfter"
        elif label in fallback_labels:
            status = "unanchored"
        elif group.get("position") == "pre":
            status = "authoredPre"
        elif group.get("after"):
            status = "authoredAfter"
        else:
            status = "unanchored"
        details.append({
            "group": group_value,
            "label": label,
            "status": status,
            "after": str(group.get("after") or ""),
            "position": str(group.get("position") or ""),
            "inferredAnchorMode": "",
            "optionIds": option_ids,
            "authoredOptionIds": [],
            "unauthoredOptionIds": [],
            "treeAfterOptionIds": [],
            "sceneLinkAfterOptionIds": [],
            "timelineAfterOptionIds": [],
            "cinematicAfterOptionIds": [],
            "textAliasAfterOptionIds": [],
            "textAliasPreOptionIds": [],
            "textAliasSourceOptionIds": [],
            "preOptionIds": [],
            "timelinePreOptionIds": [],
            "cinematicSources": [],
            "textAliasSources": [],
        })
    return details


def _render_group_detail(group_detail: dict) -> str:
    label = group_detail.get("label") or "g?"
    status = str(group_detail.get("status") or "unknown")
    after = str(group_detail.get("after") or "")
    inferred_anchor_mode = str(group_detail.get("inferredAnchorMode") or "")
    option_ids = _normalize_line_ids(group_detail.get("optionIds"))
    unauthored_option_ids = _normalize_line_ids(group_detail.get("unauthoredOptionIds"))
    tree_after_option_ids = _normalize_line_ids(group_detail.get("treeAfterOptionIds"))
    scene_link_after_option_ids = _normalize_line_ids(group_detail.get("sceneLinkAfterOptionIds"))
    timeline_after_option_ids = _normalize_line_ids(group_detail.get("timelineAfterOptionIds"))
    cinematic_after_option_ids = _normalize_line_ids(group_detail.get("cinematicAfterOptionIds"))
    text_alias_after_option_ids = _normalize_line_ids(group_detail.get("textAliasAfterOptionIds"))
    text_alias_pre_option_ids = _normalize_line_ids(group_detail.get("textAliasPreOptionIds"))
    text_alias_source_option_ids = _normalize_line_ids(group_detail.get("textAliasSourceOptionIds"))
    pre_option_ids = _normalize_line_ids(group_detail.get("preOptionIds"))
    timeline_pre_option_ids = _normalize_line_ids(group_detail.get("timelinePreOptionIds"))

    if status == "authoredAfter":
        detail = f"{label} authored after `{after}`" if after else f"{label} authored after anchor"
    elif status == "authoredPre":
        detail = f"{label} authored before scene"
    elif status == "fallbackAfter":
        mode_labels = {
            "sparseGap": "sparse-gap fallback",
            "siblingTimelinePosition": "sibling-timeline fallback",
            "lineNumber": "line-number fallback",
            "lastLine": "last-line fallback",
        }
        fallback_label = mode_labels.get(inferred_anchor_mode, "fallback candidate")
        detail = f"{label} {fallback_label} near `{after}`" if after else f"{label} {fallback_label}"
    elif status == "unanchored":
        detail = f"{label} unanchored"
    else:
        detail = f"{label} {status}"

    extra_bits: list[str] = []
    if option_ids:
        extra_bits.append(f"options: {_summarize_items(option_ids)}")
    if tree_after_option_ids:
        extra_bits.append(f"tree-after: {_summarize_items(tree_after_option_ids)}")
    if scene_link_after_option_ids:
        extra_bits.append(f"scene-link after: {_summarize_items(scene_link_after_option_ids)}")
    if timeline_after_option_ids:
        extra_bits.append(f"timeline after: {_summarize_items(timeline_after_option_ids)}")
    if cinematic_after_option_ids:
        extra_bits.append(f"cinematic-finish after: {_summarize_items(cinematic_after_option_ids)}")
    if text_alias_after_option_ids:
        extra_bits.append(f"text-alias after: {_summarize_items(text_alias_after_option_ids)}")
    if text_alias_source_option_ids:
        extra_bits.append(f"text-alias source: {_summarize_items(text_alias_source_option_ids)}")
    if pre_option_ids:
        extra_bits.append(f"tree-pre: {_summarize_items(pre_option_ids)}")
    if timeline_pre_option_ids:
        extra_bits.append(f"timeline-pre: {_summarize_items(timeline_pre_option_ids)}")
    if text_alias_pre_option_ids:
        extra_bits.append(f"text-alias pre: {_summarize_items(text_alias_pre_option_ids)}")
    if unauthored_option_ids:
        extra_bits.append(f"no authored signal: {_summarize_items(unauthored_option_ids)}")
    if extra_bits:
        detail += " (" + "; ".join(extra_bits) + ")"
    return detail


def analyze_option_layout(conv: dict) -> dict:
    meaningful_option_count = _count_meaningful_options(conv)
    option_groups = [
        group
        for group in (conv.get("optionGroups") or [])
        if isinstance(group, dict)
    ]

    if not has_meaningful_options(conv):
        return {
            "status": "notNeeded",
            "statusLabel": "not needed",
            "reasonCode": "notNeeded",
            "reason": "not needed (no meaningful options)",
            "detail": (
                f"scene has {meaningful_option_count} meaningful option(s) across "
                f"{len(option_groups)} option group(s), so option-position analysis "
                "is not needed"
            ),
            "evidence": [],
            "warning": None,
        }

    warning = inferred_option_warning(conv)
    if warning is None:
        return {
            "status": "authored",
            "statusLabel": "authored option anchors",
            "reasonCode": "ok",
            "reason": "all option groups anchored from authored evidence",
            "detail": (
                f"all {len(option_groups)} option group(s) keep explicit authored "
                "positions in the built scene data"
            ),
            "evidence": [],
            "warning": None,
        }

    reason_code = str(warning.get("reason") or "inferredOptionLayout")
    reason = OPTION_LAYOUT_REASON_TITLES.get(reason_code, reason_code)
    detail = str(
        warning.get("detail")
        or OPTION_LAYOUT_REASON_DESCRIPTIONS.get(
            reason_code,
            "option placement inferred from fallback anchors",
        )
    )
    breakdown = warning.get("groupBreakdown") or {}
    group_details = _normalize_group_details(conv, warning)
    tree_sources = [
        str(source)
        for source in (warning.get("treeSources") or [])
        if str(source).strip()
    ]
    scene_link_sources = [
        str(source)
        for source in (warning.get("sceneLinkSources") or [])
        if str(source).strip()
    ]
    timeline_sources = [
        str(source)
        for source in (warning.get("timelineSources") or [])
        if str(source).strip()
    ]
    cinematic_sources = [
        str(source)
        for source in (warning.get("cinematicSources") or [])
        if str(source).strip()
    ]
    text_alias_sources = [
        str(source)
        for source in (warning.get("textAliasSources") or [])
        if str(source).strip()
    ]
    fallback_anchor_ids = _normalize_line_ids(warning.get("fallbackAnchorIds"))

    evidence: list[str] = [
        f"{meaningful_option_count} meaningful option(s) across {len(option_groups)} option group(s)",
    ]
    if isinstance(breakdown, dict) and breakdown:
        evidence.append(
            "group breakdown: "
            f"total={int(breakdown.get('total', len(option_groups)))}, "
            f"authoredAfter={int(breakdown.get('authoredAfter', 0))}, "
            f"authoredPre={int(breakdown.get('authoredPre', 0))}, "
            f"fallbackAfter={int(breakdown.get('fallbackAfter', 0))}, "
            f"unanchored={int(breakdown.get('unanchored', 0))}"
        )
    if tree_sources:
        evidence.append(f"authored tree sources: {_summarize_items(tree_sources, limit=4)}")
    if scene_link_sources:
        evidence.append(
            f"scene-link sources: {_summarize_items(scene_link_sources, limit=4)}"
        )
    if timeline_sources:
        evidence.append(
            f"timeline sources: {_summarize_items(timeline_sources, limit=4)}"
        )
    if cinematic_sources:
        evidence.append(
            f"cinematic-finish sources: {_summarize_items(cinematic_sources, limit=4)}"
        )
    if text_alias_sources:
        evidence.append(
            f"text-alias sources: {_summarize_items(text_alias_sources, limit=4)}"
        )
    if fallback_anchor_ids:
        evidence.append(
            f"fallback candidate anchors: {_summarize_items(fallback_anchor_ids)}"
        )

    rendered_group_details = [_render_group_detail(detail_row) for detail_row in group_details]
    for rendered in rendered_group_details[:8]:
        evidence.append(rendered)
    if len(rendered_group_details) > 8:
        evidence.append(f"+{len(rendered_group_details) - 8} more group detail(s)")

    return {
        "status": "inferred",
        "statusLabel": "inferred option placement",
        "reasonCode": reason_code,
        "reason": reason,
        "detail": detail,
        "evidence": evidence,
        "warning": warning,
    }


def classify_line_order_failure(analysis: dict) -> dict:
    status = str(analysis.get("status") or "")
    mode = str(analysis.get("mode") or "")

    if status == "direct":
        label = LINE_ORDER_PATTERN_TITLES["ok"]
        return {
            "status": "ok",
            "code": "ok",
            "label": label,
            "summary": str(analysis.get("reason") or "line order comes from authored evidence"),
            "detail": f"mode={mode or 'direct'}",
        }

    if status == "partial":
        uncovered_line_ids = _normalize_line_ids(analysis.get("uncoveredLineIds"))
        detail = (
            f"mode={mode or 'direct'}; "
            f"uncovered={len(uncovered_line_ids)}"
        )
        if uncovered_line_ids:
            detail += f"; lines={_summarize_items(uncovered_line_ids, limit=6)}"
        return {
            "status": "problem",
            "code": "partialAuthoredCoverage",
            "label": LINE_ORDER_PATTERN_TITLES["partialAuthoredCoverage"],
            "summary": LINE_ORDER_PATTERN_DESCRIPTIONS["partialAuthoredCoverage"],
            "detail": detail,
        }

    if status == "missing":
        original_ids = _normalize_line_ids(analysis.get("originalLineIds"))
        suffix_diag = _line_id_suffix_diagnostics(original_ids)
        code = (
            "missingBlockButSuffixSortable"
            if suffix_diag["usable"]
            else "missingBlockNoSafeFallback"
        )
        return {
            "status": "problem",
            "code": code,
            "label": LINE_ORDER_PATTERN_TITLES[code],
            "summary": LINE_ORDER_PATTERN_DESCRIPTIONS[code],
            "detail": (
                f"{len(original_ids)} raw line id(s) inspected; "
                f"mode={mode or 'missing'}"
            ),
        }

    if mode == "lineIdSuffix":
        code = "numericSuffixFallback"
    elif mode:
        code = "otherFallbackMode"
    else:
        code = "fallbackWithoutMode"

    detail = f"mode={mode or 'missing'}"
    return {
        "status": "problem",
        "code": code,
        "label": LINE_ORDER_PATTERN_TITLES[code],
        "summary": LINE_ORDER_PATTERN_DESCRIPTIONS[code],
        "detail": detail,
    }


def classify_option_position_failure(conv: dict, analysis: dict) -> dict:
    status = str(analysis.get("status") or "")

    if status == "notNeeded":
        label = OPTION_POSITION_PATTERN_TITLES["notNeeded"]
        return {
            "status": "notNeeded",
            "code": "notNeeded",
            "label": label,
            "summary": "scene has no meaningful options",
            "detail": "",
        }

    if status != "inferred":
        label = OPTION_POSITION_PATTERN_TITLES["ok"]
        return {
            "status": "ok",
            "code": "ok",
            "label": label,
            "summary": "positions come from authored evidence",
            "detail": "",
        }

    warning = analysis.get("warning") if isinstance(analysis.get("warning"), dict) else None
    breakdown = warning.get("groupBreakdown") if isinstance(warning, dict) else {}
    group_details = _normalize_group_details(conv, warning)
    total = _as_int(breakdown.get("total"), len(group_details))
    authored_after = _as_int(breakdown.get("authoredAfter"))
    authored_pre = _as_int(breakdown.get("authoredPre"))
    fallback_after = _as_int(breakdown.get("fallbackAfter"))
    unanchored = _as_int(breakdown.get("unanchored"))
    authored_total = authored_after + authored_pre

    if total and fallback_after == total and not authored_total and not unanchored:
        code = "syntheticAfterAllGroups"
        summary = (
            f"all {total} option group(s) lack authored positions, so the report "
            "lists fallback `after` candidates without treating them as authored"
        )
    elif authored_total and fallback_after and not unanchored:
        code = "mixedAuthoredAndSyntheticAfter"
        summary = (
            f"{authored_total} group(s) keep authored positions; {fallback_after} "
            "group(s) only have fallback `after` candidates"
        )
    elif total and unanchored == total and not authored_total and not fallback_after:
        code = "unanchoredAllGroups"
        summary = (
            f"all {total} option group(s) are missing both authored positions and "
            "usable fallback anchors"
        )
    elif fallback_after and unanchored and not authored_total:
        code = "mixedSyntheticAfterAndUnanchored"
        summary = (
            f"{fallback_after} group(s) have fallback `after` candidates; "
            f"{unanchored} group(s) remain unanchored"
        )
    elif authored_total and unanchored and not fallback_after:
        code = "mixedAuthoredAndUnanchored"
        summary = (
            f"{authored_total} group(s) keep authored positions; {unanchored} "
            "group(s) remain unanchored"
        )
    elif authored_total and fallback_after and unanchored:
        code = "mixedAuthoredFallbackAndUnanchored"
        summary = (
            f"{authored_total} group(s) keep authored positions; {fallback_after} "
            f"group(s) only have fallback `after` candidates; {unanchored} "
            "group(s) remain unanchored"
        )
    else:
        code = "genericInferredPositions"
        summary = OPTION_POSITION_PATTERN_DESCRIPTIONS[code]

    detail = (
        "groups: "
        f"authoredAfter={authored_after}, "
        f"authoredPre={authored_pre}, "
        f"fallbackAfter={fallback_after}, "
        f"unanchored={unanchored}"
    )

    return {
        "status": "problem",
        "code": code,
        "label": OPTION_POSITION_PATTERN_TITLES[code],
        "summary": summary,
        "detail": detail,
    }


def build_scene_order_disorder_warning(conv: dict) -> dict | None:
    line_order_analysis = analyze_line_order(conv)
    option_layout_analysis = analyze_option_layout(conv)
    problematic_aspects: list[str] = []
    if line_order_analysis["status"] != "direct":
        problematic_aspects.append("lineOrder")
    if option_layout_analysis["status"] == "inferred":
        problematic_aspects.append("optionLayout")
    if not problematic_aspects:
        return None

    return {
        "code": "sceneOrderDisorder",
        "problematicAspects": problematic_aspects,
        "summary": (
            "scene order relies on fallback or incomplete authored evidence"
            if len(problematic_aspects) > 1
            else (
                "line order relies on fallback or incomplete authored evidence"
                if problematic_aspects[0] == "lineOrder"
                else "option placement relies on fallback or incomplete authored evidence"
            )
        ),
        "lineOrder": {
            "status": line_order_analysis["status"],
            "statusLabel": line_order_analysis["statusLabel"],
            "reasonCode": line_order_analysis["reasonCode"],
            "summary": line_order_analysis["reason"],
            "detail": line_order_analysis["detail"],
            "evidence": line_order_analysis["evidence"],
            "mode": line_order_analysis["mode"],
            "coveredLineCount": _as_int(line_order_analysis.get("coveredLineCount")),
            "uncoveredLineCount": _as_int(line_order_analysis.get("uncoveredLineCount")),
            "coveredLineIds": _normalize_line_ids(line_order_analysis.get("coveredLineIds")),
            "uncoveredLineIds": _normalize_line_ids(line_order_analysis.get("uncoveredLineIds")),
        },
        "optionLayout": {
            "status": option_layout_analysis["status"],
            "statusLabel": option_layout_analysis["statusLabel"],
            "reasonCode": option_layout_analysis["reasonCode"],
            "summary": option_layout_analysis["reason"],
            "detail": option_layout_analysis["detail"],
            "evidence": option_layout_analysis["evidence"],
        },
    }


def collect_scene_order_gap_rows(root: Path, conv_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(conv_dir.glob("dlg_*.json")):
        try:
            conv = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        meaningful_lines = has_meaningful_lines(conv)
        meaningful_options = has_meaningful_options(conv)
        line_order_analysis = analyze_line_order(conv)
        option_layout_analysis = analyze_option_layout(conv)
        line_order_pattern = classify_line_order_failure(line_order_analysis)
        option_position_pattern = classify_option_position_failure(conv, option_layout_analysis)
        inferred_options = option_layout_analysis["status"] == "inferred"
        if line_order_analysis["status"] == "direct" and not inferred_options:
            continue

        option_groups = [
            group
            for group in (conv.get("optionGroups") or [])
            if isinstance(group, dict)
        ]
        rows.append({
            "key": conv.get("key") or path.stem,
            "mission": conv.get("mission") or "",
            "kind": conv.get("kind") or "",
            "title": ((conv.get("_debug") or {}).get("title") or {}).get("value") or "",
            "lineOrderStatus": line_order_analysis["status"],
            "lineOrderReasonCode": line_order_analysis["reasonCode"],
            "lineOrderReason": line_order_analysis["reason"],
            "lineOrderDetail": line_order_analysis["detail"],
            "lineOrderEvidence": line_order_analysis["evidence"],
            "lineOrderAnalysis": line_order_analysis,
            "lineOrderPatternCode": line_order_pattern["code"],
            "lineOrderPattern": line_order_pattern,
            "inferredOptionLayout": inferred_options,
            "optionLayoutStatus": option_layout_analysis["status"],
            "optionLayoutReason": option_layout_analysis["reasonCode"],
            "optionLayoutSummary": option_layout_analysis["reason"],
            "optionLayoutDetail": option_layout_analysis["detail"],
            "optionLayoutEvidence": option_layout_analysis["evidence"],
            "optionLayoutAnalysis": option_layout_analysis,
            "optionPositionPatternCode": option_position_pattern["code"],
            "optionPositionPattern": option_position_pattern,
            "warningCodes": [
                warning.get("code")
                for warning in (conv.get("warnings") or [])
                if isinstance(warning, dict) and warning.get("code")
            ],
            "lineCount": len(conv.get("lines") or []),
            "meaningfulLineCount": _count_meaningful_lines(conv),
            "optionGroupCount": len(option_groups),
            "optionCount": sum(
                len(group.get("options") or [])
                for group in option_groups
            ),
            "meaningfulOptionCount": _count_meaningful_options(conv),
            "hasMeaningfulLines": meaningful_lines,
            "hasMeaningfulOptions": meaningful_options,
            "path": str(path.relative_to(root)).replace("\\", "/"),
        })

    rows.sort(
        key=lambda row: (
            0 if row["lineOrderStatus"] == "missing" else 1,
            0 if row["inferredOptionLayout"] else 1,
            row["mission"],
            row["key"],
        )
    )
    return rows


def build_scene_order_gap_summary(rows: list[dict], language: str) -> dict:
    line_reason_counts: dict[str, int] = {}
    option_reason_counts: dict[str, int] = {}
    line_pattern_counts: dict[str, int] = {}
    option_pattern_counts: dict[str, int] = {}
    for row in rows:
        if row.get("lineOrderStatus") != "direct":
            reason = str(row.get("lineOrderReasonCode") or "unknown")
            line_reason_counts[reason] = line_reason_counts.get(reason, 0) + 1
            pattern = str(row.get("lineOrderPatternCode") or "unknown")
            line_pattern_counts[pattern] = line_pattern_counts.get(pattern, 0) + 1
        if row.get("inferredOptionLayout"):
            reason = str(row.get("optionLayoutReason") or "unknown")
            option_reason_counts[reason] = option_reason_counts.get(reason, 0) + 1
            pattern = str(row.get("optionPositionPatternCode") or "unknown")
            option_pattern_counts[pattern] = option_pattern_counts.get(pattern, 0) + 1
    return {
        "language": language,
        "totalFlaggedScenes": len(rows),
        "missingLineOrder": sum(1 for row in rows if row["lineOrderStatus"] == "missing"),
        "partialLineOrder": sum(1 for row in rows if row["lineOrderStatus"] == "partial"),
        "fallbackLineOrder": sum(1 for row in rows if row["lineOrderStatus"] == "fallback"),
        "inferredOptionLayout": sum(1 for row in rows if row["inferredOptionLayout"]),
        "lineOrderReasonCounts": line_reason_counts,
        "lineOrderPatternCounts": line_pattern_counts,
        "optionLayoutReasonCounts": option_reason_counts,
        "optionPositionPatternCounts": option_pattern_counts,
        "bothMissingOrderAndInferredOptions": sum(
            1
            for row in rows
            if row["lineOrderStatus"] == "missing" and row["inferredOptionLayout"]
        ),
        "bothFallbackOrderAndInferredOptions": sum(
            1
            for row in rows
            if row["lineOrderStatus"] == "fallback" and row["inferredOptionLayout"]
        ),
    }

def _describe_pattern(pattern_code: str, titles: dict[str, str], descriptions: dict[str, str]) -> str:
    label = titles.get(pattern_code, pattern_code)
    description = descriptions.get(pattern_code, "additional simplified failure pattern")
    return f"`{pattern_code}` - {label}: {description}"


def _render_pattern_cell(pattern: dict) -> str:
    status = str(pattern.get("status") or "unknown")
    code = str(pattern.get("code") or "")
    parts = [f"**{pattern.get('label') or status}**"]
    if code and code not in {"ok", "notNeeded"}:
        parts.append(f"`{code}`")
    summary = str(pattern.get("summary") or "").strip()
    detail = str(pattern.get("detail") or "").strip()
    if summary:
        parts.append(summary)
    if detail and detail != summary:
        parts.append(detail)
    return "<br>".join(_escape_table_text(part) for part in parts if part)


def render_scene_order_gap_markdown(summary: dict, rows: list[dict]) -> str:
    lines = [
        f"# Scene Order Gaps ({summary['language']})",
        "",
        "Scope: `dlg_*` conversation scenes in the built WebUI data.",
        "",
        "## Summary",
        "",
        f"- flagged scenes: `{summary['totalFlaggedScenes']}`",
        f"- missing line-order block: `{summary['missingLineOrder']}`",
        f"- partial authored line order: `{summary.get('partialLineOrder', 0)}`",
        f"- fallback line order: `{summary['fallbackLineOrder']}`",
        f"- inferred option placement: `{summary['inferredOptionLayout']}`",
        f"- missing line order + inferred option placement: `{summary['bothMissingOrderAndInferredOptions']}`",
        f"- fallback line order + inferred option placement: `{summary['bothFallbackOrderAndInferredOptions']}`",
    ]

    line_pattern_counts = summary.get("lineOrderPatternCounts") or {}
    if line_pattern_counts:
        lines.extend([
            "",
            "### Line-Order Failure Patterns",
            "",
        ])
        for pattern, count in sorted(line_pattern_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{pattern}`: `{count}`")

    option_pattern_counts = summary.get("optionPositionPatternCounts") or {}
    if option_pattern_counts:
        lines.extend([
            "",
            "### Option-Position Failure Patterns",
            "",
        ])
        for pattern, count in sorted(option_pattern_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{pattern}`: `{count}`")

    lines.extend([
        "",
        "## Pattern Guide",
        "",
        "### Line Order",
        "",
    ])
    line_pattern_docs = (
        sorted(line_pattern_counts)
        if line_pattern_counts
        else ["numericSuffixFallback", "missingBlockButSuffixSortable", "missingBlockNoSafeFallback"]
    )
    for pattern_code in line_pattern_docs:
        lines.append(
            f"- {_describe_pattern(pattern_code, LINE_ORDER_PATTERN_TITLES, LINE_ORDER_PATTERN_DESCRIPTIONS)}"
        )

    lines.extend([
        "",
        "### Option Position",
        "",
    ])
    option_pattern_docs = (
        sorted(option_pattern_counts)
        if option_pattern_counts
        else ["syntheticAfterAllGroups", "mixedAuthoredAndSyntheticAfter", "unanchoredAllGroups"]
    )
    for pattern_code in option_pattern_docs:
        lines.append(
            f"- {_describe_pattern(pattern_code, OPTION_POSITION_PATTERN_TITLES, OPTION_POSITION_PATTERN_DESCRIPTIONS)}"
        )

    lines.extend([
        "",
        "## Scenes",
        "",
        "| Scene | Mission | Line-Order Pattern | Option-Position Pattern | Lines | Opt Groups | Path |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ])

    for row in rows:
        line_cell = _render_pattern_cell(row.get("lineOrderPattern") or {})
        option_cell = _render_pattern_cell(row.get("optionPositionPattern") or {})
        lines.append(
            f"| `{row['key']}` | `{row['mission']}` | {line_cell} | {option_cell} | "
            f"{row['lineCount']} | {row['optionGroupCount']} | `{_escape_table_text(row['path'])}` |"
        )

    return "\n".join(lines)
