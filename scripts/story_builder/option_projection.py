"""Pure projections for dialog option payloads."""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from collections.abc import Callable


def clone_dialog_option_for_hub(
    option_id: str,
    hub_index: int,
    target_scene_key: str = "",
    *,
    option_payload_by_id: dict[str, dict],
    option_signature_by_id: dict[str, tuple[str, str]],
) -> dict | None:
    option_id = str(option_id or "").strip()
    if not option_id:
        return None
    base = option_payload_by_id.get(option_id)
    if base:
        option = copy.deepcopy(base)
    else:
        text, icon = option_signature_by_id.get(option_id, ("", ""))
        option = {
            "id": option_id,
            "i": hub_index,
            "text": text,
            "icon": icon or "",
            "_debug": {
                "table": "DialogOptionTable",
                "rowId": option_id,
                "source": {},
                "hubOnly": True,
            },
        }
    option["i"] = hub_index
    if target_scene_key:
        option["targetSceneKey"] = target_scene_key
        option.setdefault("_debug", {})["hubTargetSceneKey"] = target_scene_key
    return option


def source_hub_option_groups(
    conv_key: str,
    valid_line_ids: set[str],
    source: dict | None,
    *,
    option_payload_by_id: dict[str, dict],
    option_signature_by_id: dict[str, tuple[str, str]],
    option_group_parts: Callable[[str], tuple[str, int, int] | None],
    unique_preserve: Callable[[list[str]], list[str]],
    scene_link_option_projector: Callable[[dict], dict],
) -> tuple[list[dict], list[dict]]:
    if not source:
        return [], []
    raw_links = [
        link
        for link in (source.get("sceneLinks") or [])
        if isinstance(link, dict)
        and (link.get("sourceKey") or "") == conv_key
    ]
    if not raw_links:
        return [], []
    nodes_by_id = {
        str(node.get("id") or ""): node
        for node in ((source.get("lineGraph") or {}).get("nodes") or [])
        if isinstance(node, dict) and node.get("id") is not None
    }
    by_source_node: dict[str, list[dict]] = defaultdict(list)
    for link in raw_links:
        link_debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
        source_node_id = str(link_debug.get("sourceOptionNodeId") or "").strip()
        group_scene_keys = [
            str(scene_key)
            for scene_key in (link_debug.get("groupSceneKeys") or [])
            if str(scene_key or "").strip()
        ]
        if source_node_id and conv_key in group_scene_keys and len(set(group_scene_keys)) > 1:
            by_source_node[source_node_id].append(link)
    hub_groups: list[dict] = []
    hub_scene_links: list[dict] = []
    for source_node_id, links in sorted(by_source_node.items()):
        local_after = next(
            (
                str(link.get("after") or "")
                for link in links
                if (link.get("sceneKey") or "") == conv_key
                and str(link.get("after") or "") in valid_line_ids
            ),
            "",
        )
        if not local_after:
            continue
        node_option_ids = [
            str(option_id)
            for option_id in (nodes_by_id.get(source_node_id, {}).get("optionIds") or [])
            if str(option_id or "").strip()
        ]
        if len(node_option_ids) < 2:
            continue
        raw_option_by_id: dict[str, dict] = {}
        target_scene_by_option: dict[str, str] = {}
        group_scene_keys: list[str] = []
        target_scene_keys: list[str] = []
        for link in links:
            link_debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
            group_scene_keys.extend(
                str(scene_key)
                for scene_key in (link_debug.get("groupSceneKeys") or [])
                if str(scene_key or "").strip()
            )
            target_scene_keys.extend(
                str(scene_key)
                for scene_key in (link_debug.get("targetSceneKeys") or [])
                if str(scene_key or "").strip()
            )
            scene_key = str(link.get("sceneKey") or "")
            for raw_option in link.get("options") or []:
                if not isinstance(raw_option, dict):
                    continue
                option_id = str(raw_option.get("optionId") or "").strip()
                if not option_id:
                    continue
                raw_option_by_id.setdefault(option_id, raw_option)
                if scene_key:
                    target_scene_by_option.setdefault(option_id, scene_key)
        ordered_option_ids = [
            option_id
            for option_id in node_option_ids
            if option_id in raw_option_by_id or option_id in option_payload_by_id
        ]
        if len(ordered_option_ids) < 2:
            continue
        group_ids = [
            parts[1]
            for option_id in ordered_option_ids
            if (parts := option_group_parts(option_id))
        ]
        group_id = group_ids[0] if group_ids else 1
        options = [
            option
            for option in (
                clone_dialog_option_for_hub(
                    option_id,
                    hub_index,
                    target_scene_by_option.get(option_id, ""),
                    option_payload_by_id=option_payload_by_id,
                    option_signature_by_id=option_signature_by_id,
                )
                for hub_index, option_id in enumerate(ordered_option_ids, start=1)
            )
            if option is not None
        ]
        if len(options) < 2:
            continue
        hub_groups.append({
            "g": group_id,
            "after": local_after,
            "options": options,
            "hubMenu": {
                "sourceKey": conv_key,
                "sourceOptionNodeId": source_node_id,
                "sourceFile": source.get("file") or "",
                "sceneKeys": unique_preserve(group_scene_keys),
            },
        })
        hub_scene_links.append({
            "sourceKey": conv_key,
            "file": source.get("file") or "",
            "after": local_after,
            "options": [
                scene_link_option_projector(raw_option_by_id[option_id])
                for option_id in ordered_option_ids
                if option_id in raw_option_by_id
            ],
            "sceneSpan": True,
            "sourceSceneKeys": source.get("sourceSceneKeys") or sorted(set(group_scene_keys)),
            "_debug": {
                "source": {
                    "targetKey": conv_key,
                    "sourceKey": conv_key,
                    "file": source.get("file") or "",
                },
                "link": {
                    "sourceOptionNodeId": source_node_id,
                    "groupSceneKeys": unique_preserve(group_scene_keys),
                    "targetSceneKeys": unique_preserve(target_scene_keys),
                    "sourceHubMenu": True,
                },
            },
        })
    return hub_groups, hub_scene_links


