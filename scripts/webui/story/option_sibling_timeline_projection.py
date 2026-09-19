from __future__ import annotations

from collections.abc import Callable


def option_signature_sequence(
    option_ids: list[str],
    *,
    option_signatures_by_id: dict[str, tuple[str, str]],
) -> list[tuple[str, str]]:
    signatures: list[tuple[str, str]] = []
    for option_id in option_ids:
        signature = option_signatures_by_id.get(option_id)
        if not signature or not signature[0]:
            return []
        signatures.append(signature)
    return signatures


def option_signatures_compatible(
    left_ids: list[str],
    right_ids: list[str],
    *,
    option_signatures_by_id: dict[str, tuple[str, str]],
    sequence_similarity_at_least: Callable[[str, str, float], bool],
) -> bool:
    if len(left_ids) != len(right_ids) or not left_ids:
        return False
    for left_id, right_id in zip(left_ids, right_ids):
        left_text, left_icon = option_signatures_by_id.get(left_id, ("", ""))
        right_text, right_icon = option_signatures_by_id.get(right_id, ("", ""))
        if not left_text or not right_text:
            return False
        if left_icon and right_icon and left_icon != right_icon:
            return False
        if left_text == right_text:
            continue
        if left_text in right_text or right_text in left_text:
            continue
        if not sequence_similarity_at_least(left_text, right_text, 0.92):
            return False
    return True


def dialog_line_text_signature(
    line_id: str,
    *,
    dialog_rows: dict[str, dict],
    translate: Callable[[object], str],
    option_text_signature: Callable[[str], str],
) -> str:
    row = dialog_rows.get(line_id)
    if not isinstance(row, dict):
        return ""
    text_value = translate((row.get("dialogText") or {}).get("id"))
    return option_text_signature(text_value)


