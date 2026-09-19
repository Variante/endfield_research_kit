from __future__ import annotations

from collections.abc import Callable


def following_line_risk_for_group(
    group_opt_ids: list[str],
    after_id: str,
    *,
    valid_line_ids: set[str],
    tree_branches: dict[str, list[str]],
    tree_converge: dict[str, str],
    timeline_option_rows: dict[str, list[dict]],
    timeline_after: dict[str, str],
    timeline_pre: set[str],
    timeline_after_line_ids: dict[str, list[str]],
    timeline_after_line_timings: dict[str, dict[str, dict]],
    timeline_after_runtime_jump_clips: dict[str, list[dict]],
    timeline_option_routes: dict[str, list[dict]],
    preferred_timeline_option_row: Callable[..., dict],
    preferred_timeline_option_route: Callable[..., dict],
    classify_zero_index_timeline_continuation: Callable[..., dict],
    classify_timeline_clip_option_index_routes: Callable[..., dict],
    unique_preserve: Callable[[list[str]], list[str]],
) -> dict:
    if len(group_opt_ids) < 2:
        return {}
    if any(
        any(
            line_id in valid_line_ids
            for line_id in (tree_branches.get(opt_id) or [])
        )
        for opt_id in group_opt_ids
    ):
        return {}
    # Dialog tree shows all options converge to the same response trunk.
    # This is complete authored route evidence on its own: every serialized
    # option edge reaches the same visible trunk.
    if all(opt_id in tree_converge for opt_id in group_opt_ids):
        trunk_ids = {tree_converge[opt_id] for opt_id in group_opt_ids}
        if len(trunk_ids) == 1:
            common_trunk = next(iter(trunk_ids))
            if common_trunk in valid_line_ids:
                return {
                    "code": "cosmeticChoice",
                    "reason": "treeSourcedConvergence",
                    "detail": (
                        "Dialog tree shows all options in this group lead to the "
                        "same response trunk; the choice affects only the player's "
                        "displayed text, not which line plays next."
                    ),
                    "after": after_id,
                    "optionIds": group_opt_ids,
                    "candidateLineIds": [],
                    "commonContinuationLineId": common_trunk,
                    "source": "dialogTree",
                }
    preferred_rows = [
        preferred_timeline_option_row(
            opt_id,
            timeline_option_rows=timeline_option_rows,
        )
        for opt_id in group_opt_ids
    ]
    option_indices = [
        row.get("optionIndex") if isinstance(row.get("optionIndex"), int) else None
        for row in preferred_rows
    ]
    option_starts = [
        float(row.get("start"))
        if isinstance(row.get("start"), (int, float))
        else None
        for row in preferred_rows
    ]
    authored_after_anchors = [
        timeline_after.get(opt_id) or "" for opt_id in group_opt_ids
    ]
    if (
        all(option_index == 0 for option_index in option_indices)
        and all(start is not None for start in option_starts)
        and len({round(start, 6) for start in option_starts}) == len(group_opt_ids)
        and all(authored_after_anchors)
        and len(set(authored_after_anchors)) == len(group_opt_ids)
    ):
        return {
            "code": "sequentialTimelineOptionPrompts",
            "reason": "distinctZeroIndexTimelineSlots",
            "detail": (
                "These option ids share a text-table group but occur in "
                "distinct authored Timeline slots, each with raw "
                "optionIndex 0 and a different preceding line. They are "
                "sequential single-option prompts, not one choice fork."
            ),
            "after": after_id,
            "optionIds": group_opt_ids,
            "candidateLineIds": [],
            "source": "dialogTimeline",
            "optionIndex": option_indices,
            "optionStartTimes": option_starts,
            "optionAnchors": authored_after_anchors,
        }
    if after_id:
        anchors = authored_after_anchors
        if not all(anchor == after_id for anchor in anchors):
            return {}
    elif not all(opt_id in timeline_pre for opt_id in group_opt_ids):
        return {}
    timeline_line_ids: list[str] = []
    timeline_line_timing_by_id: dict[str, dict] = {}
    for opt_id in group_opt_ids:
        candidate_order = timeline_after_line_ids.get(opt_id) or []
        visible_candidate_order = [
            line_id for line_id in candidate_order if line_id in valid_line_ids
        ]
        if (
            (after_id and after_id in visible_candidate_order)
            or (not after_id and visible_candidate_order)
        ):
            timeline_line_ids = visible_candidate_order
            timeline_line_timing_by_id = (
                timeline_after_line_timings.get(opt_id) or {}
            )
            break
    if not timeline_line_ids or (after_id and after_id not in timeline_line_ids):
        return {}
    after_index = timeline_line_ids.index(after_id) if after_id else -1
    candidate_line_ids = [
        line_id
        for line_id in timeline_line_ids[
            after_index + 1 : after_index + 1 + len(group_opt_ids)
        ]
        if line_id in valid_line_ids
    ]
    runtime_jump_clips = (
        timeline_after_runtime_jump_clips.get(group_opt_ids[0])
        if group_opt_ids
        else None
    )
    if not candidate_line_ids:
        positive_jumps_after_option = []
        if isinstance(runtime_jump_clips, list) and all(
            start is not None for start in option_starts
        ):
            option_start = min(option_starts)
            positive_jumps_after_option = [
                clip
                for clip in runtime_jump_clips
                if (
                    isinstance(clip, dict)
                    and isinstance(clip.get("optionIndex"), int)
                    and clip.get("optionIndex") > 0
                    and isinstance(clip.get("start"), (int, float))
                    and float(clip["start"]) >= option_start - 1e-6
                )
            ]
        if (
            after_id
            and after_index == len(timeline_line_ids) - 1
            and all(start is not None for start in option_starts)
            and len({round(start, 6) for start in option_starts}) == 1
            and isinstance(runtime_jump_clips, list)
            and not positive_jumps_after_option
            and not any(
                preferred_timeline_option_route(
                    opt_id,
                    timeline_option_routes=timeline_option_routes,
                )
                for opt_id in group_opt_ids
            )
        ):
            return {
                "code": "terminalTimelineOptionSlot",
                "reason": "afterLastLocalTimelineLine",
                "detail": (
                    "The authored option slot follows the final local "
                    "dialog line, and the decoded Timeline contains no "
                    "later local line or positive option-index Runtime "
                    "Jump. It has no intra-dialog line route; this does "
                    "not claim that an external scene cannot follow."
                ),
                "after": after_id,
                "optionIds": group_opt_ids,
                "candidateLineIds": [],
                "source": "dialogTimeline",
                "optionIndex": option_indices,
                "optionStartTimes": option_starts,
            }
        return {}
    common_continuation_id = ""
    for line_id in timeline_line_ids[
        after_index + 1 + len(group_opt_ids) :
    ]:
        if line_id in valid_line_ids:
            common_continuation_id = line_id
            break
    candidate_clip_indices = [
        (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
        for line_id in candidate_line_ids
    ]
    candidate_timing_rows = [
        timeline_line_timing_by_id.get(line_id) or {}
        for line_id in candidate_line_ids
    ]
    candidate_starts = [
        float(row.get("start"))
        for row in candidate_timing_rows
        if isinstance(row.get("start"), (int, float))
    ]
    candidate_ends = [
        float(row.get("start")) + float(row.get("duration") or 0.0)
        for row in candidate_timing_rows
        if isinstance(row.get("start"), (int, float))
    ]
    continuation_classification = classify_zero_index_timeline_continuation(
        option_indices,
        candidate_clip_indices,
        candidate_window_start=min(candidate_starts) if candidate_starts else None,
        candidate_window_end=max(candidate_ends) if candidate_ends else None,
        runtime_jump_clips=runtime_jump_clips,
    )
    if continuation_classification.get("status") == "shared":
        reason = str(
            continuation_classification.get("reason")
            or "defaultTrunkClipContinuation"
        )
        detail = (
            "The current game runtime only activates option-bound trunk "
            "clips whose runtime option field is positive. Every adjacent "
            "candidate trunk clip carries clipOptionIndex 0, and no raw "
            "Runtime Jump overlaps this window, so these lines are a shared "
            "Timeline continuation rather than per-option replies."
        )
        if reason == "rawOptionIndexConverges":
            detail = (
                "Both the UI option rows and adjacent trunk clips resolve to "
                "raw optionIndex 0. The current game runtime treats this as "
                "shared Timeline continuation rather than option-specific "
                "branch replies."
            )
        if reason == "defaultTrunkClipContinuationWithRuntimeJump":
            detail = (
                "Every adjacent candidate trunk clip carries "
                "clipOptionIndex 0, so the window is shared immediate "
                "continuation rather than one reply per option. Raw "
                "Runtime Jump clips overlap the window but do not form "
                "a complete per-option route; they remain attached as "
                "later-route uncertainty instead of being converted "
                "into adjacent reply targets."
            )
        result = {
            "code": "sharedTimelineContinuation",
            "reason": reason,
            "detail": detail,
            "after": after_id,
            **({"position": "pre"} if not after_id else {}),
            "optionIds": group_opt_ids,
            "candidateLineIds": [],
            "candidateWindowLineIds": candidate_line_ids,
            "commonContinuationLineId": candidate_line_ids[0],
            "commonContinuationLineIds": candidate_line_ids,
            "source": "dialogTimeline",
            "optionIndex": option_indices,
            "candidateLineClipOptionIndex": candidate_clip_indices,
            "optionIndexPattern": continuation_classification.get(
                "optionIndexPattern"
            ),
            "candidateLineClipOptionIndexPattern": continuation_classification.get(
                "candidateLineClipOptionIndexPattern"
            ),
        }
        if continuation_classification.get("runtimeJumpRouteStatus"):
            result["runtimeJumpRouteStatus"] = continuation_classification[
                "runtimeJumpRouteStatus"
            ]
        if continuation_classification.get("overlappingRuntimeJumpClips"):
            result["overlappingRuntimeJumpClips"] = continuation_classification[
                "overlappingRuntimeJumpClips"
            ]
        return result
    candidate_mapping = ""
    branch_line_ids_by_option: dict[str, list[str]] = {}
    branch_clip_indices_by_option: dict[str, list[int]] = {}
    if (
        len(candidate_clip_indices) == len(candidate_line_ids) == len(option_indices)
        and all(isinstance(value, int) for value in candidate_clip_indices)
        and all(isinstance(value, int) for value in option_indices)
        and len(set(candidate_clip_indices)) == len(candidate_clip_indices)
        and set(candidate_clip_indices) == set(option_indices)
    ):
        line_id_by_clip_index = {
            clip_index: line_id
            for line_id, clip_index in zip(candidate_line_ids, candidate_clip_indices)
        }
        reordered_candidate_line_ids = [
            line_id_by_clip_index.get(option_index) for option_index in option_indices
        ]
        if (
            len(reordered_candidate_line_ids) == len(candidate_line_ids)
            and all(
                line_id in valid_line_ids for line_id in reordered_candidate_line_ids
            )
        ):
            candidate_line_ids = [
                str(line_id) for line_id in reordered_candidate_line_ids
            ]
            candidate_mapping = "trunkClipOptionIndex"
            candidate_clip_indices = [
                (timeline_line_timing_by_id.get(line_id) or {}).get(
                    "clipOptionIndex"
                )
                for line_id in candidate_line_ids
            ]
            option_index_set = {
                value
                for value in option_indices
                if isinstance(value, int) and value != 0
            }
            branch_line_ids_by_index: dict[int, list[str]] = {
                value: [] for value in option_index_set
            }
            branch_clip_indices_by_index: dict[int, list[int]] = {
                value: [] for value in option_index_set
            }
            branch_window_end_index = after_index + len(candidate_line_ids)
            for index, line_id in enumerate(
                timeline_line_ids[after_index + 1 :],
                start=after_index + 1,
            ):
                if line_id not in valid_line_ids:
                    continue
                clip_index = (
                    timeline_line_timing_by_id.get(line_id) or {}
                ).get("clipOptionIndex")
                if isinstance(clip_index, int) and clip_index in option_index_set:
                    branch_line_ids_by_index.setdefault(clip_index, []).append(
                        line_id
                    )
                    branch_clip_indices_by_index.setdefault(clip_index, []).append(
                        clip_index
                    )
                    branch_window_end_index = index
                    continue
                break
            for opt_id, option_index in zip(group_opt_ids, option_indices):
                if not isinstance(option_index, int):
                    continue
                branch_lines = [
                    line_id
                    for line_id in (
                        branch_line_ids_by_index.get(option_index) or []
                    )
                    if line_id in valid_line_ids
                ]
                if not branch_lines:
                    branch_lines = [
                        line_id
                        for line_id in [line_id_by_clip_index.get(option_index)]
                        if line_id in valid_line_ids
                    ]
                if branch_lines:
                    branch_line_ids_by_option[opt_id] = branch_lines
                    branch_clip_indices_by_option[opt_id] = [
                        int(value)
                        for value in (
                            branch_clip_indices_by_index.get(option_index)
                            or [option_index]
                        )
                        if isinstance(value, int)
                    ]
            for line_id in timeline_line_ids[branch_window_end_index + 1 :]:
                if line_id in valid_line_ids:
                    common_continuation_id = line_id
                    break
    clip_route_classification = {}
    if candidate_mapping:
        clip_route_classification = classify_timeline_clip_option_index_routes(
            group_opt_ids,
            option_indices,
            branch_line_ids_by_option,
            branch_clip_indices_by_option,
            timeline_line_timing_by_id,
            runtime_jump_clips,
            common_continuation_id,
        )
    if clip_route_classification.get("status") == "exact":
        return {
            "code": "timelineClipOptionIndexBranches",
            "reason": "runtimeClipOptionIndex",
            "detail": (
                "The authored Timeline option rows use distinct positive "
                "optionIndex values, and every response trunk clip carries "
                "the matching runtime optionIndex. Any Runtime Jump inside "
                "the branch window occurs only after that option's final "
                "response clip and converges forward to the shared "
                "continuation."
            ),
            "after": after_id,
            "optionIds": group_opt_ids,
            "branchLineIdsByOption": branch_line_ids_by_option,
            "branchLineClipOptionIndexByOption": branch_clip_indices_by_option,
            "commonContinuationLineId": common_continuation_id,
            "source": "dialogTimeline",
            "optionIndex": option_indices,
            "candidateMapping": candidate_mapping,
            "candidateLineClipOptionIndex": candidate_clip_indices,
            "assetTracks": unique_preserve([
                str(row.get("assetTrack") or "")
                for row in preferred_rows
                if row.get("assetTrack")
            ]),
            "convergenceRuntimeJumps": (
                clip_route_classification.get("convergenceRuntimeJumps") or []
            ),
        }
    detail = (
        "Timeline option metadata anchors this group to a trunk line, "
        "but the option entries do not name explicit target trunk ids; "
        "the following line candidates are inferred from Timeline order."
    )
    if candidate_mapping:
        detail = (
            "Timeline option metadata anchors this group to a trunk line, "
            "but the option entries do not name explicit target trunk ids; "
            "candidate response lines and same-index branch continuations "
            "are matched to options by the raw trunk clip optionIndex values."
        )
    risk = {
        "code": "inferredFollowingLines",
        "reason": "optionTargetsMissing",
        "detail": detail,
        "after": after_id,
        "optionIds": group_opt_ids,
        "candidateLineIds": candidate_line_ids,
        "commonContinuationLineId": common_continuation_id,
        "source": "dialogTimeline",
        "optionIndex": [row.get("optionIndex") for row in preferred_rows],
        "assetTracks": unique_preserve([
            str(row.get("assetTrack") or "")
            for row in preferred_rows
            if row.get("assetTrack")
        ]),
    }
    if continuation_classification.get("status") in {"blocked", "unverified"}:
        risk["runtimeContinuationClassification"] = continuation_classification
    if candidate_mapping:
        risk["candidateMapping"] = candidate_mapping
        risk["candidateLineIdsByOption"] = {
            opt_id: branch_line_ids_by_option.get(opt_id) or [line_id]
            for opt_id, line_id in zip(group_opt_ids, candidate_line_ids)
        }
        risk["candidateLineClipOptionIndex"] = candidate_clip_indices
        if branch_line_ids_by_option:
            risk["branchLineIdsByOption"] = branch_line_ids_by_option
        if branch_clip_indices_by_option:
            risk["branchLineClipOptionIndexByOption"] = (
                branch_clip_indices_by_option
            )
    return risk


__all__ = ["following_line_risk_for_group"]
