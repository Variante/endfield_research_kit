"""Classify authored option routes and their shared Timeline continuation.

The algorithms operate only on already-decoded route and timing values.  They
do not read files, infer dialog identities, or depend on Story build context.
"""

from __future__ import annotations


def _option_index_pattern(values: list[object]) -> str:
    ints = [value for value in values if isinstance(value, int)]
    if not ints:
        return "missing"
    if len(ints) < len(values):
        return "partialMissing"
    has_zero = any(value == 0 for value in ints)
    has_nonzero = any(value != 0 for value in ints)
    if has_zero and has_nonzero:
        return "mixedZeroNonzero"
    if has_zero:
        return "allZero"
    if has_nonzero:
        return "strictNonzero"
    return "other"


def classify_zero_index_timeline_continuation(
    option_indices: list[object],
    candidate_clip_indices: list[object],
    *,
    candidate_window_start: object,
    candidate_window_end: object,
    runtime_jump_clips: object,
) -> dict:
    """Classify an all-zero adjacent trunk window using runtime semantics.

    Native ``TryTriggerTrunkBindingOption`` selects only active trunk clips
    whose runtime option field is positive. Adjacent trunk clips whose
    serialized ``TimelineClip.optionIndex`` values are all zero are therefore
    shared continuation, not one reply per UI option. A raw Runtime Jump may
    still alter the later route; completed routes are handled by the
    higher-priority route classifier, while incomplete overlaps remain attached
    as route uncertainty instead of reviving a one-line-per-option guess.
    """
    candidate_pattern = _option_index_pattern(candidate_clip_indices)
    if candidate_pattern != "allZero" or not candidate_clip_indices:
        return {"status": "notApplicable"}
    option_pattern = _option_index_pattern(option_indices)
    if not isinstance(runtime_jump_clips, list):
        return {
            "status": "unverified",
            "reason": "runtimeJumpEvidenceMissing",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
        }
    try:
        window_start = float(candidate_window_start)
        window_end = float(candidate_window_end)
    except (TypeError, ValueError):
        return {
            "status": "unverified",
            "reason": "candidateWindowTimingMissing",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
        }
    if window_end <= window_start:
        return {
            "status": "unverified",
            "reason": "candidateWindowTimingInvalid",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
        }

    overlaps: list[dict] = []
    malformed = False
    for raw in runtime_jump_clips:
        if not isinstance(raw, dict):
            malformed = True
            continue
        try:
            clip_start = float(raw.get("start"))
            clip_end = float(
                raw.get("end")
                if raw.get("end") is not None
                else clip_start + float(raw.get("duration"))
            )
        except (TypeError, ValueError):
            malformed = True
            continue
        if clip_end > window_start + 1e-6 and clip_start < window_end - 1e-6:
            overlaps.append(raw)
    if malformed:
        return {
            "status": "blocked",
            "reason": "runtimeJumpEvidenceMalformed",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
            "overlappingRuntimeJumpClips": overlaps,
        }
    if overlaps:
        return {
            "status": "shared",
            "reason": "defaultTrunkClipContinuationWithRuntimeJump",
            "runtimeJumpRouteStatus": "overlapUnresolved",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
            "overlappingRuntimeJumpClips": overlaps,
        }
    return {
        "status": "shared",
        "reason": (
            "rawOptionIndexConverges"
            if option_pattern == "allZero"
            else "defaultTrunkClipContinuation"
        ),
        "optionIndexPattern": option_pattern,
        "candidateLineClipOptionIndexPattern": candidate_pattern,
    }


def classify_timeline_clip_option_index_routes(
    option_ids: list[str],
    option_indices: list[object],
    branch_line_ids_by_option: dict[str, list[str]],
    branch_clip_indices_by_option: dict[str, list[int]],
    line_timing_by_id: dict[str, dict],
    runtime_jump_clips: object,
    common_continuation_line_id: str,
) -> dict:
    """Validate exact nonzero Timeline option-index branch ownership.

    A selected dialog option is written into the runtime option field, and
    option-bound Timeline clips are enabled by that value. Distinct positive
    option indices therefore identify branch clips directly. Runtime Jumps in
    the same window are accepted only when they occur after that option's last
    response clip and converge forward to the shared continuation.
    """
    if (
        len(option_ids) < 2
        or len(option_ids) != len(option_indices)
        or not all(isinstance(value, int) and value > 0 for value in option_indices)
        or len(set(option_indices)) != len(option_indices)
        or not isinstance(runtime_jump_clips, list)
        or not common_continuation_line_id
    ):
        return {
            "status": "incomplete",
            "reason": "routeCardinalityOrRuntimeEvidence",
        }

    continuation_timing = line_timing_by_id.get(common_continuation_line_id) or {}
    continuation_start = continuation_timing.get("start")
    if not isinstance(continuation_start, (int, float)):
        return {"status": "incomplete", "reason": "continuationTimingMissing"}
    continuation_start = float(continuation_start)

    branch_end_by_index: dict[int, float] = {}
    branch_starts: list[float] = []
    for option_id, option_index in zip(option_ids, option_indices):
        branch_lines = branch_line_ids_by_option.get(option_id) or []
        clip_indices = branch_clip_indices_by_option.get(option_id) or []
        if (
            not branch_lines
            or len(branch_lines) != len(clip_indices)
            or any(value != option_index for value in clip_indices)
        ):
            return {"status": "incomplete", "reason": "branchClipIndexCoverage"}
        ends: list[float] = []
        for line_id in branch_lines:
            timing = line_timing_by_id.get(line_id) or {}
            start = timing.get("start")
            duration = timing.get("duration")
            if not isinstance(start, (int, float)) or not isinstance(
                duration, (int, float)
            ):
                return {"status": "incomplete", "reason": "branchTimingMissing"}
            start = float(start)
            end = start + float(duration)
            if end < start or start >= continuation_start + 1e-6:
                return {"status": "blocked", "reason": "branchTimingInvalid"}
            branch_starts.append(start)
            ends.append(end)
        branch_end_by_index[int(option_index)] = max(ends)

    branch_window_start = min(branch_starts)
    convergence_jumps: list[dict] = []
    option_index_set = {int(value) for value in option_indices}
    for raw in runtime_jump_clips:
        if not isinstance(raw, dict):
            return {"status": "blocked", "reason": "runtimeJumpEvidenceMalformed"}
        start = raw.get("start")
        end = raw.get("end")
        if end is None and isinstance(start, (int, float)) and isinstance(
            raw.get("duration"), (int, float)
        ):
            end = float(start) + float(raw["duration"])
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return {"status": "blocked", "reason": "runtimeJumpTimingMissing"}
        start = float(start)
        end = float(end)
        if end <= branch_window_start + 1e-6 or start >= continuation_start - 1e-6:
            continue
        option_index = raw.get("optionIndex")
        if (
            not isinstance(option_index, int)
            or option_index not in option_index_set
            or raw.get("isReverseJump") not in (None, 0, False)
            or raw.get("needChangeOptionAfterJump") not in (None, 0, False)
            or start + 1e-6 < branch_end_by_index[option_index]
            or end > continuation_start + 1e-6
            or end <= start
        ):
            return {
                "status": "blocked",
                "reason": "runtimeJumpDoesNotConvergeAfterBranch",
                "runtimeJump": raw,
            }
        convergence_jumps.append(raw)

    return {
        "status": "exact",
        "reason": "runtimeClipOptionIndex",
        "commonContinuationLineId": common_continuation_line_id,
        "convergenceRuntimeJumps": convergence_jumps,
    }