def apply_source_hub_option_groups(
    payload: dict,
    scene_graph_links: list[dict],
    source: dict | None,
    *,
    option_payload_by_id: dict[str, dict],
    option_signature_by_id: dict[str, tuple[str, str]],
    option_group_parts: Callable[[str], tuple[str, int, int] | None],
    unique_preserve: Callable[[list[str]], list[str]],
    scene_link_option_projector: Callable[[dict], dict],
) -> list[dict]:
    def group_after_suffix(group: dict) -> int:
        match = re.search(r"_(\d+)$", str(group.get("after") or ""))
        return int(match.group(1)) if match else -1

    def link_source_node_id(link: dict) -> str:
        debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
        link_debug = debug.get("link") if isinstance(debug.get("link"), dict) else {}
        return str(link_debug.get("sourceOptionNodeId") or "")

    def link_option_ids(link: dict) -> set[str]:
        return {
            str(option.get("optionId") or "")
            for option in (link.get("options") or [])
            if isinstance(option, dict) and str(option.get("optionId") or "")
        }

    conv_key = str(payload.get("key") or "")
    valid_line_ids = {
        str(line.get("id") or "")
        for line in (payload.get("lines") or [])
        if isinstance(line, dict) and str(line.get("id") or "")
    }
    hub_groups, hub_links = source_hub_option_groups(
        conv_key,
        valid_line_ids,
        source,
        option_payload_by_id=option_payload_by_id,
        option_signature_by_id=option_signature_by_id,
        option_group_parts=option_group_parts,
        unique_preserve=unique_preserve,
        scene_link_option_projector=scene_link_option_projector,
    )
    if not hub_groups:
        return scene_graph_links
    groups = [
        group
        for group in (payload.get("optionGroups") or [])
        if isinstance(group, dict)
    ]
    for hub_group in hub_groups:
        hub_g = hub_group.get("g")
        replaced = False
        for idx, existing_group in enumerate(groups):
            if existing_group.get("g") == hub_g and existing_group.get("after") == hub_group.get("after"):
                groups[idx] = hub_group
                replaced = True
                break
        if not replaced:
            groups.append(hub_group)
    groups.sort(key=lambda group: (group_after_suffix(group), group.get("g") or 0))
    payload["optionGroups"] = groups
    for hub_link in hub_links:
        if hub_link.get("options"):
            hub_debug = hub_link.get("_debug") if isinstance(hub_link.get("_debug"), dict) else {}
            hub_link_debug = hub_debug.get("link") if isinstance(hub_debug.get("link"), dict) else {}
            hub_source_node_id = str(hub_link_debug.get("sourceOptionNodeId") or "")
            hub_after = str(hub_link.get("after") or "")
            hub_option_ids = link_option_ids(hub_link)
            scene_graph_links[:] = [
                existing
                for existing in scene_graph_links
                if not (
                    str(existing.get("after") or "") == hub_after
                    and link_source_node_id(existing) == hub_source_node_id
                    and link_option_ids(existing).issubset(hub_option_ids)
                )
            ]
            scene_graph_links.append(hub_link)
    return scene_graph_links


