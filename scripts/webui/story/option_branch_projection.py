from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable


def option_risk_line_ids(
    following_line_risk: dict,
    option_count: int,
    *,
    valid_line_ids: set[str],
) -> list[str]:
    option_ids = [
        str(option_id)
        for option_id in (following_line_risk.get("optionIds") or [])
        if str(option_id or "").strip()
    ]
    candidate_lines_by_option = following_line_risk.get("candidateLineIdsByOption")
    if isinstance(candidate_lines_by_option, dict) and len(option_ids) == option_count:
        mapped_line_ids: list[str] = []
        for option_id in option_ids:
            mapped_value = candidate_lines_by_option.get(option_id)
            if isinstance(mapped_value, list):
                line_id = next(
                    (
                        str(value)
                        for value in mapped_value
                        if str(value or "") in valid_line_ids
                    ),
                    "",
                )
            else:
                line_id = str(mapped_value or "")
            if line_id not in valid_line_ids:
                break
            mapped_line_ids.append(line_id)
        if len(mapped_line_ids) == option_count:
            return mapped_line_ids
    candidate_line_ids = [
        str(line_id)
        for line_id in (following_line_risk.get("candidateLineIds") or [])
        if line_id in valid_line_ids
    ]
    if len(candidate_line_ids) == option_count:
        return candidate_line_ids
    common_line_id = str(following_line_risk.get("commonContinuationLineId") or "")
    if common_line_id in valid_line_ids:
        return [common_line_id for _ in range(option_count)]
    return []


def all_option_response_risk_line_ids(
    following_line_risk: dict,
    *,
    valid_line_ids: set[str],
) -> list[str]:
    out: list[str] = []

    def push(line_id: object) -> None:
        value = str(line_id or "")
        if value and value in valid_line_ids and value not in out:
            out.append(value)

    for line_id in following_line_risk.get("candidateLineIds") or []:
        push(line_id)
    branch_lines_by_option = following_line_risk.get("branchLineIdsByOption")
    if isinstance(branch_lines_by_option, dict):
        for line_ids in branch_lines_by_option.values():
            if isinstance(line_ids, list):
                for line_id in line_ids:
                    push(line_id)
            else:
                push(line_ids)
    return out


def collect_local_scene_link_options(
    scene_links: Iterable[dict],
    *,
    valid_line_ids: set[str],
) -> dict[str, list[dict]]:
    options_by_after: dict[str, list[dict]] = defaultdict(list)
    seen_options: set[tuple[str, str, tuple[str, ...]]] = set()
    for link in scene_links:
        after_id = str(link.get("after") or "")
        if after_id not in valid_line_ids:
            continue
        for option in link.get("options") or []:
            if not isinstance(option, dict):
                continue
            path_line_ids = tuple(
                str(line_id)
                for line_id in (option.get("pathLineIds") or [])
                if str(line_id or "") in valid_line_ids
            )
            if not path_line_ids:
                continue
            option_id = str(option.get("optionId") or "")
            identity = (after_id, option_id, path_line_ids)
            if identity in seen_options:
                continue
            seen_options.add(identity)
            options_by_after[after_id].append(option)
    return options_by_after


def hidden_single_option_path_after(
    after_id: str,
    *,
    local_scene_link_options_by_after: dict[str, list[dict]],
    conversation_key: str,
    valid_line_ids: set[str],
    dialog_option_signature_by_id: dict[str, tuple[str, str]],
    dialog_tree_option_prefix: Callable[[str], str],
) -> tuple[str, list[str]]:
    options_after = [
        option
        for option in local_scene_link_options_by_after.get(after_id, [])
        if dialog_tree_option_prefix(str(option.get("optionId") or ""))
        == conversation_key
    ]
    if len(options_after) != 1:
        return "", []
    option = options_after[0]
    option_id = str(option.get("optionId") or "")
    text_value, _icon_value = dialog_option_signature_by_id.get(option_id, ("", ""))
    if not option_id or text_value:
        return "", []
    path_line_ids = [
        str(line_id)
        for line_id in (option.get("pathLineIds") or [])
        if str(line_id or "") in valid_line_ids
    ]
    return option_id, path_line_ids


