"""Project classified Story relations into evidence-typed trigger routes.

Native/runtime classification remains owned by the Mission Pipeline builder and is
injected as runtime_selector. This module only normalizes classified rows into the
published route schema.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def unique_route_strings(*values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        items = value if isinstance(value, (list, tuple, set)) else [value]
        for item in items:
            text = str(item or "").strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
    return result


NATIVE_OCCURRENCE_FIELDS = (
    "occurrences",
    "levelScriptOccurrences",
    "nativeOccurrences",
    "nativeBlackActionOccurrences",
    "parentDialogNativeOccurrences",
    "preloadOccurrences",
    "worldEntityLevelScriptEvidence",
)


def _native_occurrence_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field in NATIVE_OCCURRENCE_FIELDS:
        for occurrence in row.get(field) or []:
            if not isinstance(occurrence, dict):
                continue
            if (
                field == "worldEntityLevelScriptEvidence"
                and isinstance(occurrence.get("listener"), dict)
            ):
                occurrence = {
                    **occurrence,
                    "actionName": (
                        occurrence.get("actionName")
                        or occurrence.get("nativeAction")
                    ),
                    "nativeEventOwners": [occurrence["listener"]],
                }
            signature = json.dumps(
                occurrence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if signature not in seen:
                seen.add(signature)
                occurrences.append(occurrence)
    return occurrences


def _compact_native_trigger_paths(
    row: dict[str, Any],
    *,
    runtime_selector: Callable[..., dict[str, Any]],
) -> list[dict[str, Any]]:
    occurrences = _native_occurrence_rows(row)
    if not occurrences and isinstance(row.get("nativeEventOwners"), list):
        occurrences = [{
            "levelId": next(iter(row.get("levelIds") or []), ""),
            "scriptId": next(iter(row.get("scriptIds") or []), ""),
            "sourceFile": next(iter(row.get("sourceFiles") or []), ""),
            "nativeEventOwners": row.get("nativeEventOwners") or [],
        }]

    paths: list[dict[str, Any]] = []
    seen: set[str] = set()
    for occurrence in occurrences:
        level_id = str(occurrence.get("levelId") or "")
        script_id = str(occurrence.get("scriptId") or "")
        source_file = str(occurrence.get("sourceFile") or "")
        for owner in occurrence.get("nativeEventOwners") or []:
            if not isinstance(owner, dict):
                continue
            event_name = str(owner.get("headerName") or "").strip()
            event_detail = (
                owner.get("eventDetail")
                if isinstance(owner.get("eventDetail"), dict)
                else {}
            )
            header_local_id = (
                int(owner["headerLocalId"])
                if isinstance(owner.get("headerLocalId"), int)
                else None
            )
            selector = runtime_selector(
                event_name,
                event_detail,
                level_id=level_id,
                script_id=script_id,
                header_local_id=header_local_id,
            )
            steps = []
            for step in owner.get("path") or []:
                if not isinstance(step, dict):
                    continue
                compact_step = {
                    key: step[key]
                    for key in (
                        "edge",
                        "localId",
                        "actionName",
                        "recordClass",
                        "unionTag",
                    )
                    if step.get(key) is not None
                }
                if compact_step:
                    steps.append(compact_step)
            path = {
                "eventName": event_name,
                "eventSummary": str(event_detail.get("summary") or ""),
                "transport": str(event_detail.get("transport") or ""),
                "serverExchange": event_detail.get("serverExchange"),
                "levelId": level_id,
                "scriptId": script_id,
                "sourceFile": source_file,
                "headerLocalId": header_local_id,
                "selector": selector or None,
                "steps": steps,
            }
            signature = json.dumps(
                path,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if signature not in seen:
                seen.add(signature)
                paths.append(path)
    return paths


def build_story_trigger_route(
    row: dict[str, Any],
    *,
    mission_id: str,
    quest_id: str = "",
    scope: str = "mission",
    owner_status: str = "connected",
    runtime_selector: Callable[..., dict[str, Any]],
) -> dict[str, Any] | None:
    """Normalize one Story relation into a compact, evidence-typed route."""
    key = str(row.get("key") or "")
    if not key:
        return None
    relation = str(row.get("relation") or "unknown")
    direction = str(row.get("direction") or "context")
    owner_unresolved = owner_status in {
        "unresolved",
        "unresolved_playback",
    }
    if relation == "original_text_definition_without_consumer":
        causality = "definition_only"
    elif owner_status == "unresolved_playback":
        causality = "playback_owner_unresolved"
    elif owner_unresolved:
        causality = "context_owner_unresolved"
    elif direction == "quest_to_story":
        causality = "playback"
    elif direction == "story_to_quest":
        causality = "condition"
    elif row.get("dependencyOnly") is True or row.get("ownership") is False:
        causality = "dependency"
    else:
        causality = "context"

    native_paths = _compact_native_trigger_paths(
        row,
        runtime_selector=runtime_selector,
    )
    native_occurrences = _native_occurrence_rows(row)
    event_names = unique_route_strings(
        row.get("event"),
        row.get("nativeEventNames"),
        [path.get("eventName") for path in native_paths],
    )
    event_summaries = unique_route_strings(
        row.get("nativeEventSummaries"),
        [path.get("eventSummary") for path in native_paths],
    )
    action_names = unique_route_strings(
        row.get("actionType"),
        row.get("actionName"),
        row.get("nativeAction"),
        row.get("nativeActions"),
        [occurrence.get("actionName") for occurrence in native_occurrences],
        [
            step.get("actionName")
            for path in native_paths
            for step in path.get("steps") or []
            if str(step.get("recordClass") or "").startswith("play_")
        ],
    )
    script_ids = unique_route_strings(
        row.get("scriptId"),
        row.get("scriptIds"),
        [path.get("scriptId") for path in native_paths],
    )
    source_files = unique_route_strings(
        row.get("sourceFile"),
        row.get("sourceFiles"),
        row.get("assetPaths"),
        row.get("trackPaths"),
        row.get("rootPaths"),
        [path.get("sourceFile") for path in native_paths],
    )
    timeline_dialog_containments = [
        containment
        for containment in row.get("timelineDialogContainments") or []
        if isinstance(containment, dict)
    ]
    parent_story_key = str(row.get("parentStoryKey") or "")
    timeline_ids = unique_route_strings(
        row.get("timelines"),
        [
            containment.get("timeline")
            for containment in timeline_dialog_containments
        ],
    )
    embedded_line_ids = unique_route_strings(
        row.get("textIds"),
        [
            line_id
            for containment in timeline_dialog_containments
            for line_id in containment.get("lineIds") or []
        ],
    )
    embedded_option_ids = unique_route_strings(
        row.get("optionIds"),
        [
            option_id
            for containment in timeline_dialog_containments
            for option_id in containment.get("optionIds") or []
        ],
    )
    before_parent_line_ids = unique_route_strings([
        containment.get("beforeParentLineId")
        for containment in timeline_dialog_containments
    ])
    after_parent_line_ids = unique_route_strings([
        containment.get("afterParentLineId")
        for containment in timeline_dialog_containments
    ])

    owner_step = {
        "kind": "ownership_gap" if owner_unresolved else scope,
        "id": quest_id if scope == "quest" and quest_id else mission_id,
        "phase": str(row.get("phase") or ""),
    }
    story_step = {
        "kind": (
            "dialog_definition"
            if row.get("dialogDefinitionOnly") is True
            else "story"
        ),
        "id": key,
    }
    middle_steps: list[dict[str, Any]] = []
    if row.get("serverMessage"):
        middle_steps.append({
            "kind": "server_message",
            "id": str(row["serverMessage"]),
            "fields": unique_route_strings(row.get("serverFields")),
        })
    if event_names:
        middle_steps.append({
            "kind": "native_event",
            "ids": event_names,
            "summaries": event_summaries,
        })
    if script_ids:
        middle_steps.append({"kind": "levelscript", "ids": script_ids})
    if relation == "leveldata_interactive_narrative_config":
        leveldata_assets = unique_route_strings(row.get("levelDataAssets"))
        if leveldata_assets:
            middle_steps.append({
                "kind": "leveldata",
                "ids": leveldata_assets,
            })
        progress_conditions = [
            dict(condition)
            for condition in row.get("progressLockConditions") or []
            if isinstance(condition, dict)
        ]
        if (
            row.get("progressLockConditionStatus") == "decoded"
            and progress_conditions
        ):
            condition_summaries: list[str] = []

            def summarize_condition(node: object, depth: int = 0) -> None:
                if not isinstance(node, dict):
                    return
                if node.get("conditionType") == "CombinedConditionRuntime":
                    condition_summaries.append(
                        (
                            f"{'nested ' if depth else ''}combined operator "
                            f"{node.get('conditionOperator')} runtime flag "
                            f"{str(node.get('serializedRuntimeFlag')).lower()}"
                        )
                    )
                    for child in node.get("conditions") or []:
                        summarize_condition(child, depth + 1)
                    return
                condition_summaries.append(
                    (
                        f"{node.get('ownerKind')} "
                        f"{node.get('ownerId')} state "
                        f"{node.get('compareTarget')} "
                        f"(compare {node.get('compareOperator')})"
                    )
                )

            tree = row.get("progressLockConditionTree")
            if isinstance(tree, dict):
                summarize_condition(tree)
            else:
                for condition in progress_conditions:
                    summarize_condition(condition)
            middle_steps.append({
                "kind": "availability_condition",
                "id": str(row.get("progressLockConditionType") or ""),
                "summaries": condition_summaries,
            })
    if (
        relation in {
            "levelscript_interactive_narrative_config",
            "leveldata_interactive_narrative_config",
        }
        and (
            row.get("localInteractiveId") is not None
            or row.get("entityLogicId") is not None
        )
    ):
        interactive_summaries = unique_route_strings(
            row.get("rawTypeId"),
            row.get("entityTemplateIds"),
        )
        middle_steps.append({
            "kind": "narrative_interactive",
            "id": str(
                row.get("localInteractiveId")
                if row.get("localInteractiveId") is not None
                else row.get("entityLogicId")
            ),
            "summaries": interactive_summaries,
        })
    if action_names:
        middle_steps.append({"kind": "native_action", "ids": action_names})
    if relation == "timeline_dialog_contains_foreign_dialog":
        if parent_story_key:
            middle_steps.append({
                "kind": "parent_story",
                "id": parent_story_key,
            })
        if timeline_ids:
            middle_steps.append({
                "kind": "dialog_timeline",
                "ids": timeline_ids,
                "beforeParentLineIds": before_parent_line_ids,
                "afterParentLineIds": after_parent_line_ids,
            })
    if direction == "story_to_quest":
        steps = [story_step, *middle_steps, owner_step]
    else:
        steps = [owner_step, *middle_steps, story_step]

    return {
        "storyKey": key,
        "missionId": mission_id,
        "questId": quest_id or None,
        "scope": scope,
        "ownerStatus": "unresolved" if owner_unresolved else owner_status,
        "relation": relation,
        "direction": direction,
        "phase": str(row.get("phase") or ""),
        "causality": causality,
        "confidence": str(row.get("confidence") or ""),
        "evidenceTier": str(row.get("evidenceTier") or ""),
        "nativeMappingId": str(row.get("nativeMappingId") or ""),
        "certainty": str(row.get("certainty") or ""),
        "eventNames": event_names,
        "eventSummaries": event_summaries,
        "actionNames": action_names,
        "scriptIds": script_ids,
        "levelId": str(row.get("levelId") or ""),
        "sourcePathIds": unique_route_strings(row.get("sourcePathIds")),
        "parentScopeRelations": unique_route_strings(
            row.get("parentScopeRelations")
        ),
        "carrierKinds": unique_route_strings(row.get("carrierKinds")),
        "occurrenceCount": row.get("occurrenceCount"),
        "runtimeReplacementPossible": row.get("runtimeReplacementPossible"),
        "headerLocalId": row.get("headerLocalId"),
        "gateActionLocalId": row.get("gateActionLocalId"),
        "conditionType": str(row.get("conditionType") or ""),
        "conditionComparer": str(row.get("conditionComparer") or ""),
        "conditionQuestState": row.get("conditionQuestState"),
        "actionLocalId": row.get("actionLocalId"),
        "actionCode": str(row.get("actionCode") or ""),
        "actionKind": str(row.get("actionKind") or ""),
        "levelDataAssets":
            unique_route_strings(row.get("levelDataAssets")),
        "localInteractiveId": row.get("localInteractiveId"),
        "entityLogicId": row.get("entityLogicId"),
        "interactiveRecordIndex": row.get("interactiveRecordIndex"),
        "interactiveRecordBoundarySource":
            str(row.get("interactiveRecordBoundarySource") or ""),
        "narrativeConsumerKind":
            str(row.get("narrativeConsumerKind") or ""),
        "dialogDefinitionOnly":
            row.get("dialogDefinitionOnly") is True,
        "dialogDefinitionBinding":
            row.get("dialogDefinitionBinding") is True,
        "dialogDefinitionConsumerMission":
            str(row.get("dialogDefinitionConsumerMission") or ""),
        "dialogDefinitionConsumerQuestId":
            str(row.get("dialogDefinitionConsumerQuestId") or ""),
        "dialogIdEntryOffset": row.get("dialogIdEntryOffset"),
        "interactiveHornTemplateSha256":
            str(row.get("interactiveHornTemplateSha256") or ""),
        "interactiveHornNativeMappingId":
            str(row.get("interactiveHornNativeMappingId") or ""),
        "levelDataMember21Offset": row.get("levelDataMember21Offset"),
        "levelIdNum": row.get("levelIdNum"),
        "levelScriptBriefDictionaryCountOffset":
            row.get("levelScriptBriefDictionaryCountOffset"),
        "levelScriptBriefDictionaryCount":
            row.get("levelScriptBriefDictionaryCount"),
        "levelScriptDataPathDictionaryCountOffset":
            row.get("levelScriptDataPathDictionaryCountOffset"),
        "levelScriptDataPathDictionaryCount":
            row.get("levelScriptDataPathDictionaryCount"),
        "levelDataSafeZoneOffset": row.get("levelDataSafeZoneOffset"),
        "levelDataSceneId": str(row.get("levelDataSceneId") or ""),
        "levelDataSpecificDataOffset":
            row.get("levelDataSpecificDataOffset"),
        "levelDataEmptySuffixEndOffset":
            row.get("levelDataEmptySuffixEndOffset"),
        "levelDataFinalBoundaryValidation":
            str(row.get("levelDataFinalBoundaryValidation") or ""),
        "progressLockConditionStatus":
            str(row.get("progressLockConditionStatus") or ""),
        "progressLockConditionUnionTag":
            row.get("progressLockConditionUnionTag"),
        "progressLockConditionSerializedMemberCount":
            row.get("progressLockConditionSerializedMemberCount"),
        "progressLockConditionType":
            str(row.get("progressLockConditionType") or ""),
        "progressLockConditionOperator":
            row.get("progressLockConditionOperator"),
        "progressLockSerializedRuntimeFlag":
            row.get("progressLockSerializedRuntimeFlag"),
        "progressLockConditionTree":
            row.get("progressLockConditionTree"),
        "progressLockConditions": [
            dict(condition)
            for condition in row.get("progressLockConditions") or []
            if isinstance(condition, dict)
        ],
        "rawTypeId": str(row.get("rawTypeId") or ""),
        "entityDetailIds": unique_route_strings(row.get("entityDetailIds")),
        "entityTemplateIds": unique_route_strings(row.get("entityTemplateIds")),
        "parentStoryKey": parent_story_key,
        "timelineIds": timeline_ids,
        "embeddedLineIds": embedded_line_ids,
        "embeddedOptionIds": embedded_option_ids,
        "beforeParentLineIds": before_parent_line_ids,
        "afterParentLineIds": after_parent_line_ids,
        "placementBoundary": str(row.get("placementBoundary") or ""),
        "graphEffect": str(row.get("graphEffect") or ""),
        "controlPathCount": int(row.get("nativeControlPathCount") or len(native_paths)),
        "nativePaths": native_paths,
        "sourceFiles": source_files,
        "serverMessage": str(row.get("serverMessage") or ""),
        "serverFields": unique_route_strings(row.get("serverFields")),
        "upstreamServerStateSources": unique_route_strings(
            row.get("upstreamServerStateSources")
        ),
        "serverExchange": row.get("serverExchange"),
        "clientRequest": row.get("clientRequest"),
        "expectedClientReply": row.get("expectedClientReply"),
        "npcProxyId": str(row.get("npcProxyId") or ""),
        "candidateQuestIds": unique_route_strings(
            row.get("candidateQuestIds")
        ),
        "activeRowIndex": row.get("activeRowIndex"),
        "configuredDialogIds": unique_route_strings(
            row.get("configuredDialogIds")
        ),
        "selectionOrderStatus": str(
            row.get("selectionOrderStatus") or ""
        ),
        "questTriggerStatus": str(row.get("questTriggerStatus") or ""),
        "candidateQuestTopology": (
            copy.deepcopy(row.get("candidateQuestTopology"))
            if isinstance(row.get("candidateQuestTopology"), dict)
            else None
        ),
        "steps": steps,
    }


def story_trigger_route_sort_key(route: dict[str, Any]) -> tuple:
    """Keep direct playback/condition routes ahead of context diagnostics."""
    causality = str(route.get("causality") or "")
    causality_rank = {
        "playback": 0,
        "condition": 1,
        "dependency": 2,
        "context": 3,
        "playback_owner_unresolved": 4,
        "context_owner_unresolved": 5,
        "definition_only": 6,
    }.get(causality, 7)
    return (
        causality_rank,
        _natural_quest_key(str(route.get("missionId") or "")),
        _natural_quest_key(str(route.get("questId") or "")),
        str(route.get("relation") or ""),
    )