def attach_submenu_targets(
    links: list[dict],
    *,
    option_text_by_id: dict[str, str],
    option_scene_key: Callable[[str], str | None],
) -> None:
    for link in links or []:
        for opt in link.get("options") or []:
            if not isinstance(opt, dict):
                continue
            submenu_scene_keys = [
                str(scene_key)
                for scene_key in (opt.get("submenuSceneKeys") or [])
                if str(scene_key).strip()
            ]
            if not submenu_scene_keys:
                continue
            debug = opt.get("_debug") if isinstance(opt.get("_debug"), dict) else {}
            return_option_ids = [
                str(option_id)
                for option_id in (debug.get("returnOptionIds") or [])
                if str(option_id).strip()
            ]
            targets: list[dict] = []
            seen_targets: set[tuple[str, str]] = set()
            for idx, option_id in enumerate(return_option_ids):
                scene_key = option_scene_key(option_id) or ""
                if not scene_key and idx < len(submenu_scene_keys):
                    scene_key = submenu_scene_keys[idx]
                if not scene_key:
                    continue
                key = (scene_key, option_id)
                if key in seen_targets:
                    continue
                seen_targets.add(key)
                target = {
                    "sceneKey": scene_key,
                    "optionId": option_id,
                }
                if text := option_text_by_id.get(option_id):
                    target["text"] = text
                targets.append(target)
            for scene_key in submenu_scene_keys:
                if any(target.get("sceneKey") == scene_key for target in targets):
                    continue
                target = {"sceneKey": scene_key}
                targets.append(target)
            if targets:
                opt["submenuTargets"] = targets


