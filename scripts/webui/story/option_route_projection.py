from __future__ import annotations

from collections.abc import Callable


def dialog_tree_option_prompt_sequence(
    group_option_ids: list[str],
    layouts_by_option: dict[str, list[dict]],
) -> list[str]:
    """Order separate option nodes by exact reachability from the tree prime."""
    return sorted(
        group_option_ids,
        key=lambda option_id: min(
            (
                int(layout["distanceFromPrime"])
                for layout in layouts_by_option.get(option_id, [])
                if layout.get("reachableFromPrime")
                and isinstance(layout.get("distanceFromPrime"), int)
            ),
            default=10**9,
        ),
    )


def dialog_tree_option_nodes_form_sequence(
    prompt_sequence: list[str],
    layouts_by_option: dict[str, list[dict]],
) -> bool:
    """Require each separate option node to reach the next authored prompt."""
    if len(prompt_sequence) < 2:
        return False
    for source_option_id, target_option_id in zip(
        prompt_sequence,
        prompt_sequence[1:],
    ):
        source_layouts = layouts_by_option.get(source_option_id, [])
        target_layouts = layouts_by_option.get(target_option_id, [])
        if not any(
            str(target_layout.get("nodeId") or "")
            in {
                str(node_id)
                for node_id in (source_layout.get("reachableNodeIds") or [])
            }
            for source_layout in source_layouts
            for target_layout in target_layouts
            if (
                source_layout.get("sourceKey") == target_layout.get("sourceKey")
                and source_layout.get("file") == target_layout.get("file")
            )
        ):
            return False
    return True


def preferred_timeline_option_row(
    option_id: str,
    *,
    timeline_option_rows: dict[str, list[dict]],
) -> dict:
    rows = timeline_option_rows.get(option_id) or []
    if not rows:
        return {}
    return min(
        rows,
        key=lambda row: (
            0 if row.get("anchorMode") == "trunkBinding" else 1,
            float(row.get("start") or 0.0),
            row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
            row.get("assetTrack") or "",
        ),
    )


def preferred_timeline_option_route(
    option_id: str,
    *,
    timeline_option_routes: dict[str, list[dict]],
) -> dict:
    routes = timeline_option_routes.get(option_id) or []
    if not routes:
        return {}
    return max(
        routes,
        key=lambda route: (
            len(route.get("pathLineIds") or []),
            -float(route.get("start") or 0.0),
            str(route.get("source") or ""),
        ),
    )


def dialog_tree_option_node_layout_for_group(
    group_option_ids: list[str],
    after_id: str,
    *,
    tree_option_node_layouts: dict[str, list[dict]],
) -> dict:
    if len(group_option_ids) < 2:
        return {}
    layouts_by_option = {
        option_id: [
            layout
            for layout in (tree_option_node_layouts.get(option_id) or [])
            if isinstance(layout, dict) and layout.get("nodeId") is not None
        ]
        for option_id in group_option_ids
    }
    if any(not layouts_by_option.get(option_id) for option_id in group_option_ids):
        return {}
    node_ids_by_option = {
        option_id: {
            (
                str(layout.get("sourceKey") or ""),
                str(layout.get("file") or ""),
                str(layout.get("nodeId") or ""),
            )
            for layout in layouts
        }
        for option_id, layouts in layouts_by_option.items()
    }
    shared_node_ids = set.intersection(*node_ids_by_option.values())
    if not shared_node_ids:
        prompt_sequence = dialog_tree_option_prompt_sequence(
            group_option_ids,
            layouts_by_option,
        )
        is_prompt_sequence = dialog_tree_option_nodes_form_sequence(
            prompt_sequence,
            layouts_by_option,
        )
        return {
            "code": (
                "sequentialDialogTreeOptionNodes"
                if is_prompt_sequence
                else "separateDialogTreeOptionNodes"
            ),
            "reason": (
                "reachableAuthoredOptionNodeSequence"
                if is_prompt_sequence
                else "distinctAuthoredOptionNodes"
            ),
            "detail": (
                "The same-prefix table ids are authored on distinct "
                "DialogTree option nodes connected by a directed path. "
                "They are consecutive single-option prompts, not arms "
                "of one runtime choice fork."
                if is_prompt_sequence
                else "The same-prefix table ids are authored on distinct "
                "DialogTree option nodes without a complete directed "
                "prompt chain. They are not proven arms of one runtime "
                "choice fork or one sequential prompt list."
            ),
            "after": after_id,
            "optionIds": group_option_ids,
            "source": "dialogTree",
            "promptSequenceOptionIds": prompt_sequence,
            "optionNodeLayouts": layouts_by_option,
        }
    shared_layouts = [
        layout
        for layouts in layouts_by_option.values()
        for layout in layouts
        if (
            str(layout.get("sourceKey") or ""),
            str(layout.get("file") or ""),
            str(layout.get("nodeId") or ""),
        )
        in shared_node_ids
    ]
    if shared_layouts and all(
        not layout.get("outgoingNodeIds") for layout in shared_layouts
    ):
        return {
            "code": "orphanDialogTreeOptionDefinitions",
            "reason": "optionNodeHasNoOutgoingConnection",
            "detail": (
                "The registered DialogTree serializes these option ids "
                "on a disconnected option node with no outgoing "
                "connection. The rows are authored definitions but do "
                "not form a playable route in this tree."
            ),
            "after": after_id,
            "optionIds": group_option_ids,
            "source": "dialogTree",
            "optionNodeLayouts": layouts_by_option,
        }
    return {}


