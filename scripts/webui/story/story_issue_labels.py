"""Derive compact Story issue labels from generated dialog evidence.

The classifiers are pure projections of one conversation payload.  They do not
read overrides or Story files and never infer new recovery evidence.
"""

from __future__ import annotations

def dialog_story_issue_codes(payload: dict) -> list[str]:
    codes: list[str] = []
    debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
    runtime_registry = (
        debug.get("runtimeRegistry")
        if isinstance(debug.get("runtimeRegistry"), dict)
        else {}
    )
    is_unregistered_scene = runtime_registry.get("registered") is False
    warning = next(
        (
            item
            for item in (payload.get("warnings") or [])
            if isinstance(item, dict) and item.get("code") == "sceneOrderDisorder"
        ),
        None,
    )
    if isinstance(warning, dict):
        line_order = warning.get("lineOrder") if isinstance(warning.get("lineOrder"), dict) else {}
        option_layout = warning.get("optionLayout") if isinstance(warning.get("optionLayout"), dict) else {}
        problematic_aspects = {
            str(aspect)
            for aspect in (warning.get("problematicAspects") or [])
            if str(aspect)
        }

        line_order_status = str(line_order.get("status") or "")
        if "lineOrder" in problematic_aspects:
            if line_order_status == "missing":
                codes.append("missingLineOrder")
            elif line_order_status == "fallback":
                codes.append("fallbackLineOrder")
            if int(line_order.get("uncoveredLineCount") or 0) > 0:
                codes.append("uncoveredLines")
        if str(option_layout.get("status") or "") == "inferred":
            layout_warning = next(
                (
                    item
                    for item in (payload.get("warnings") or [])
                    if isinstance(item, dict) and item.get("code") == "inferredOptionLayout"
                ),
                None,
            )
            group_details = (
                layout_warning.get("groupDetails")
                if isinstance(layout_warning, dict)
                and isinstance(layout_warning.get("groupDetails"), list)
                else []
            )
            modes = {
                str(detail.get("inferredAnchorMode") or "")
                for detail in group_details
                if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
            }
            statuses = {
                str(detail.get("status") or "")
                for detail in group_details
                if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
            }
            if is_unregistered_scene:
                # A DialogOptionTable row can survive without any executable
                # DialogIdTable root. Its suffix/gap still provides a useful
                # display placement, but there is no live runtime layout to
                # recover or validate. Keep this queue separate from active
                # key/gap placement work.
                codes.append("tableOnlyOptionLayout")
            else:
                if "lineNumber" in modes:
                    codes.append("keyedOptionLayout")
                if modes.intersection({"sparseGap", "siblingTimelinePosition"}):
                    codes.append("gapOptionLayout")
                if "lastLine" in modes:
                    codes.append("lastLineOptionLayout")
                if "unanchored" in statuses or any(
                    isinstance(detail, dict)
                    and not detail.get("manualLayoutOverride")
                    and not (detail.get("after") or detail.get("position"))
                    for detail in group_details
                ):
                    codes.append("unanchoredOptionLayout")
            # Older payloads did not expose per-group placement modes. Keep a
            # compatibility issue only for those files instead of incorrectly
            # calling every recovered table-key anchor "missing".
            if not group_details and not is_unregistered_scene:
                codes.append("inferredOptionLayout")
    if any(
        isinstance(item, dict) and item.get("code") == "duplicateTimestamps"
        for item in (payload.get("warnings") or [])
    ):
        codes.append("duplicateTimestamps")
    if any(
        isinstance(item, dict) and item.get("code") == "timelineTimestampRegression"
        for item in (payload.get("warnings") or [])
    ):
        codes.append("timelineTimestampRegression")
    if any(
        isinstance(item, dict) and item.get("code") == "inferredOptionResponse"
        for item in (payload.get("warnings") or [])
    ):
        codes.append("inferredOptionResponse")
    if _has_manual_option_override(payload):
        codes.append("overrided")
    return codes