def dialog_recovery_methods(
    payload: dict,
    *,
    line_id_list_equal: Callable[[object, object], bool],
) -> list[str]:
    methods: list[str] = []

    def add(method: str) -> None:
        if method and method not in methods:
            methods.append(method)

    debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
    runtime_registry = (
        debug.get("runtimeRegistry")
        if isinstance(debug.get("runtimeRegistry"), dict)
        else {}
    )
    line_order = debug.get("lineOrder") if isinstance(debug.get("lineOrder"), dict) else {}
    line_order_mode = str(line_order.get("mode") or "")
    if line_order_mode == "lineIdSuffix":
        registry = debug.get("runtimeRegistry") if isinstance(debug.get("runtimeRegistry"), dict) else {}
        original_line_ids = line_order.get("originalLineIds") or []
        ordered_line_ids = line_order.get("orderedLineIds") or []
        if registry.get("registered") is True and line_id_list_equal(original_line_ids, ordered_line_ids):
            add("lineOrder:runtimeRowIteration")
        elif registry.get("registered") is False:
            add("lineOrder:unregisteredScene")
        else:
            add("lineOrder:lineIdSuffix")
    elif line_order_mode:
        add(f"lineOrder:{line_order_mode}")
    elif len(payload.get("lines") or []) > 1:
        add("lineOrder:missing")
    option_groups = [
        group
        for group in (payload.get("optionGroups") or [])
        if isinstance(group, dict)
    ]
    warnings = [
        warning
        for warning in (payload.get("warnings") or [])
        if isinstance(warning, dict)
    ]
    layout_warning = next(
        (warning for warning in warnings if warning.get("code") == "inferredOptionLayout"),
        None,
    )
    if layout_warning:
        reason = str(layout_warning.get("reason") or "")
        group_details = [
            detail
            for detail in (layout_warning.get("groupDetails") or [])
            if isinstance(detail, dict)
        ]
        modes = {
            str(detail.get("inferredAnchorMode") or "")
            for detail in group_details
        }
        statuses = {str(detail.get("status") or "") for detail in group_details}
        if runtime_registry.get("registered") is False:
            add("optionLayout:tableOnlyCutContent")
        else:
            if "lineNumber" in modes:
                add("optionLayout:keyMatched")
            if "sparseGap" in modes:
                add("optionLayout:sparseGap")
            if "siblingTimelinePosition" in modes:
                add("optionLayout:siblingTimelinePosition")
            if "lastLine" in modes:
                add("optionLayout:lastLine")
            if "unanchored" in statuses:
                add("optionLayout:unanchored")
        if not group_details:
            if reason == "partialAuthoredCoverage":
                add("optionLayout:partialAuthoredCoverage")
            elif reason == "noAuthoredGroupAnchor":
                add("optionLayout:noAuthoredGroupAnchor")
            else:
                add("optionLayout:fallback")
    elif option_groups:
        add("optionLayout:authored")
    if payload.get("sceneGraphLinks"):
        add("optionBranch:sceneGraph")
    if payload.get("graphFragments"):
        add("optionBranch:dialogTreeFragment")
    for group in option_groups:
        if group.get("continuationOptionIds"):
            add("optionBranch:continuationOption")
        if group.get("branchHint"):
            add("optionBranch:siblingSceneHint")
        risk = group.get("optionBranchRisk") if isinstance(group.get("optionBranchRisk"), dict) else {}
        if not risk:
            continue

        def add_option_branch_methods(branch_risk: dict) -> None:
            if branch_risk.get("code") == "timelineRouteBranches":
                add("optionBranch:runtimeJump")
            elif (
                branch_risk.get("code")
                == "timelineClipOptionIndexBranches"
            ):
                add("optionBranch:runtimeClipOptionIndex")
            elif branch_risk.get("code") == "siblingSceneTextBranches":
                add("optionBranch:siblingSceneText")
            elif branch_risk.get("code") in {
                "separateDialogTreeOptionNodes",
                "sequentialDialogTreeOptionNodes",
            }:
                add(f"optionBranch:{branch_risk['code']}")
            elif (
                branch_risk.get("code")
                == "orphanDialogTreeOptionDefinitions"
            ):
                add("optionBranch:orphanDialogTreeOptionDefinitions")
            elif branch_risk.get("candidateMapping") == "trunkClipOptionIndex":
                add("optionBranch:rawIndexMatched")
            elif branch_risk.get("code") == "inferredFollowingLines":
                add("optionBranch:timelineAdjacent")
            elif branch_risk.get("code") == "sharedTimelineContinuation":
                add("optionBranch:commonContinuation")
            if branch_risk.get("commonContinuationLineId"):
                add("optionBranch:commonContinuation")
            if branch_risk.get("continuationOptionIds"):
                add("optionBranch:continuationOption")

        add_option_branch_methods(risk)
    return methods


__all__ = [
    "apply_source_hub_option_groups",
    "attach_submenu_targets",
    "clone_dialog_option_for_hub",
    "dialog_recovery_methods",
    "source_hub_option_groups",
]