def timeline_route_branch_for_group(
    group_option_ids: list[str],
    after_id: str,
    *,
    valid_line_ids: set[str],
    tree_branches: dict[str, list[str]],
    timeline_after: dict[str, str],
    timeline_pre: set[str],
    timeline_option_routes: dict[str, list[dict]],
    local_ordered_line_ids: list[str],
    classify_runtime_jump_option_routes: Callable[..., dict],
    unique_preserve: Callable[[list[str]], list[str]],
) -> dict:
    if len(group_option_ids) < 2:
        return {}
    if any(
        any(line_id in valid_line_ids for line_id in (tree_branches.get(option_id) or []))
        for option_id in group_option_ids
    ):
        return {}
    if after_id:
        anchors = [timeline_after.get(option_id) or "" for option_id in group_option_ids]
        if not all(anchor == after_id for anchor in anchors):
            return {}
    elif not all(option_id in timeline_pre for option_id in group_option_ids):
        return {}
    routes = [
        preferred_timeline_option_route(
            option_id,
            timeline_option_routes=timeline_option_routes,
        )
        for option_id in group_option_ids
    ]
    # A route is acceptable when either it lists per-option lines OR it flags
    # ``terminatesSlot``: the latter means the option's Runtime Jump skip
    # range covers the whole post-anchor window so no in-slot lines play.
    if not all(route.get("pathLineIds") or route.get("terminatesSlot") for route in routes):
        return {}
    route_classification = classify_runtime_jump_option_routes(
        group_option_ids,
        routes,
        local_ordered_line_ids,
        after_line_id=after_id,
    )
    if route_classification.get("status") != "branched":
        return {}
    branch_line_ids_by_option = route_classification["branchLineIdsByOption"]
    skipped_line_ids_by_option: dict[str, list[str]] = {}
    reverse_range_line_ids_by_option: dict[str, list[str]] = {}
    for option_id, route in zip(group_option_ids, routes):
        skipped_line_ids_by_option[option_id] = [
            str(line_id)
            for line_id in (route.get("skippedLineIds") or [])
            if line_id in valid_line_ids
        ]
        reverse_range_line_ids_by_option[option_id] = [
            str(line_id)
            for line_id in (route.get("reverseRangeLineIds") or [])
            if line_id in valid_line_ids
        ]
    continuation_option_ids = unique_preserve([
        str(option_id)
        for route in routes
        for option_id in (route.get("continuationOptionIds") or [])
        if str(option_id or "").strip()
    ])
    payload = {
        "code": "timelineRouteBranches",
        "reason": "runtimeJumpTrack",
        "detail": (
            "Runtime Jump Track clips in the dialog Timeline mark "
            "which time ranges each selected optionIndex skips or "
            "re-enters; branch lines are recovered from those "
            "directional route windows."
        ),
        "after": after_id,
        "optionIds": group_option_ids,
        "branchLineIdsByOption": branch_line_ids_by_option,
        "skippedLineIdsByOption": skipped_line_ids_by_option,
        "reverseRangeLineIdsByOption": {
            option_id: line_ids
            for option_id, line_ids in reverse_range_line_ids_by_option.items()
            if line_ids
        },
        "directContinuationOptionIds": route_classification.get(
            "directContinuationOptionIds"
        ) or [],
        "commonContinuationLineId": route_classification.get(
            "commonContinuationLineId"
        ) or "",
        "commonContinuationLineIds": route_classification.get(
            "commonContinuationLineIds"
        ) or [],
        "continuationOptionIds": continuation_option_ids,
        "source": "dialogTimeline",
        "optionIndex": [route.get("optionIndex") for route in routes],
        "assetTracks": unique_preserve([
            str(raw_range.get("track") or raw_range.get("assetTrack") or "")
            for route in routes
            for raw_range in (
                (route.get("skipRanges") or []) + (route.get("reverseRanges") or [])
            )
            if str(raw_range.get("track") or raw_range.get("assetTrack") or "").strip()
        ]),
    }
    terminating_option_ids = route_classification.get("terminatingOptionIds") or []
    if terminating_option_ids:
        payload["terminatingOptionIds"] = terminating_option_ids
    return payload


__all__ = [
    "dialog_tree_option_node_layout_for_group",
    "dialog_tree_option_nodes_form_sequence",
    "dialog_tree_option_prompt_sequence",
    "preferred_timeline_option_route",
    "preferred_timeline_option_row",
    "timeline_route_branch_for_group",
]
