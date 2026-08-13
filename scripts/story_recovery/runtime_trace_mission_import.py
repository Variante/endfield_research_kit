"""Mission/LevelScript import adapter for :mod:`runtime_trace`.

The input is JSON Lines emitted by a runtime hook.  This importer deliberately
keeps observed co-activity separate from authored mission ownership: seeing a
Story playback while a quest is active is useful runtime context, but is not a
foreign key proving that the quest owns or triggered the playback.

Run through ``python -m scripts.story_recovery.runtime_trace import --profile mission``.
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import runtime_trace_core as core


ROOT = Path(__file__).resolve().parents[2]
EVENT_SCHEMA = "missionRuntimeTrace.event.v1"
BUNDLE_SCHEMA = "missionRuntimeTrace.v1"
DEFAULT_OUTPUT = ROOT / "reports" / "story" / "recovery" / "mission_runtime_trace.json"
EVENT_KINDS = {
    "session_start",
    "mission_state",
    "quest_state",
    "levelscript_event",
    "levelscript_task",
    "action_enter",
    "story_playback",
    "session_end",
}


class TraceValidationError(ValueError):
    """Raised when a capture cannot be normalized without guessing."""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("inputs", nargs="+", type=Path, help="runtime-hook JSONL capture(s)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="defaults to the JSON output path with an .md suffix",
    )


def _fail(source: str, message: str) -> TraceValidationError:
    return TraceValidationError(f"{source}: {message}")


def _required_text(row: dict[str, Any], key: str, source: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _fail(source, f"{key} must be a non-empty string")
    return value.strip()


def _required_int(row: dict[str, Any], key: str, source: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _fail(source, f"{key} must be a non-negative integer")
    return value


def _optional_int(row: dict[str, Any], key: str, source: str) -> int | None:
    value = row.get(key)
    if value is None:
        return None
    return _required_int(row, key, source)


def _optional_text(row: dict[str, Any], key: str, source: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _fail(source, f"{key} must be null or a non-empty string")
    return value.strip()


def _required_signed_int(row: dict[str, Any], key: str, source: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail(source, f"{key} must be an integer")
    return value


def _base_event(row: dict[str, Any], source: str) -> dict[str, Any]:
    if row.get("schema") != EVENT_SCHEMA:
        raise _fail(source, f"schema must be {EVENT_SCHEMA!r}")
    kind = _required_text(row, "kind", source)
    if kind not in EVENT_KINDS:
        raise _fail(source, f"unsupported kind {kind!r}")
    monotonic_ms = row.get("monotonicMs")
    if (
        isinstance(monotonic_ms, bool)
        or not isinstance(monotonic_ms, (int, float))
        or monotonic_ms < 0
    ):
        raise _fail(source, "monotonicMs must be a non-negative number")
    event = {
        "sessionId": _required_text(row, "sessionId", source),
        "seq": _required_int(row, "seq", source),
        "monotonicMs": monotonic_ms,
        "kind": kind,
    }
    utc = _optional_text(row, "utc", source)
    if utc is not None:
        event["utc"] = utc
    thread_id = row.get("threadId")
    if thread_id is not None:
        if not isinstance(thread_id, (str, int)) or isinstance(thread_id, bool):
            raise _fail(source, "threadId must be a string or integer")
        event["threadId"] = str(thread_id)
    return event


def normalize_event(row: dict[str, Any], source: str) -> dict[str, Any]:
    event = _base_event(row, source)
    kind = event["kind"]
    if kind == "session_start":
        event["gameBuild"] = _required_text(row, "gameBuild", source)
        event["captureTool"] = _required_text(row, "captureTool", source)
        fingerprint = _optional_text(row, "exportFingerprint", source)
        if fingerprint is not None:
            event["exportFingerprint"] = fingerprint
    elif kind == "mission_state":
        event.update({
            "missionId": _required_text(row, "missionId", source),
            "state": _required_text(row, "state", source),
        })
        if not isinstance(row.get("active"), bool):
            raise _fail(source, "mission_state.active must be boolean")
        event["active"] = row["active"]
    elif kind == "quest_state":
        event.update({
            "missionId": _required_text(row, "missionId", source),
            "questId": _required_text(row, "questId", source),
            "state": _required_text(row, "state", source),
        })
        if not isinstance(row.get("active"), bool):
            raise _fail(source, "quest_state.active must be boolean")
        event["active"] = row["active"]
    elif kind == "levelscript_event":
        if "headerLocalId" not in row:
            raise _fail(
                source,
                "levelscript_event.headerLocalId must be present (use null when unavailable)",
            )
        event.update({
            "chainId": _required_text(row, "chainId", source),
            "levelId": _required_text(row, "levelId", source),
            "scriptId": _required_text(row, "scriptId", source),
            "headerLocalId": _optional_int(row, "headerLocalId", source),
            "eventName": _required_text(row, "eventName", source),
        })
        selector = row.get("selector")
        if selector is not None:
            if not isinstance(selector, dict):
                raise _fail(source, "selector must be an object when present")
            event["selector"] = selector
    elif kind == "levelscript_task":
        task_event = _required_text(row, "taskEvent", source)
        allowed_task_events = {
            "condition_result_changed",
            "objective_progress_send",
            "state_update",
            "progress_update",
            "condition_completion_applied",
            "start_finish",
            "script_set_done",
        }
        if task_event not in allowed_task_events:
            raise _fail(source, f"unsupported taskEvent {task_event!r}")
        direction = _required_text(row, "direction", source)
        if direction not in {"client_local", "client_to_server", "server_to_client"}:
            raise _fail(source, f"unsupported levelscript_task direction {direction!r}")
        if "taskId" not in row:
            raise _fail(source, "levelscript_task.taskId must be present (use null for script_set_done)")
        task_id = _optional_text(row, "taskId", source)
        if task_event != "script_set_done" and task_id is None:
            raise _fail(source, f"levelscript_task {task_event!r} requires taskId")
        event.update({
            "taskEvent": task_event,
            "direction": direction,
            "sceneNumId": _required_int(row, "sceneNumId", source),
            "scriptId": _required_text(row, "scriptId", source),
            "taskId": task_id,
        })
        message_id = row.get("messageId")
        if message_id is not None:
            event["messageId"] = _required_int(row, "messageId", source)
        for key in ("message", "conditionId", "sourceHook"):
            value = _optional_text(row, key, source)
            if value is not None:
                event[key] = value
        for key in ("progress", "taskState"):
            if row.get(key) is not None:
                event[key] = _required_signed_int(row, key, source)
        for key in ("conditionResult", "conditionMapCaptured", "conditionCompleted"):
            if row.get(key) is not None:
                if not isinstance(row[key], bool):
                    raise _fail(source, f"{key} must be boolean when present")
                event[key] = row[key]
    elif kind == "action_enter":
        event.update({
            "chainId": _required_text(row, "chainId", source),
            "levelId": _required_text(row, "levelId", source),
            "scriptId": _required_text(row, "scriptId", source),
            "actionLocalId": _required_int(row, "actionLocalId", source),
            "actionType": _required_text(row, "actionType", source),
        })
        header_local_id = _optional_int(row, "headerLocalId", source)
        if header_local_id is not None:
            event["headerLocalId"] = header_local_id
    elif kind == "story_playback":
        if "chainId" not in row:
            raise _fail(source, "story_playback.chainId must be present (use null when unavailable)")
        event.update({
            "chainId": _optional_text(row, "chainId", source),
            "storyKey": _required_text(row, "storyKey", source),
            "playbackType": _required_text(row, "playbackType", source),
        })
        for key in ("levelId", "scriptId", "actionType"):
            value = _optional_text(row, key, source)
            if value is not None:
                event[key] = value
        for key in ("headerLocalId", "actionLocalId"):
            value = _optional_int(row, key, source)
            if value is not None:
                event[key] = value
    return event


def read_events(paths: Iterable[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    return core.read_jsonl(
        paths,
        label="mission",
        normalize=normalize_event,
        validation_error=TraceValidationError,
    )


def _compact_chain_event(event: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "kind", "seq", "monotonicMs", "levelId", "scriptId", "headerLocalId",
        "eventName", "selector", "actionLocalId", "actionType",
    )
    return {key: event[key] for key in keys if key in event}


def _compact_task_event(event: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "kind", "seq", "monotonicMs", "threadId", "taskEvent", "direction",
        "messageId", "message", "sceneNumId", "scriptId", "taskId",
        "conditionId", "progress", "conditionResult", "taskState",
        "conditionMapCaptured", "conditionCompleted", "sourceHook",
    )
    return {key: event[key] for key in keys if key in event}


def build_bundle(events: list[dict[str, Any]], sources: list[str]) -> dict[str, Any]:
    sessions: dict[str, dict[str, Any]] = {}
    session_order: list[str] = []
    active_missions: dict[str, dict[str, str]] = defaultdict(dict)
    active_quests: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)
    chain_events: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    observations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    playback_by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    task_events_by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        session_id = event["sessionId"]
        session = sessions.get(session_id)
        if event["kind"] == "session_start":
            if session is not None:
                raise TraceValidationError(f"session {session_id!r} has more than one session_start")
            session = {
                "id": session_id,
                "gameBuild": event["gameBuild"],
                "captureTool": event["captureTool"],
                "exportFingerprint": event.get("exportFingerprint"),
                "firstSeq": event["seq"],
                "lastSeq": event["seq"],
                "eventCount": 0,
                "playbackCount": 0,
                "closed": False,
            }
            sessions[session_id] = session
            session_order.append(session_id)
        elif session is None:
            raise TraceValidationError(
                f"session {session_id!r} emitted {event['kind']} before session_start"
            )
        elif session["closed"]:
            raise TraceValidationError(f"session {session_id!r} emitted an event after session_end")

        assert session is not None
        if session["eventCount"] and event["seq"] <= session["lastSeq"]:
            raise TraceValidationError(
                f"session {session_id!r} seq {event['seq']} is not strictly increasing"
            )
        session["lastSeq"] = event["seq"]
        session["eventCount"] += 1

        kind = event["kind"]
        if kind == "session_end":
            session["closed"] = True
        elif kind == "mission_state":
            mission_id = event["missionId"]
            if event["active"]:
                active_missions[session_id][mission_id] = event["state"]
            else:
                active_missions[session_id].pop(mission_id, None)
                for key in [key for key in active_quests[session_id] if key[0] == mission_id]:
                    active_quests[session_id].pop(key, None)
        elif kind == "quest_state":
            key = (event["missionId"], event["questId"])
            if event["active"]:
                active_quests[session_id][key] = event["state"]
            else:
                active_quests[session_id].pop(key, None)
        elif kind in {"levelscript_event", "action_enter"}:
            chain_events[(session_id, event["chainId"])].append(event)
        elif kind == "levelscript_task":
            task_events_by_session[session_id].append(_compact_task_event(event))
        elif kind == "story_playback":
            session["playbackCount"] += 1
            chain_id = event.get("chainId")
            route = list(chain_events.get((session_id, chain_id), [])) if chain_id else []
            has_event = any(item["kind"] == "levelscript_event" for item in route)
            has_action = any(item["kind"] == "action_enter" for item in route)
            if has_event and has_action:
                trigger_status = "exact_event_action_chain"
            elif has_action:
                trigger_status = "action_chain_only"
            elif has_event:
                trigger_status = "event_chain_only"
            else:
                trigger_status = "playback_only"
            missions = [
                {"missionId": mission_id, "state": state}
                for mission_id, state in sorted(active_missions[session_id].items())
            ]
            quests = [
                {"missionId": mission_id, "questId": quest_id, "state": state}
                for (mission_id, quest_id), state in sorted(active_quests[session_id].items())
            ]
            if quests:
                ownership_status = "observed_active_quest_context"
            elif missions:
                ownership_status = "observed_active_mission_context"
            else:
                ownership_status = "no_active_mission_snapshot"
            observation = {
                "sessionId": session_id,
                "seq": event["seq"],
                "monotonicMs": event["monotonicMs"],
                "storyKey": event["storyKey"],
                "playbackType": event["playbackType"],
                "chainId": chain_id,
                "triggerStatus": trigger_status,
                "ownershipStatus": ownership_status,
                "activeMissions": missions,
                "activeQuests": quests,
                "route": [_compact_chain_event(item) for item in route],
            }
            for key in ("levelId", "scriptId", "headerLocalId", "actionLocalId", "actionType"):
                if key in event:
                    observation[key] = event[key]
            observations[event["storyKey"]].append(observation)
            playback_by_session[session_id].append(observation)

    observed_edges: list[dict[str, Any]] = []
    transition_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for session_id in session_order:
        playbacks = playback_by_session[session_id]
        for before, after in zip(playbacks, playbacks[1:]):
            before_quests = {(row["missionId"], row["questId"]) for row in before["activeQuests"]}
            after_quests = {(row["missionId"], row["questId"]) for row in after["activeQuests"]}
            before_missions = {row["missionId"] for row in before["activeMissions"]}
            after_missions = {row["missionId"] for row in after["activeMissions"]}
            shared_quests = sorted(before_quests & after_quests)
            shared_missions = sorted(before_missions & after_missions)
            if shared_quests:
                context = "same_active_quest_context"
            elif shared_missions:
                context = "same_active_mission_context"
            else:
                context = "session_sequence_only"
            edge = {
                "source": before["storyKey"],
                "target": after["storyKey"],
                "sessionId": session_id,
                "fromSeq": before["seq"],
                "toSeq": after["seq"],
                "elapsedMs": after["monotonicMs"] - before["monotonicMs"],
                "context": context,
                "sharedMissionIds": shared_missions,
                "sharedQuests": [
                    {"missionId": mission_id, "questId": quest_id}
                    for mission_id, quest_id in shared_quests
                ],
                "evidence": "observed_runtime_sequence",
            }
            observed_edges.append(edge)
            group_key = (edge["source"], edge["target"], context)
            group = transition_groups.setdefault(group_key, {
                "source": edge["source"],
                "target": edge["target"],
                "context": context,
                "observationCount": 0,
                "sessionIds": set(),
            })
            group["observationCount"] += 1
            group["sessionIds"].add(session_id)

    transitions = []
    for group in transition_groups.values():
        transitions.append({**group, "sessionIds": sorted(group["sessionIds"])})
    transitions.sort(key=lambda row: (row["source"], row["target"], row["context"]))
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    for row in transitions:
        outgoing[row["source"]].add(row["target"])
        incoming[row["target"]].add(row["source"])

    normalized_sessions = []
    for session_id in session_order:
        row = dict(sessions[session_id])
        if row.get("exportFingerprint") is None:
            row.pop("exportFingerprint", None)
        normalized_sessions.append(row)
    story_observations = {
        key: sorted(rows, key=lambda row: (row["sessionId"], row["seq"]))
        for key, rows in sorted(observations.items())
    }
    observation_count = sum(len(rows) for rows in story_observations.values())
    exact_chain_count = sum(
        row["triggerStatus"] == "exact_event_action_chain"
        for rows in story_observations.values()
        for row in rows
    )
    active_quest_count = sum(
        row["ownershipStatus"] == "observed_active_quest_context"
        for rows in story_observations.values()
        for row in rows
    )
    normalized_task_events = {
        session_id: sorted(rows, key=lambda row: row["seq"])
        for session_id, rows in sorted(task_events_by_session.items())
    }
    task_event_count = sum(len(rows) for rows in normalized_task_events.values())
    exact_task_identity_count = sum(
        bool(row.get("taskId"))
        for rows in normalized_task_events.values()
        for row in rows
    )
    return {
        "_schema": BUNDLE_SCHEMA,
        "generated": int(time.time()),
        "evidencePolicy": {
            "classification": "observed_runtime",
            "trigger": (
                "A trigger route is exact only when one capture chain contains the "
                "LevelScript event, entered action, and Story playback identity."
            ),
            "ownership": (
                "Active mission/quest snapshots are temporal context, not authored ownership. "
                "They must not replace or promote source-backed Story connections."
            ),
            "ordering": (
                "Observed edges preserve actual playback sequence per session. They are an "
                "overlay and must not be merged into sourceStoryPartialOrder as authored order."
            ),
            "tasks": (
                "Decoded LevelScript task events preserve exact scene/script/task identity "
                "when present. Synchronous task context nested inside a LevelScript event is "
                "native causal context; it still supplies no mission or quest foreign key."
            ),
        },
        "sources": sources,
        "summary": {
            "sessions": len(normalized_sessions),
            "events": len(events),
            "storyFiles": len(story_observations),
            "storyPlaybacks": observation_count,
            "exactEventActionChains": exact_chain_count,
            "activeQuestContextPlaybacks": active_quest_count,
            "levelScriptTaskEvents": task_event_count,
            "exactTaskIdentityEvents": exact_task_identity_count,
            "observedEdges": len(observed_edges),
            "distinctTransitions": len(transitions),
            "observedForks": sum(len(targets) > 1 for targets in outgoing.values()),
            "observedMerges": sum(len(sources_) > 1 for sources_ in incoming.values()),
        },
        "sessions": normalized_sessions,
        "storyObservations": story_observations,
        "levelScriptTaskEvents": normalized_task_events,
        "observedEdges": observed_edges,
        "transitions": transitions,
        "observedForks": [
            {"source": source, "targets": sorted(targets)}
            for source, targets in sorted(outgoing.items()) if len(targets) > 1
        ],
        "observedMerges": [
            {"target": target, "sources": sorted(sources_)}
            for target, sources_ in sorted(incoming.items()) if len(sources_) > 1
        ],
    }


def normalize_files(paths: Iterable[Path]) -> dict[str, Any]:
    events, sources = read_events(paths)
    return build_bundle(events, sources)


def render_markdown(bundle: dict[str, Any]) -> str:
    summary = bundle["summary"]
    lines = [
        "# Mission runtime trace",
        "",
        "This report is observed runtime evidence. Active mission/quest state is temporal "
        "context and is not promoted to authored Story ownership.",
        "",
        "## Summary",
        "",
        f"- Sessions: `{summary['sessions']}`",
        f"- Events: `{summary['events']}`",
        f"- Story playbacks/files: `{summary['storyPlaybacks']}` / `{summary['storyFiles']}`",
        f"- Exact event/action/playback chains: `{summary['exactEventActionChains']}`",
        f"- Playbacks with active quest context: `{summary['activeQuestContextPlaybacks']}`",
        f"- LevelScript task events/exact task identities: `{summary['levelScriptTaskEvents']}` / `{summary['exactTaskIdentityEvents']}`",
        f"- Observed sequence edges/distinct transitions: `{summary['observedEdges']}` / `{summary['distinctTransitions']}`",
        f"- Observed forks/merges: `{summary['observedForks']}` / `{summary['observedMerges']}`",
        "",
        "## Capture requirements",
        "",
        "Each session starts with `session_start`. Emit mission and quest snapshots with an "
        "explicit `active` boolean; emit a unique `chainId` through `_RaiseOnScriptEvent`, "
        "ActionHeader/ActionBase dispatch, and the final Story playback call. Use an explicit "
        "null `chainId` when asynchronous propagation is unavailable.",
        "",
        "## Boundary",
        "",
        bundle["evidencePolicy"]["ownership"],
        "",
        bundle["evidencePolicy"]["ordering"],
        "",
        bundle["evidencePolicy"]["tasks"],
        "",
    ]
    return "\n".join(lines)


def import_trace(args: argparse.Namespace) -> int:
    bundle = normalize_files(args.inputs)
    output = args.output.resolve()
    core.write_report(
        output,
        bundle,
        render_markdown(bundle),
        args.markdown_output,
    )
    summary = bundle["summary"]
    print(
        f"Mission runtime trace: {summary['storyPlaybacks']} playbacks, "
        f"{summary['exactEventActionChains']} exact chains, "
        f"{summary['observedEdges']} observed edges -> {output}"
    )
    return 0