def dialog_option_issue_targets(payload: dict) -> dict:
    """Return compact per-issue targets for runtime WebUI override coverage.

    Option overrides intentionally stay outside generated conversation JSON so
    they can be edited without rebuilding Story data.  The index still needs
    to say which generated groups/options each issue covers; otherwise the
    frontend can only detect that a scene has *some* override and cannot tell a
    complete correction from a partial one.
    """
    warnings = [
        warning
        for warning in (payload.get("warnings") or [])
        if isinstance(warning, dict)
    ]
    layout_warning = next(
        (warning for warning in warnings if warning.get("code") == "inferredOptionLayout"),
        None,
    )
    response_warning = next(
        (warning for warning in warnings if warning.get("code") == "inferredOptionResponse"),
        None,
    )
    issue_codes = set(dialog_story_issue_codes(payload))
    out: dict[str, object] = {}

    if isinstance(layout_warning, dict):
        details = [
            detail
            for detail in (layout_warning.get("groupDetails") or [])
            if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
        ]
        if not details and "inferredOptionLayout" in issue_codes:
            details = [
                {"group": group.get("g")}
                for group in (payload.get("optionGroups") or [])
                if isinstance(group, dict) and group.get("g") is not None
            ]

        def groups_matching(predicate) -> list[str]:
            values: list[str] = []
            for detail in details:
                if not predicate(detail) or detail.get("group") is None:
                    continue
                group_id = str(detail.get("group"))
                if group_id and group_id not in values:
                    values.append(group_id)
            return values

        layout_targets: dict[str, list[str]] = {}
        if "tableOnlyOptionLayout" in issue_codes:
            layout_targets["tableOnlyOptionLayout"] = groups_matching(lambda _detail: True)
        if "keyedOptionLayout" in issue_codes:
            layout_targets["keyedOptionLayout"] = groups_matching(
                lambda detail: str(detail.get("inferredAnchorMode") or "") == "lineNumber"
            )
        if "gapOptionLayout" in issue_codes:
            layout_targets["gapOptionLayout"] = groups_matching(
                lambda detail: str(detail.get("inferredAnchorMode") or "")
                in {"sparseGap", "siblingTimelinePosition"}
            )
        if "lastLineOptionLayout" in issue_codes:
            layout_targets["lastLineOptionLayout"] = groups_matching(
                lambda detail: str(detail.get("inferredAnchorMode") or "") == "lastLine"
            )
        if "unanchoredOptionLayout" in issue_codes:
            layout_targets["unanchoredOptionLayout"] = groups_matching(
                lambda detail: (
                    str(detail.get("status") or "") == "unanchored"
                    or not (detail.get("after") or detail.get("position"))
                )
            )
        if "inferredOptionLayout" in issue_codes:
            layout_targets["inferredOptionLayout"] = groups_matching(lambda _detail: True)
        layout_targets = {
            code: group_ids
            for code, group_ids in layout_targets.items()
            if group_ids
        }
        if layout_targets:
            out["layoutGroupsByCode"] = layout_targets

    if isinstance(response_warning, dict) and "inferredOptionResponse" in issue_codes:
        option_ids: list[str] = []
        raw_option_ids = list(response_warning.get("optionIds") or [])
        if not raw_option_ids:
            raw_option_ids = [
                option_id
                for group in (response_warning.get("groups") or [])
                if isinstance(group, dict)
                for option_id in (group.get("optionIds") or [])
            ]
        for raw_option_id in raw_option_ids:
            option_id = str(raw_option_id or "")
            if option_id and option_id not in option_ids:
                option_ids.append(option_id)
        if option_ids:
            out["responseOptionIds"] = option_ids

    return out

def _has_manual_option_override(payload: dict) -> bool:
    for group in (payload.get("optionGroups") or []):
        if not isinstance(group, dict):
            continue
        if isinstance(group.get("manualOverride"), dict) and group.get("manualOverride"):
            return True
        for option in (group.get("options") or []):
            if isinstance(option, dict) and isinstance(option.get("manualOverride"), dict) and option.get("manualOverride"):
                return True
    for warning in (payload.get("warnings") or []):
        if not isinstance(warning, dict):
            continue
        if isinstance(warning.get("manualOverride"), dict) and warning.get("manualOverride"):
            return True
        for detail in (warning.get("groupDetails") or []):
            if isinstance(detail, dict) and isinstance(detail.get("manualOverride"), dict) and detail.get("manualOverride"):
                return True
        for group in (warning.get("groups") or []):
            if isinstance(group, dict) and isinstance(group.get("manualOverride"), dict) and group.get("manualOverride"):
                return True
    return False

__all__ = [
    "dialog_option_issue_targets",
    "dialog_story_issue_codes",
]
