"""Project exact post-playback variable setter/listener candidates."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

if __package__ and __package__.startswith("scripts."):
    from scripts.common import compact_dict as _compact_dict
else:
    from common import compact_dict as _compact_dict


def build_post_playback_variable_bridge_audit(
    native_story_playback_index: dict[str, list[dict[str, Any]]],
    *,
    setter_actions: set[str],
    listener_fields: dict[str, str],
    post_playback_control_projector: Any,
) -> dict[str, Any]:
    """Census exact Story setter-to-listener candidates without promoting them.

    The installed ActionBase formatter identifies the three setter classes and
    their MemoryPack runtime shape carries a key/value pair. Exact native event
    payloads independently identify property and blackboard listener keys. A
    candidate requires the same level, same LevelScript, and exact key; class
    names, file order, Story names, and numeric ids never participate.

    Even a candidate remains context-only until the installed generic
    ``Set<T>.Execute`` body proves which notification family it emits. The
    current build has no candidate, which closes this route more strongly: no
    execution-semantics assumption could create a Story-to-Story edge.
    """
    listeners: dict[tuple[str, str, str], dict[tuple[Any, ...], dict[str, Any]]] = (
        defaultdict(dict)
    )
    setters: dict[tuple[Any, ...], dict[str, Any]] = {}
    occurrence_count = 0
    for story_key, occurrences in sorted(native_story_playback_index.items()):
        for occurrence in occurrences:
            occurrence_count += 1
            level_id = str(occurrence.get("levelId") or "")
            script_id = str(occurrence.get("scriptId") or "")
            source_file = str(occurrence.get("sourceFile") or "")
            playback_local_id = occurrence.get("localId")
            if not level_id or not script_id or not source_file:
                continue
            for owner in occurrence.get("nativeEventOwners") or []:
                if not isinstance(owner, dict):
                    continue
                detail = owner.get("eventDetail") or {}
                if (
                    owner.get("status") not in {
                        "exact_serialized_control_path",
                        "exact_serialized_control_path_equivalent_duplicates",
                        "exact_serialized_control_path_runtime_shadowing",
                    }
                    or detail.get("payloadSchemaStatus")
                    != "exact_current_build_memorypack_fields"
                ):
                    continue
                for field, listener_kind in (
                    listener_fields.items()
                ):
                    variable_key = str(detail.get(field) or "")
                    if not variable_key:
                        continue
                    listener = _compact_dict({
                        "storyKey": story_key,
                        "listenerKind": listener_kind,
                        "eventName": str(owner.get("headerName") or ""),
                        "headerLocalId": owner.get("headerLocalId"),
                        "levelId": level_id,
                        "scriptId": script_id,
                        "variableKey": variable_key,
                        "sourceFile": source_file,
                    })
                    signature = (
                        story_key,
                        listener_kind,
                        listener.get("eventName"),
                        listener.get("headerLocalId"),
                        source_file,
                    )
                    listeners[(level_id, script_id, variable_key)][signature] = (
                        listener
                    )
                if not isinstance(playback_local_id, int):
                    continue
                control = post_playback_control_projector(
                    owner,
                    story_key=story_key,
                    playback_local_id=playback_local_id,
                    source_file=source_file,
                )
                for action in control.get("actions") or []:
                    action_name = str(action.get("actionName") or "")
                    if action_name not in setter_actions:
                        continue
                    keys = sorted({
                        str(value)
                        for value in action.get("texts") or []
                        if str(value) and not str(value).startswith(("$", "#"))
                    })
                    if len(keys) != 1:
                        continue
                    variable_key = keys[0]
                    setter = {
                        "storyKey": story_key,
                        "levelId": level_id,
                        "scriptId": script_id,
                        "playbackLocalId": playback_local_id,
                        "setterLocalId": action.get("localId"),
                        "setterAction": action_name,
                        "variableKey": variable_key,
                        "sourceFile": source_file,
                    }
                    signature = (
                        story_key,
                        level_id,
                        script_id,
                        playback_local_id,
                        action.get("localId"),
                        action_name,
                        variable_key,
                        source_file,
                    )
                    setters[signature] = setter

    setter_rows: list[dict[str, Any]] = []
    exact_match_count = 0
    cross_story_match_count = 0
    for setter in setters.values():
        matches = sorted(
            listeners.get((
                setter["levelId"],
                setter["scriptId"],
                setter["variableKey"],
            ), {}).values(),
            key=lambda row: (
                str(row.get("storyKey") or ""),
                str(row.get("listenerKind") or ""),
                int(row.get("headerLocalId") or -1),
            ),
        )
        exact_match_count += len(matches)
        cross_story_matches = [
            match
            for match in matches
            if match.get("storyKey") != setter.get("storyKey")
        ]
        cross_story_match_count += len(cross_story_matches)
        setter_rows.append({
            **setter,
            "exactListenerMatches": matches,
            "crossStoryListenerMatchCount": len(cross_story_matches),
            "orderEvidence": False,
            "missionOwnershipEvidence": False,
        })
    setter_rows.sort(key=lambda row: (
        str(row.get("levelId") or ""),
        str(row.get("scriptId") or ""),
        int(row.get("setterLocalId") or -1),
        str(row.get("storyKey") or ""),
    ))
    listener_rows = [
        row
        for bucket in listeners.values()
        for row in bucket.values()
    ]
    return {
        "schema": "postPlaybackVariableBridgeAudit.v1",
        "summary": {
            "nativeStoryKeys": len(native_story_playback_index),
            "nativePlaybackOccurrences": occurrence_count,
            "exactVariableListenerSelectors": len(listeners),
            "exactVariableListenerRows": len(listener_rows),
            "postPlaybackVariableSetters": len(setter_rows),
            "exactSetterListenerMatches": exact_match_count,
            "crossStorySetterListenerMatches": cross_story_match_count,
            "setterActions": dict(sorted(Counter(
                row["setterAction"] for row in setter_rows
            ).items())),
            "listenerKinds": dict(sorted(Counter(
                row["listenerKind"] for row in listener_rows
            ).items())),
        },
        "status": (
            "closed_no_exact_same_script_key_match"
            if exact_match_count == 0
            else "context_only_execute_notification_family_unproven"
        ),
        "setters": setter_rows,
        "evidenceBoundary": (
            "The installed formatter and exact MemoryPack payloads prove the "
            "setter classes, serialized keys, listener classes, and listener "
            "keys. They do not prove that generic Set<T>.Execute emits the "
            "property or blackboard notification family. No current setter "
            "matches any exact same-level, same-script, same-key Story listener, "
            "so this route creates no ownership, branch, or order edge."
        ),
        "usesOcrOrManualOrder": False,
    }