def classify_runtime_jump_option_routes(
    option_ids: list[str],
    routes: list[dict],
    ordered_line_ids: list[str],
    *,
    after_line_id: str = "",
) -> dict:
    """Reduce complete Runtime Jump paths to option-exclusive line spans.

    Timeline recovery deliberately keeps each option's complete path until the
    next option slot.  That path can contain a long shared suffix, while a
    route marked ``terminatesSlot`` can contain no line because it skips the
    option-response window and resumes at the shared continuation.  This
    classifier removes the common suffix and names direct-continuation options
    explicitly so callers do not require a fake response line for every
    choice.
    """
    if len(option_ids) < 2 or len(option_ids) != len(routes):
        return {"status": "incomplete", "reason": "optionRouteCardinality"}

    valid_line_ids = {
        str(line_id)
        for line_id in ordered_line_ids
        if str(line_id or "").strip()
    }
    paths: dict[str, list[str]] = {}
    terminates_slot: list[str] = []
    for option_id, route in zip(option_ids, routes):
        if not option_id or not isinstance(route, dict):
            return {"status": "incomplete", "reason": "missingOptionRoute"}
        path = []
        for raw_line_id in route.get("pathLineIds") or []:
            line_id = str(raw_line_id or "")
            if line_id in valid_line_ids and line_id not in path:
                path.append(line_id)
        if not path and not route.get("terminatesSlot"):
            return {"status": "incomplete", "reason": "emptyOptionRoute"}
        paths[option_id] = path
        if route.get("terminatesSlot"):
            terminates_slot.append(option_id)

    nonempty_paths = [path for path in paths.values() if path]
    common_suffix: list[str] = []
    if len(nonempty_paths) == len(paths):
        suffix_length = 0
        min_length = min(len(path) for path in nonempty_paths)
        while suffix_length < min_length:
            candidate = nonempty_paths[0][-suffix_length - 1]
            if not all(path[-suffix_length - 1] == candidate for path in nonempty_paths):
                break
            suffix_length += 1
        if suffix_length:
            common_suffix = nonempty_paths[0][-suffix_length:]

    exclusive_paths = {
        option_id: (path[:-len(common_suffix)] if common_suffix else list(path))
        for option_id, path in paths.items()
    }
    direct_continuation_ids = [
        option_id
        for option_id in option_ids
        if not exclusive_paths.get(option_id)
    ]
    signatures = {
        tuple(exclusive_paths.get(option_id) or [])
        for option_id in option_ids
    }
    if len(signatures) < 2:
        return {
            "status": "shared",
            "reason": "identicalRuntimeJumpPaths",
            "commonContinuationLineIds": common_suffix,
        }

    common_continuation = common_suffix[0] if common_suffix else ""
    if not common_continuation and terminates_slot:
        line_index = {
            line_id: index
            for index, line_id in enumerate(ordered_line_ids)
        }
        covered_indexes = [
            line_index[line_id]
            for path in paths.values()
            for line_id in path
            if line_id in line_index
        ]
        if covered_indexes:
            continuation_index = max(covered_indexes) + 1
        else:
            continuation_index = line_index.get(after_line_id, -1) + 1
        if 0 <= continuation_index < len(ordered_line_ids):
            common_continuation = ordered_line_ids[continuation_index]

    return {
        "status": "branched",
        "reason": "runtimeJumpExclusivePaths",
        "branchLineIdsByOption": exclusive_paths,
        "directContinuationOptionIds": direct_continuation_ids,
        "commonContinuationLineId": common_continuation,
        "commonContinuationLineIds": common_suffix,
        "terminatingOptionIds": terminates_slot,
        "fullPathLineIdsByOption": paths,
    }


__all__ = [
    "classify_runtime_jump_option_routes",
    "classify_timeline_clip_option_index_routes",
    "classify_zero_index_timeline_continuation",
]
