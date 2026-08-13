from __future__ import annotations

from collections.abc import Callable


def sibling_scene_template_branch_for_group(
    group_option_ids: list[str],
    after_id: str,
    group_id: int,
    *,
    conversation_key: str,
    line_indices: list[tuple[int, str]],
    lines: list[dict],
    valid_line_ids: set[str],
    option_group_keys_by_group_and_count: dict[tuple[int, int], list[tuple[str, int]]],
    option_group_ids_by_key: dict[tuple[str, int], list[str]],
    option_signature_sequence: Callable[[list[str]], list[tuple[str, str]]],
    dialog_line_text_signature: Callable[[str], str],
    load_dialog_tree: Callable[[str], dict],
    option_text_signature: Callable[[str], str],
    sequence_similarity_at_least: Callable[[str, str, float], bool],
    unique_preserve: Callable[[list[str]], list[str]],
) -> dict:
    if not group_option_ids or len(group_option_ids) < 2:
        return {}
    local_line_ids = [
        line_id for _idx, line_id in line_indices if line_id in valid_line_ids
    ]
    if len(local_line_ids) < 3:
        return {}
    local_signature_by_line_id = {
        line_id: option_text_signature(str(line.get("text") or ""))
        for line in (lines or [])
        if (line_id := str(line.get("id") or "")) in valid_line_ids
    }
    if not local_signature_by_line_id:
        return {}
    local_option_signatures = option_signature_sequence(group_option_ids)
    if not local_option_signatures:
        return {}
    sibling_group_keys = [
        key
        for key in option_group_keys_by_group_and_count.get(
            (group_id, len(group_option_ids)),
            [],
        )
        if key[0] != conversation_key
    ]
    for sibling_scene, _sibling_group_id in sibling_group_keys:
        sibling_option_ids = (
            option_group_ids_by_key.get((sibling_scene, group_id)) or []
        )
        sibling_signatures = option_signature_sequence(sibling_option_ids)
        if not sibling_signatures:
            continue
        compatible_positions = 0
        icons_compatible = True
        for (local_text, local_icon), (sibling_text, sibling_icon) in zip(
            local_option_signatures,
            sibling_signatures,
        ):
            if local_icon and sibling_icon and local_icon != sibling_icon:
                icons_compatible = False
                break
            if (
                local_text == sibling_text
                or local_text in sibling_text
                or sibling_text in local_text
            ):
                compatible_positions += 1
            elif sequence_similarity_at_least(local_text, sibling_text, 0.92):
                compatible_positions += 1
        if not icons_compatible or compatible_positions < max(
            2,
            len(group_option_ids) - 1,
        ):
            continue
        sibling_tree = load_dialog_tree(sibling_scene) or {}
        sibling_branches = sibling_tree.get("branches") or {}
        sibling_after = sibling_tree.get("after") or {}
        if not sibling_branches:
            continue
        sibling_after_ids = [
            str(sibling_after.get(option_id) or "")
            for option_id in sibling_option_ids
            if str(sibling_after.get(option_id) or "").strip()
        ]
        if len(set(sibling_after_ids)) != 1:
            continue
        sibling_after_id = sibling_after_ids[0]
        sibling_after_text = dialog_line_text_signature(sibling_after_id)
        if not sibling_after_text:
            continue
        local_after_candidates = [
            local_line_id
            for local_line_id in local_line_ids
            if (
                local_signature_by_line_id.get(local_line_id) == sibling_after_text
                or sequence_similarity_at_least(
                    local_signature_by_line_id.get(local_line_id) or "",
                    sibling_after_text,
                    0.80,
                )
            )
        ]
        if not local_after_candidates:
            continue
        branch_line_ids_by_option: dict[str, list[str]] = {}
        sibling_line_ids_by_option: dict[str, list[str]] = {}
        used_local_line_ids: set[str] = set()
        missing_options: list[tuple[str, str, list[str]]] = []
        for local_option_id, sibling_option_id in zip(
            group_option_ids,
            sibling_option_ids,
        ):
            sibling_branch_line_ids = [
                str(line_id)
                for line_id in (sibling_branches.get(sibling_option_id) or [])
                if str(line_id or "").strip()
            ]
            if not sibling_branch_line_ids:
                branch_line_ids_by_option = {}
                break
            mapped_line_ids: list[str] = []
            for sibling_line_id in sibling_branch_line_ids:
                sibling_signature = dialog_line_text_signature(sibling_line_id)
                if not sibling_signature:
                    mapped_line_ids = []
                    break
                matches = [
                    local_line_id
                    for local_line_id in local_line_ids
                    if local_line_id not in used_local_line_ids
                    and local_signature_by_line_id.get(local_line_id)
                    == sibling_signature
                ]
                if len(matches) != 1:
                    mapped_line_ids = []
                    break
                mapped_line_id = matches[0]
                used_local_line_ids.add(mapped_line_id)
                mapped_line_ids.append(mapped_line_id)
            if mapped_line_ids:
                branch_line_ids_by_option[local_option_id] = mapped_line_ids
                sibling_line_ids_by_option[local_option_id] = (
                    sibling_branch_line_ids
                )
            else:
                missing_options.append(
                    (local_option_id, sibling_option_id, sibling_branch_line_ids)
                )
        if not branch_line_ids_by_option or len(missing_options) > 1:
            continue
        mapped_indices = [
            local_line_ids.index(line_id)
            for mapped_lines in branch_line_ids_by_option.values()
            for line_id in mapped_lines
            if line_id in local_line_ids
        ]
        if not mapped_indices:
            continue
        earliest_mapped_index = min(mapped_indices)
        local_after_id = ""
        for candidate in reversed(local_after_candidates):
            candidate_index = local_line_ids.index(candidate)
            if candidate_index < earliest_mapped_index:
                local_after_id = candidate
                break
        if not local_after_id:
            continue
        after_index = local_line_ids.index(local_after_id)
        if (
            after_id
            and after_id in local_line_ids
            and local_line_ids.index(after_id) > after_index
        ):
            continue
        if missing_options:
            local_option_id, sibling_option_id, sibling_branch_line_ids = (
                missing_options[0]
            )
            inferred_lines = [
                line_id
                for line_id in local_line_ids[
                    after_index + 1 : earliest_mapped_index
                ]
                if line_id not in used_local_line_ids
            ]
            if not inferred_lines:
                continue
            branch_line_ids_by_option[local_option_id] = inferred_lines
            sibling_line_ids_by_option[local_option_id] = sibling_branch_line_ids
        if len(branch_line_ids_by_option) != len(group_option_ids):
            continue
        if len({tuple(line_ids) for line_ids in branch_line_ids_by_option.values()}) < 2:
            continue
        sibling_option_ids_by_option = {
            local_option_id: sibling_option_id
            for local_option_id, sibling_option_id in zip(
                group_option_ids,
                sibling_option_ids,
            )
        }
        source_bits = unique_preserve([
            str(value)
            for value in (
                sibling_scene,
                sibling_tree.get("sourceKey") or "",
                sibling_tree.get("file") or "",
            )
            if str(value or "").strip()
        ])
        return {
            "code": "siblingSceneTextBranches",
            "reason": "siblingSceneTemplate",
            "detail": (
                "A sibling scene has authored SceneGraph option branches "
                "with matching option layout and repeated local branch text; "
                "unmatched local lines between the sibling-matched anchor and "
                "the first matched branch are assigned to the remaining option."
            ),
            "after": local_after_id,
            "previousAfter": after_id,
            "optionIds": group_option_ids,
            "branchLineIdsByOption": branch_line_ids_by_option,
            "siblingScene": sibling_scene,
            "siblingOptionIdsByOption": sibling_option_ids_by_option,
            "siblingBranchLineIdsByOption": sibling_line_ids_by_option,
            "source": "siblingSceneGraphText",
            "sources": source_bits,
        }
    return {}


__all__ = ["sibling_scene_template_branch_for_group"]