def sibling_scene_text_branch_for_group(
    group_option_ids: list[str],
    after_id: str,
    sibling_anchor_record: dict | None,
    group_id: int,
    *,
    conversation_key: str,
    line_indices: list[tuple[int, str]],
    valid_line_ids: set[str],
    lines: list[dict] | None,
    option_group_ids_by_key: dict[tuple[str, int], list[str]],
    option_signatures_by_id: dict[str, tuple[str, str]],
    dialog_rows: dict[str, dict],
    translate: Callable[[object], str],
    load_dialog_tree: Callable[[str], dict],
    option_text_signature: Callable[[str], str],
    sequence_similarity_at_least: Callable[[str, str, float], bool],
    unique_preserve: Callable[[list[str]], list[str]],
) -> dict:
    if (
        not group_option_ids
        or len(group_option_ids) < 2
        or not after_id
        or not sibling_anchor_record
    ):
        return {}
    sibling_scenes = [
        str(scene_key)
        for scene_key in (sibling_anchor_record.get("siblingScenes") or [])
        if str(scene_key or "").strip() and str(scene_key) != conversation_key
    ]
    if not sibling_scenes:
        return {}
    local_line_ids = [
        line_id for _index, line_id in line_indices if line_id in valid_line_ids
    ]
    if after_id in local_line_ids:
        local_candidate_line_ids = local_line_ids[local_line_ids.index(after_id) + 1 :]
    else:
        local_candidate_line_ids = local_line_ids
    if not local_candidate_line_ids:
        return {}
    local_signature_by_line_id = {
        line_id: option_text_signature(str(line.get("text") or ""))
        for line in (lines or [])
        if (line_id := str(line.get("id") or "")) in valid_line_ids
    }
    if not local_signature_by_line_id:
        return {}
    for sibling_scene in sibling_scenes:
        sibling_option_ids = option_group_ids_by_key.get((sibling_scene, group_id)) or []
        if not option_signatures_compatible(
            group_option_ids,
            sibling_option_ids,
            option_signatures_by_id=option_signatures_by_id,
            sequence_similarity_at_least=sequence_similarity_at_least,
        ):
            continue
        sibling_tree = load_dialog_tree(sibling_scene) or {}
        sibling_branches = sibling_tree.get("branches") or {}
        branch_line_ids_by_option: dict[str, list[str]] = {}
        sibling_line_ids_by_option: dict[str, list[str]] = {}
        used_local_line_ids: set[str] = set()
        for local_option_id, sibling_option_id in zip(
            group_option_ids, sibling_option_ids
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
                sibling_signature = dialog_line_text_signature(
                    sibling_line_id,
                    dialog_rows=dialog_rows,
                    translate=translate,
                    option_text_signature=option_text_signature,
                )
                if not sibling_signature:
                    mapped_line_ids = []
                    break
                matches = [
                    local_line_id
                    for local_line_id in local_candidate_line_ids
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
            if not mapped_line_ids:
                branch_line_ids_by_option = {}
                break
            branch_line_ids_by_option[local_option_id] = mapped_line_ids
            sibling_line_ids_by_option[local_option_id] = sibling_branch_line_ids
        if len(branch_line_ids_by_option) != len(group_option_ids):
            continue
        if len({tuple(line_ids) for line_ids in branch_line_ids_by_option.values()}) < 2:
            continue
        sibling_option_ids_by_option = {
            local_option_id: sibling_option_id
            for local_option_id, sibling_option_id in zip(
                group_option_ids, sibling_option_ids
            )
        }
        source_bits = unique_preserve([
            str(value)
            for value in (
                sibling_scene,
                sibling_tree.get("sourceKey") or "",
                sibling_tree.get("file") or "",
                sibling_anchor_record.get("timeline") or "",
            )
            if str(value or "").strip()
        ])
        return {
            "code": "siblingSceneTextBranches",
            "reason": "siblingSceneTextMatch",
            "detail": (
                "A sibling scene on the same dialog Timeline has authored "
                "SceneGraph option branches whose branch texts exactly "
                "match local lines after this fallback option anchor."
            ),
            "after": after_id,
            "optionIds": group_option_ids,
            "branchLineIdsByOption": branch_line_ids_by_option,
            "siblingScene": sibling_scene,
            "siblingOptionIdsByOption": sibling_option_ids_by_option,
            "siblingBranchLineIdsByOption": sibling_line_ids_by_option,
            "source": "siblingSceneGraphText",
            "sources": source_bits,
        }
    return {}


def foreign_timeline_option_definition_for_group(
    group_option_ids: list[str],
    sibling_text_risk: dict,
    *,
    authored_option_ids: set[str],
    conversation_key: str,
    cinematic_finish_groups: list[dict],
    timeline_entries: list[dict],
    dialog_tree_option_prefix: Callable[[str], str],
    unique_preserve: Callable[[list[str]], list[str]],
) -> dict:
    """Close local table-only options when the cinematic consumes foreign ids."""
    if sibling_text_risk.get("code") != "siblingSceneTextBranches":
        return {}
    if any(option_id in authored_option_ids for option_id in group_option_ids):
        return {}
    sibling_mapping = sibling_text_risk.get("siblingOptionIdsByOption") or {}
    foreign_option_ids = [
        str(sibling_mapping.get(option_id) or "") for option_id in group_option_ids
    ]
    if not all(foreign_option_ids) or any(
        dialog_tree_option_prefix(option_id) == conversation_key
        for option_id in foreign_option_ids
    ):
        return {}
    for finish_group in cinematic_finish_groups:
        timeline_name = str(finish_group.get("timeline") or "")
        finish_nums = [
            value
            for value in (finish_group.get("finishNums") or [])
            if isinstance(value, int) and not isinstance(value, bool)
        ]
        if not timeline_name or len(finish_nums) < 2:
            continue
        for timeline in timeline_entries:
            entry_name = str(timeline.get("timeline") or timeline.get("sourceKey") or "")
            if entry_name != timeline_name:
                continue
            rows_by_id = {
                str(row.get("id") or ""): row
                for row in (timeline.get("optionRows") or [])
                if isinstance(row, dict) and str(row.get("id") or "")
            }
            if any(option_id in rows_by_id for option_id in group_option_ids):
                continue
            foreign_rows = [rows_by_id.get(option_id) or {} for option_id in foreign_option_ids]
            if not all(foreign_rows):
                continue
            if not all(row.get("changeFinishNum") == 1 for row in foreign_rows):
                continue
            target_finish_nums = [row.get("targetFinishNum") for row in foreign_rows]
            if set(target_finish_nums) != set(finish_nums):
                continue
            return {
                "code": "foreignTimelineOptionDefinitions",
                "reason": "cinematicConsumesForeignOptionIds",
                "detail": (
                    "The local DialogTree launches this exact cinematic "
                    "Timeline, but the Timeline consumes only sibling-scene "
                    "option ids and maps them completely onto its authored "
                    "finish numbers. The same-text local option rows are "
                    "unconsumed table definitions, not missing local routes."
                ),
                "after": sibling_text_risk.get("after") or "",
                "optionIds": group_option_ids,
                "foreignOptionIds": foreign_option_ids,
                "timeline": timeline_name,
                "finishNums": finish_nums,
                "targetFinishNums": target_finish_nums,
                "source": "dialogTimeline",
                "sources": unique_preserve([
                    str(finish_group.get("file") or ""),
                    str(timeline.get("file") or ""),
                    *[
                        str(value)
                        for value in (sibling_text_risk.get("sources") or [])
                    ],
                ]),
            }
    return {}


__all__ = [
    "dialog_line_text_signature",
    "foreign_timeline_option_definition_for_group",
    "option_signature_sequence",
    "option_signatures_compatible",
    "sibling_scene_text_branch_for_group",
]