def expand_transparent_single_option_branch(
    branch_lines: list[str],
    *,
    valid_line_ids: set[str],
    rendered_ordered_line_ids: list[str],
    rendered_line_order_index: dict[str, int],
    local_scene_link_options_by_after: dict[str, list[dict]],
    conversation_key: str,
    dialog_option_signature_by_id: dict[str, tuple[str, str]],
    dialog_tree_option_prefix: Callable[[str], str],
) -> list[str]:
    expanded: list[str] = []
    expanded_after_ids: set[str] = set()

    def append_line(line_id: str) -> None:
        if line_id in valid_line_ids and line_id not in expanded:
            expanded.append(line_id)

    for line_id in branch_lines:
        append_line(line_id)
    while expanded:
        after_id = expanded[-1]
        if after_id in expanded_after_ids:
            break
        expanded_after_ids.add(after_id)
        _option_id, next_path = hidden_single_option_path_after(
            after_id,
            local_scene_link_options_by_after=local_scene_link_options_by_after,
            conversation_key=conversation_key,
            valid_line_ids=valid_line_ids,
            dialog_option_signature_by_id=dialog_option_signature_by_id,
            dialog_tree_option_prefix=dialog_tree_option_prefix,
        )
        if not next_path:
            break
        first_next = next_path[0]
        start_index = rendered_line_order_index.get(after_id)
        end_index = rendered_line_order_index.get(first_next)
        if start_index is not None and end_index is not None and start_index < end_index:
            for line_id in rendered_ordered_line_ids[start_index + 1 : end_index]:
                append_line(line_id)
        before_count = len(expanded)
        for line_id in next_path:
            append_line(line_id)
        if len(expanded) == before_count:
            break
    return expanded


def normalize_group_branch_convergence(
    group: dict,
    options: list[dict],
    group_option_ids: list[str],
    *,
    valid_line_ids: set[str],
) -> dict:
    if len(options) < 2 or len(group_option_ids) != len(options):
        return {}
    paths: list[list[str]] = []
    for option in options:
        branch_lines = [
            str(line_id)
            for line_id in (option.get("branchLines") or [])
            if str(line_id or "") in valid_line_ids
        ]
        if not branch_lines:
            return {}
        paths.append(branch_lines)
    min_length = min(len(path) for path in paths)
    suffix_length = 0
    while suffix_length < min_length:
        candidate = paths[0][len(paths[0]) - suffix_length - 1]
        if not all(
            path[len(path) - suffix_length - 1] == candidate for path in paths
        ):
            break
        suffix_length += 1
    if suffix_length <= 0:
        return {}
    if any(len(path) <= suffix_length for path in paths):
        return {}
    common_suffix = paths[0][len(paths[0]) - suffix_length :]
    branch_line_ids_by_option: dict[str, list[str]] = {}
    for option, option_id, path in zip(options, group_option_ids, paths):
        branch_specific_lines = path[: len(path) - suffix_length]
        if not branch_specific_lines:
            return {}
        option["branchLines"] = branch_specific_lines
        branch_line_ids_by_option[option_id] = branch_specific_lines
        option.setdefault("_debug", {})["branchConvergence"] = {
            "mode": "commonSuffix",
            "commonLineIds": common_suffix,
        }
    return {
        "code": "dialogTreeBranchConvergence",
        "reason": "commonBranchSuffix",
        "detail": (
            "Authored same-scene branch paths share a trailing line sequence; "
            "branchLines are trimmed to branch-specific lines and rendered as "
            "converging at the shared continuation."
        ),
        "after": group.get("after") or "",
        "optionIds": group_option_ids,
        "branchLineIdsByOption": branch_line_ids_by_option,
        "commonContinuationLineId": common_suffix[0],
        "commonContinuationLineIds": common_suffix,
        "source": "dialogTree",
    }


__all__ = [
    "all_option_response_risk_line_ids",
    "collect_local_scene_link_options",
    "expand_transparent_single_option_branch",
    "normalize_group_branch_convergence",
    "option_risk_line_ids",
]
