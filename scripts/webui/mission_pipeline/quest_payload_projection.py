"""Publish authored Quest objective and client-action rows.

Condition parsing, authority classification, LevelScript evidence, table paths, and
runtime contracts remain owned by the Mission Pipeline entrypoint and are injected.
This module only projects those inputs into the published Quest payload schema.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any


_SUBMIT_ITEM_ROWS_CACHE: dict[str, Any] | None = None


def submit_item_requirements(
    submission_id: str,
    *,
    submit_item_table: Path,
    json_loader: Callable[[Path], Any],
) -> dict[str, Any]:
    """Return exact authored SubmitItem requirements for one submission id."""
    global _SUBMIT_ITEM_ROWS_CACHE
    if _SUBMIT_ITEM_ROWS_CACHE is None:
        payload = json_loader(submit_item_table)
        _SUBMIT_ITEM_ROWS_CACHE = payload if isinstance(payload, dict) else {}
    row = _SUBMIT_ITEM_ROWS_CACHE.get(submission_id)
    if not isinstance(row, dict):
        return {
            "submissionId": submission_id,
            "tableDefined": False,
            "requirementGroups": [],
        }
    groups: list[dict[str, Any]] = []
    for group_index, group in enumerate(row.get("paramData") or []):
        if not isinstance(group, dict):
            continue
        params = group.get("paramList") or []
        item_param = params[0] if len(params) > 0 and isinstance(params[0], dict) else {}
        count_param = params[1] if len(params) > 1 and isinstance(params[1], dict) else {}
        item_ids = [
            str(value)
            for value in item_param.get("valueStringList") or []
            if value not in (None, "")
        ]
        counts = [
            int(value)
            for value in count_param.get("valueIntList") or []
            if isinstance(value, (int, float))
        ]
        items = [{
            "itemId": item_id,
            "count": counts[index] if index < len(counts) else (
                counts[0] if counts else None
            ),
        } for index, item_id in enumerate(item_ids)]
        groups.append({
            "index": group_index + 1,
            "type": group.get("type"),
            "items": items,
        })
    return {
        "submissionId": submission_id,
        "tableDefined": True,
        "requirementGroups": groups,
    }


def submission_dialog_co_gates(
    condition: Any,
    *,
    get_const_projector: Callable[..., Any],
    type_name_projector: Callable[[Any], str],
) -> list[dict[str, Any]]:
    """Find direct SubmitItem + dialog-finish siblings under authored AND groups."""
    output: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if not isinstance(value, dict):
            return
        children = [
            child
            for child in value.get("subConditions") or []
            if isinstance(child, dict)
        ]
        expression = str(value.get("conditionEvalString") or "").lower()
        if children and "and" in expression:
            submissions = []
            dialogs = []
            for child in children:
                child_type = type_name_projector(child.get("$type"))
                if child_type == "CheckQuestSubmitItem":
                    submission_id = get_const_projector(
                        child, "_submissionId", "submissionId"
                    )
                    if isinstance(submission_id, str) and submission_id:
                        submissions.append(submission_id)
                elif child_type == "CheckTalkOptionFinish":
                    dialog_id = get_const_projector(child, "_dialogId", "dialogId")
                    finish_id = get_const_projector(child, "_finishId", "finishId")
                    if isinstance(dialog_id, str) and dialog_id:
                        dialogs.append((dialog_id, finish_id))
            for submission_id in submissions:
                for dialog_id, finish_id in dialogs:
                    output.append({
                        "submissionId": submission_id,
                        "dialogId": dialog_id,
                        "finishId": finish_id,
                        "combineConditionId": str(
                            value.get("uniqueId") or ""
                        ),
                        "relation": "same_authored_and_objective",
                    })
        for child in children:
            walk(child)

    walk(condition)
    return output


def submission_level_script_co_gates(
    condition: Any,
    *,
    get_const_projector: Callable[..., Any],
    type_name_projector: Callable[[Any], str],
) -> list[dict[str, Any]]:
    """Find direct SubmitItem + LevelScript-stage siblings under authored AND groups."""
    output: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if not isinstance(value, dict):
            return
        children = [
            child
            for child in value.get("subConditions") or []
            if isinstance(child, dict)
        ]
        expression = str(value.get("conditionEvalString") or "").lower()
        if children and "and" in expression:
            submissions: list[str] = []
            level_scripts: list[tuple[str, str, str]] = []
            for child in children:
                child_type = type_name_projector(child.get("$type"))
                if child_type == "CheckQuestSubmitItem":
                    submission_id = get_const_projector(
                        child, "_submissionId", "submissionId"
                    )
                    if isinstance(submission_id, str) and submission_id:
                        submissions.append(submission_id)
                elif child_type == "CheckLevelScriptStageReachMax":
                    level_id = get_const_projector(child, "_levelId", "levelId")
                    script_id = get_const_projector(child, "_scriptId", "scriptId")
                    if isinstance(script_id, dict):
                        script_id = script_id.get("scriptId")
                    if isinstance(script_id, (str, int)) and str(script_id):
                        level_scripts.append((
                            str(level_id or ""),
                            str(script_id),
                            str(child.get("uniqueId") or ""),
                        ))
            for submission_id in submissions:
                for level_id, script_id, condition_id in level_scripts:
                    output.append({
                        "submissionId": submission_id,
                        "levelId": level_id,
                        "scriptId": script_id,
                        "conditionId": condition_id,
                        "combineConditionId": str(
                            value.get("uniqueId") or ""
                        ),
                        "relation": "same_authored_and_objective",
                    })
        for child in children:
            walk(child)

    walk(condition)
    return output


def objective_row(
    objective: dict[str, Any],
    index: int,
    *,
    include_level_script_source_evidence: bool = True,
    authority_classifier: Callable[[list[str]], str],
    condition_objects_projector: Callable[[Any], list[dict[str, Any]]],
    condition_tree_projector: Callable[[Any], dict[str, Any] | None],
    get_const_projector: Callable[..., Any],
    level_script_source_projector: Callable[[Any], list[dict[str, Any]]],
    level_script_dependency_projector: Callable[[Any], list[dict[str, Any]]],
    json_loader: Callable[[Path], Any],
    submit_item_table: Path,
    tracking_info_projector: Callable[[Any, int], dict[str, Any] | None],
    type_name_projector: Callable[[Any], str],
) -> dict[str, Any]:
    condition = objective.get("condition")
    objects = condition_objects_projector(condition)
    types = sorted({type_name_projector(row.get("$type")) for row in objects if type_name_projector(row.get("$type"))})
    dialog_finishes: list[dict[str, Any]] = []
    quest_state_refs: list[dict[str, Any]] = []
    level_scripts: set[str] = set()
    properties: set[str] = set()
    server_placeholder_condition_ids: set[str] = set()
    submission_checks: list[dict[str, Any]] = []
    for row in objects:
        name = type_name_projector(row.get("$type"))
        if name == "GameConditionServerPlaceHolder":
            condition_id = row.get("uniqueId")
            if condition_id not in (None, ""):
                server_placeholder_condition_ids.add(str(condition_id))
        if name == "CheckTalkOptionFinish":
            dialog = get_const_projector(row, "_dialogId", "dialogId")
            finish = get_const_projector(row, "_finishId", "finishId")
            if isinstance(dialog, str):
                dialog_finishes.append({"dialogId": dialog, "finishId": finish})
        if name == "CheckQuestSubmitItem":
            submission_id = get_const_projector(row, "_submissionId", "submissionId")
            if isinstance(submission_id, str) and submission_id:
                submission_check = submit_item_requirements(
                    submission_id,
                    submit_item_table=submit_item_table,
                    json_loader=json_loader,
                )
                submission_check["conditionId"] = str(row.get("uniqueId") or "")
                submission_checks.append(submission_check)
        if name in {"CheckQuestState", "SimpleConditionCheckQuestState"}:
            quest_id = get_const_projector(row, "_questId", "questId", "_targetQuestId", "targetQuestId")
            state = get_const_projector(row, "_targetQuestState", "targetQuestState", "compareTarget")
            if isinstance(quest_id, str):
                quest_state_refs.append({"questId": quest_id, "state": state})
        script = get_const_projector(row, "_scriptId", "scriptId")
        if isinstance(script, dict):
            script = script.get("scriptId")
        if isinstance(script, (str, int)):
            level_scripts.add(str(script))
        prop = get_const_projector(row, "_propertyKey", "propertyKey", "_key", "key")
        if isinstance(prop, str):
            properties.add(prop)
    description = objective.get("description") or {}
    tracking = [
        normalized
        for tracking_index, info in enumerate(
            objective.get("trackingInfoList") or []
        )
        if (
            normalized := tracking_info_projector(info, tracking_index)
        ) is not None
    ]
    return {
        "index": index,
        "conditionId": condition.get("uniqueId") if isinstance(condition, dict) else "",
        "descriptionKey": description.get("key") if isinstance(description, dict) else "",
        "multiple": bool(objective.get("multiple")),
        "condition": condition_tree_projector(condition),
        "conditionTypes": types,
        "authority": authority_classifier(types),
        "serverPlaceholderConditionIds": sorted(server_placeholder_condition_ids),
        "dialogFinishes": dialog_finishes,
        "submissionChecks": submission_checks,
        "submissionDialogCoGates": submission_dialog_co_gates(
            condition,
            get_const_projector=get_const_projector,
            type_name_projector=type_name_projector,
        ),
        "submissionLevelScriptCoGates": submission_level_script_co_gates(
            condition,
            get_const_projector=get_const_projector,
            type_name_projector=type_name_projector,
        ),
        "questStateRefs": quest_state_refs,
        "levelScriptIds": sorted(level_scripts),
        "levelScriptSources": (
            level_script_source_projector(condition)
            if include_level_script_source_evidence
            else []
        ),
        "levelScriptTaskDependencies": level_script_dependency_projector(condition),
        "propertyKeys": sorted(properties),
        "tracking": tracking,
    }


def action_rows(
    mission: dict[str, Any],
    *,
    compact_scalar_projector: Callable[[Any], Any],
    quest_action_triggers: dict[Any, str],
    type_name_projector: Callable[[Any], str],
) -> dict[str, list[dict[str, Any]]]:
    action_by_id: dict[Any, dict[str, Any]] = {}
    next_action_by_id: dict[Any, Any] = {}
    data_map = ((mission.get("actionMapRaw") or {}).get("dataMap") or {})
    for action in data_map.get("actionList") or []:
        if not isinstance(action, dict):
            continue
        action_id = action.get("_ID")
        facts = {
            key.lstrip("_"): compact_scalar_projector(value)
            for key, value in action.items()
            if key not in {"$type", "_ID", "_uid"} and value not in (None, "", [], {})
        }
        action_by_id[action_id] = {
            "id": action_id,
            "type": type_name_projector(action.get("$type")) or "UnknownAction",
            "facts": facts,
        }
        next_action_by_id[action_id] = action.get("_nextID")
    keys = mission.get("clientActionMapKey") or []
    values = mission.get("clientActionMapValue") or []
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, key in enumerate(keys):
        if not isinstance(key, dict):
            continue
        quest_id = key.get("questId")
        if not isinstance(quest_id, str):
            continue
        root_action_id = values[index] if index < len(values) else None
        action_id = root_action_id
        seen_action_ids: set[Any] = set()
        chain_index = 0
        while action_id not in seen_action_ids:
            seen_action_ids.add(action_id)
            action = dict(action_by_id.get(action_id) or {"id": action_id, "type": "UnknownAction"})
            action["trigger"] = key.get("action")
            action["triggerName"] = quest_action_triggers.get(key.get("action"), "UnknownQuestAction")
            action["rootActionId"] = root_action_id
            action["chainIndex"] = chain_index
            output[quest_id].append(action)
            next_action_id = next_action_by_id.get(action_id)
            if not isinstance(next_action_id, int) or next_action_id < 0:
                break
            action_id = next_action_id
            chain_index += 1
    return dict(output)


def annotate_quest_action_dispatch(
    payload: dict[str, Any],
    contract: dict[str, Any],
) -> Counter[str]:
    """Apply the corpus-wide binary dispatcher census to authored action rows."""
    dispatched = {
        int(row["questActionValue"]): row
        for row in contract.get("safeRunDirectCallers") or []
        if isinstance(row, dict) and isinstance(row.get("questActionValue"), int)
    }
    start_value = int(
        (contract.get("questActionEnum") or {}).get("OnStartClientAction", 1)
    )
    start_dispatchers = contract.get("startActionDispatchers") or []
    counts: Counter[str] = Counter()
    for node in payload.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        for action in node.get("clientActions") or []:
            if not isinstance(action, dict):
                continue
            value = action.get("trigger")
            if value in dispatched:
                caller = dispatched[value]
                status = (
                    "binary_proven_server_success_dispatch"
                    if value == 2
                    else "binary_proven_server_failure_dispatch"
                )
                action["runtimeDispatchHandler"] = caller.get("symbol") or ""
            elif value == start_value and not start_dispatchers:
                status = "authored_definition_no_current_aot_dispatch"
            else:
                status = "runtime_dispatch_unresolved"
            action["runtimeDispatchStatus"] = status
            action["runtimeDispatchSource"] = contract.get("source") or ""
            action["runtimeDispatchBoundary"] = contract.get("boundary") or ""
            counts[f"rows:{status}"] += 1
            if action.get("chainIndex") == 0:
                counts[f"roots:{status}"] += 1
    return counts

