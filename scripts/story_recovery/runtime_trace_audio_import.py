r"""Audio import adapter for :mod:`runtime_trace`.

The importer joins numeric Wwise Event hashes to the current exported audio
index only as a static name/media candidate. It never upgrades an observed
Adapter request into Wwise acceptance or audible playback.

Run through ``python -m scripts.story_recovery.runtime_trace import --profile audio``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import runtime_trace_core as core


ROOT = Path(__file__).resolve().parents[2]
EVENT_SCHEMA = "audioRuntimeTrace.event.v1"
BUNDLE_SCHEMA = "audioRuntimeTrace.v1"
EVENT_KINDS = {
    "session_start",
    "audio_request",
    "audio_request_result",
    "audio_control_request",
    "audio_control_result",
    "audio_carrier_enter",
    "audio_carrier_leave",
    "session_end",
}
DEFAULT_OUTPUT = ROOT / "reports" / "story" / "recovery" / "audio_runtime_trace.json"
DEFAULT_INDEX = ROOT / "export_full" / "structured" / "Audio" / "CN" / "index.json"
DEFAULT_TRIGGER_CONTEXTS = ROOT / "webui" / "data" / "lang" / "CN" / "audio" / "trigger_contexts.json"
MAX_TRIGGER_CONTEXT_SAMPLES = 12
TRIGGER_CONTEXT_SCHEMA_VERSION = 4


class AudioTraceValidationError(ValueError):
    """Raised when an audio trace cannot be normalized safely."""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--audio-index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--trigger-contexts", type=Path, default=DEFAULT_TRIGGER_CONTEXTS)


def fail(source: str, message: str) -> AudioTraceValidationError:
    return AudioTraceValidationError(f"{source}: {message}")


def optional_text(row: dict[str, Any], key: str, source: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise fail(source, f"{key} must be null or non-empty text")
    return value.strip()


def base_event(row: dict[str, Any], source: str) -> dict[str, Any]:
    if row.get("schema") != EVENT_SCHEMA:
        raise fail(source, f"schema must be {EVENT_SCHEMA!r}")
    kind = optional_text(row, "kind", source)
    if kind not in EVENT_KINDS:
        raise fail(source, f"unsupported kind {kind!r}")
    session_id = optional_text(row, "sessionId", source)
    if session_id is None:
        raise fail(source, "sessionId is required")
    seq = row.get("seq")
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
        raise fail(source, "seq must be a non-negative integer")
    monotonic = row.get("monotonicMs")
    if isinstance(monotonic, bool) or not isinstance(monotonic, (int, float)) or monotonic < 0:
        raise fail(source, "monotonicMs must be a non-negative number")
    event = {
        "schema": EVENT_SCHEMA,
        "sessionId": session_id,
        "seq": seq,
        "monotonicMs": monotonic,
        "kind": kind,
    }
    utc = optional_text(row, "utc", source)
    if utc is not None:
        event["utc"] = utc
    thread_id = row.get("threadId")
    if thread_id is not None:
        if isinstance(thread_id, bool) or not isinstance(thread_id, (int, str)):
            raise fail(source, "threadId must be a string or integer")
        event["threadId"] = str(thread_id)
    if row.get("runtimeExecutionObserved") is not None:
        if not isinstance(row["runtimeExecutionObserved"], bool):
            raise fail(source, "runtimeExecutionObserved must be boolean")
        event["runtimeExecutionObserved"] = row["runtimeExecutionObserved"]
    return event


def normalize_event(row: dict[str, Any], source: str) -> dict[str, Any]:
    event = base_event(row, source)
    kind = event["kind"]
    if kind == "session_start":
        for key in ("gameBuild", "captureTool"):
            value = optional_text(row, key, source)
            if value is None:
                raise fail(source, f"{key} is required for session_start")
            event[key] = value
        for key in ("exportFingerprint", "language", "expectedModulePath", "attachedModulePath"):
            value = optional_text(row, key, source)
            if value is not None:
                event[key] = value
        for key in ("expectedModuleSize", "attachedModuleSize"):
            value = row.get(key)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise fail(source, f"{key} must be a non-negative integer")
                event[key] = value
        if row.get("evidenceBoundary") is not None:
            if not isinstance(row["evidenceBoundary"], dict):
                raise fail(source, "evidenceBoundary must be an object")
            event["evidenceBoundary"] = row["evidenceBoundary"]
    elif kind == "session_end":
        for key in ("attachedModulePath",):
            value = optional_text(row, key, source)
            if value is not None:
                event[key] = value
        for key in ("attachedModuleSize",):
            value = row.get(key)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise fail(source, f"{key} must be a non-negative integer")
                event[key] = value
        for key in ("modulePathMatch", "moduleSizeMatch"):
            value = row.get(key)
            if value is not None:
                if not isinstance(value, bool):
                    raise fail(source, f"{key} must be boolean")
                event[key] = value
    else:
        source_kind = optional_text(row, "sourceKind", source)
        hook_name = optional_text(row, "hookName", source)
        if source_kind is None or hook_name is None:
            raise fail(source, f"{kind} requires sourceKind and hookName")
        event["sourceKind"] = source_kind
        event["hookName"] = hook_name
        for key in ("captureId", "parentCaptureId", "token", "rva"):
            value = optional_text(row, key, source)
            if value is not None:
                event[key] = value
        method_index = row.get("methodIndex")
        if method_index is not None:
            if isinstance(method_index, bool) or not isinstance(method_index, int) or method_index < 0:
                raise fail(source, "methodIndex must be a non-negative integer")
            event["methodIndex"] = method_index
        if row.get("arguments") is not None:
            if not isinstance(row["arguments"], dict):
                raise fail(source, "arguments must be an object")
            event["arguments"] = row["arguments"]
        if row.get("activeContexts") is not None:
            if not isinstance(row["activeContexts"], list):
                raise fail(source, "activeContexts must be a list")
            event["activeContexts"] = row["activeContexts"]
        if row.get("instancePointer") is not None:
            event["instancePointer"] = str(row["instancePointer"])
        if row.get("returnValue") is not None:
            event["returnValue"] = row["returnValue"]
        if row.get("requestArguments") is not None:
            if not isinstance(row["requestArguments"], dict):
                raise fail(source, "requestArguments must be an object")
            event["requestArguments"] = row["requestArguments"]
        if row.get("captureId") is not None:
            event["captureId"] = row["captureId"]
    return event


def read_events(paths: Iterable[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    return core.read_jsonl(
        paths,
        label="audio",
        normalize=normalize_event,
        validation_error=AudioTraceValidationError,
    )


def read_json_input(path: Path, label: str) -> tuple[Any | None, dict[str, Any]]:
    status: dict[str, Any] = {
        "label": label,
        "path": str(path.resolve()),
        "status": "missing",
        "sha256": None,
    }
    if not path.is_file():
        status["reason"] = "file_missing"
        return None, status
    try:
        raw = path.read_bytes()
        status["sha256"] = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        status.update({"status": "degraded", "reason": f"invalid_json:{type(exc).__name__}"})
        return None, status
    if not isinstance(payload, dict):
        status.update({"status": "degraded", "reason": "root_not_object"})
        return None, status
    status.update({
        "status": "ready",
        "language": payload.get("language"),
        "schemaVersion": payload.get("schemaVersion"),
    })
    return payload, status


def apply_expected_language(status: dict[str, Any], expected_language: str | None) -> None:
    if not expected_language or status.get("status") not in {"ready", "degraded"}:
        return
    status["expectedLanguage"] = expected_language
    language = status.get("language")
    status["languageMatch"] = language == expected_language
    if not status["languageMatch"] and status.get("status") == "ready":
        status.update({"status": "degraded", "reason": "language_mismatch"})


def load_event_index_with_status(
    path: Path,
    expected_language: str | None = None,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    payload, status = read_json_input(path, "audioIndex")
    apply_expected_language(status, expected_language)
    if status.get("status") != "ready" or payload is None:
        return {}, status
    rows = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        status.update({"status": "degraded", "reason": "events_not_list"})
        return {}, status
    status["eventCount"] = len(rows)
    lookup: dict[int, dict[str, Any]] = {}
    names: dict[int, set[str]] = defaultdict(set)
    media: dict[int, set[str]] = defaultdict(set)
    categories: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_hash = row.get("eventHash")
        if isinstance(raw_hash, bool) or not isinstance(raw_hash, int):
            continue
        event_hash = raw_hash & 0xFFFFFFFF
        name = row.get("eventId") or row.get("id") or row.get("name")
        if isinstance(name, str) and name:
            names[event_hash].add(name)
        rel = row.get("rel") or row.get("src")
        if isinstance(rel, str) and rel:
            media[event_hash].add(rel)
        category = row.get("eventCategory") or row.get("audioCategory")
        if isinstance(category, str) and category:
            categories[event_hash].add(category)
    for event_hash in names:
        lookup[event_hash] = {
            "eventHash": event_hash,
            "names": sorted(names[event_hash]),
            "mediaCandidates": sorted(media[event_hash]),
            "categories": sorted(categories[event_hash]),
        }
    status["indexedEventHashCount"] = len(lookup)
    return lookup, status


def load_event_index(path: Path) -> dict[int, dict[str, Any]]:
    return load_event_index_with_status(path)[0]


def numeric_event_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    if isinstance(value, str):
        text = value.strip()
        try:
            if text.lower().startswith("0x"):
                return int(text, 16) & 0xFFFFFFFF
            if text.lstrip("-").isdigit():
                return int(text) & 0xFFFFFFFF
        except ValueError:
            return None
    return None


def _trigger_context_ref(context: dict[str, Any]) -> dict[str, Any]:
    situation = context.get("situation") if isinstance(context.get("situation"), dict) else {}
    meaning = context.get("meaning") if isinstance(context.get("meaning"), dict) else {}
    owner = context.get("owner") if isinstance(context.get("owner"), dict) else {}
    selection = context.get("selection") if isinstance(context.get("selection"), dict) else {}
    ref: dict[str, Any] = {}
    for key in ("triggerId", "semanticKind", "triggerRole", "runtimeActivationStatus"):
        value = context.get(key)
        if isinstance(value, str) and value:
            ref[key] = value
    compact_situation = {}
    for key in (
        "eventId", "eventHash", "dialogId", "dialogKey", "timelineId", "lineId",
        "radioId", "envTalkId", "envTalkVariant", "mission", "remoteCommonId", "singleId", "middleId",
        "index", "autoPlayTime", "timelineStartSec", "timelineDurationSec",
    ):
        value = situation.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            compact_situation[key] = value
    if compact_situation:
        ref["situation"] = compact_situation
    compact_meaning = {}
    for key in ("eventId", "audio", "category", "foundInWwise", "possibleMediaCount"):
        value = meaning.get(key)
        if isinstance(value, (str, int, float, bool)):
            compact_meaning[key] = value
    if compact_meaning:
        ref["meaning"] = compact_meaning
    compact_owner = {}
    for key in (
        "dialogId", "dialogKey", "timelineId", "levelScriptId", "radioId",
        "envTalkId", "remoteCommonId", "singleId", "middleId", "voiceId",
        "sourceTable", "speakerActorId", "speakerChannel",
        "timelineAssetName",
    ):
        value = owner.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool) and value != "":
            compact_owner[key] = value
    if compact_owner:
        ref["owner"] = compact_owner
    if isinstance(situation.get("autoPlay"), bool):
        ref["autoPlay"] = situation["autoPlay"]
    media_ids = []
    media_refs = context.get("mediaRefs")
    if isinstance(media_refs, list):
        for media in media_refs:
            if isinstance(media, dict):
                value = media.get("id") or media.get("rel")
                if isinstance(value, str) and value and value not in media_ids:
                    media_ids.append(value)
            if len(media_ids) >= 8:
                break
    if media_ids:
        ref["mediaIds"] = media_ids
    media_status = selection.get("mediaSelectionStatus")
    if isinstance(media_status, str) and media_status:
        ref["mediaSelectionStatus"] = media_status
    source_refs = context.get("sourceRefs")
    if isinstance(source_refs, list):
        ref["sourceRefs"] = [value for value in source_refs if isinstance(value, str)][:4]
    return ref


def load_trigger_context_index_with_status(
    path: Path,
    expected_language: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    payload, status = read_json_input(path, "triggerContexts")
    apply_expected_language(status, expected_language)
    if status.get("status") != "ready" or payload is None:
        return {}, status
    if payload.get("schemaVersion") != TRIGGER_CONTEXT_SCHEMA_VERSION:
        status.update({"status": "degraded", "reason": "schema_version_mismatch"})
        return {}, status
    contexts = payload.get("contexts") if isinstance(payload, dict) else None
    if not isinstance(contexts, list):
        status.update({"status": "degraded", "reason": "contexts_not_list"})
        return {}, status
    status["contextCount"] = len(contexts)
    lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    def add(key: str, ref: dict[str, Any]) -> None:
        if not key:
            return
        identity = (key, str(ref.get("triggerId") or ""))
        if identity in seen:
            return
        seen.add(identity)
        lookup[key].append(ref)

    for context in contexts:
        if not isinstance(context, dict):
            continue
        ref = _trigger_context_ref(context)
        if not ref:
            continue
        situation = context.get("situation") if isinstance(context.get("situation"), dict) else {}
        meaning = context.get("meaning") if isinstance(context.get("meaning"), dict) else {}
        event_hash = numeric_event_id(situation.get("eventHash"))
        if event_hash is None:
            event_hash = numeric_event_id(meaning.get("hash"))
        if event_hash is not None:
            add(f"hash:{event_hash}", ref)
        for value in (
            situation.get("eventId"),
            meaning.get("eventId"),
            meaning.get("audio"),
        ):
            if isinstance(value, str) and value.strip():
                add(f"key:{value.strip().lower()}", ref)
        media_refs = context.get("mediaRefs")
        if isinstance(media_refs, list):
            for media in media_refs:
                if isinstance(media, dict) and isinstance(media.get("id"), str) and media["id"].strip():
                    add(f"key:{media['id'].strip().lower()}", ref)
    status["indexedKeyCount"] = len(lookup)
    status["indexedReferenceCount"] = sum(len(values) for values in lookup.values())
    return dict(lookup), status


def load_trigger_context_index(path: Path) -> dict[str, list[dict[str, Any]]]:
    return load_trigger_context_index_with_status(path)[0]


def static_trigger_context_candidates(
    event: dict[str, Any], lookup: dict[str, list[dict[str, Any]]]
) -> dict[str, Any] | None:
    arguments = event.get("arguments") or event.get("requestArguments") or {}
    if not isinstance(arguments, dict):
        return None
    keys: list[str] = []
    event_key = arguments.get("eventKey")
    if isinstance(event_key, str) and event_key.strip():
        keys.append(f"key:{event_key.strip().lower()}")
    event_hash = numeric_event_id(arguments.get("eventId"))
    if event_hash is not None:
        keys.append(f"hash:{event_hash}")
    resolution = event.get("eventResolution")
    if isinstance(resolution, dict):
        for name in resolution.get("eventNameCandidates", []):
            if isinstance(name, str) and name:
                keys.append(f"key:{name.strip().lower()}")
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in keys:
        for candidate in lookup.get(key, []):
            identity = str(candidate.get("triggerId") or id(candidate))
            if identity not in seen:
                seen.add(identity)
                candidates.append(candidate)
    if not candidates:
        return None
    by_kind = Counter(str(candidate.get("semanticKind") or "unknown") for candidate in candidates)
    return {
        "candidateCount": len(candidates),
        "bySemanticKind": dict(sorted(by_kind.items())),
        "samples": candidates[:MAX_TRIGGER_CONTEXT_SAMPLES],
        "truncated": len(candidates) > MAX_TRIGGER_CONTEXT_SAMPLES,
        "evidenceBoundary": "static trigger-context candidate join; not runtime ownership or execution proof",
    }


def event_resolution(event: dict[str, Any], lookup: dict[int, dict[str, Any]]) -> dict[str, Any]:
    arguments = event.get("arguments") or event.get("requestArguments") or {}
    if not isinstance(arguments, dict):
        return {}
    key = arguments.get("eventKey")
    if isinstance(key, str) and key:
        return {"eventKey": key, "resolution": "observedStringKey"}
    raw_id = arguments.get("eventId")
    event_hash = numeric_event_id(raw_id)
    if event_hash is None:
        return {}
    result: dict[str, Any] = {"eventId": event_hash}
    candidate = lookup.get(event_hash)
    if candidate:
        result.update({
            "eventNameCandidates": candidate["names"],
            "mediaCandidates": candidate["mediaCandidates"],
            "categories": candidate["categories"],
            "resolution": "staticEventHashJoin",
        })
    else:
        result["resolution"] = "unresolvedEventHash"
    return result


def build_bundle(
    events: list[dict[str, Any]],
    sources: list[str],
    index_path: Path,
    trigger_context_path: Path | None = None,
) -> dict[str, Any]:
    sessions: dict[str, dict[str, Any]] = {}
    session_order: list[str] = []
    last_seq: dict[str, int] = {}
    closed: set[str] = set()
    by_capture: dict[tuple[str, str], dict[str, Any]] = {}
    observations: list[dict[str, Any]] = []
    counts = Counter()
    trace_languages = sorted({
        str(event.get("language"))
        for event in events
        if event.get("kind") == "session_start" and event.get("language")
    })
    expected_language = trace_languages[0] if len(trace_languages) == 1 else None
    lookup, audio_index_input = load_event_index_with_status(index_path, expected_language)
    if len(trace_languages) > 1:
        audio_index_input.update({"status": "degraded", "reason": "multiple_trace_languages", "traceLanguages": trace_languages})
    if trigger_context_path:
        trigger_lookup, trigger_context_input = load_trigger_context_index_with_status(
            trigger_context_path,
            expected_language,
        )
        if len(trace_languages) > 1:
            trigger_context_input.update({"status": "degraded", "reason": "multiple_trace_languages", "traceLanguages": trace_languages})
    else:
        trigger_lookup = {}
        trigger_context_input = {"status": "not_requested", "path": None}
    join_inputs = [audio_index_input]
    if trigger_context_path:
        join_inputs.append(trigger_context_input)
    join_status = "ready" if all(item.get("status") == "ready" for item in join_inputs) else "degraded"
    trigger_context_matches = 0
    trigger_context_candidates = 0

    for event in events:
        session_id = event["sessionId"]
        kind = event["kind"]
        if kind == "session_start":
            if session_id in sessions:
                raise AudioTraceValidationError(f"session {session_id!r} has duplicate session_start")
            sessions[session_id] = {
                "id": session_id,
                "gameBuild": event["gameBuild"],
                "captureTool": event["captureTool"],
                "language": event.get("language"),
                "expectedModulePath": event.get("expectedModulePath"),
                "expectedModuleSize": event.get("expectedModuleSize"),
                "attachedModulePath": event.get("attachedModulePath"),
                "attachedModuleSize": event.get("attachedModuleSize"),
                "eventCount": 0,
                "closed": False,
            }
            session_order.append(session_id)
        elif session_id not in sessions:
            raise AudioTraceValidationError(f"session {session_id!r} emitted {kind} before session_start")
        if session_id in closed:
            raise AudioTraceValidationError(f"session {session_id!r} emitted {kind} after session_end")
        prior = last_seq.get(session_id)
        if prior is not None and event["seq"] <= prior:
            raise AudioTraceValidationError(f"session {session_id!r} sequence is not strictly increasing")
        last_seq[session_id] = event["seq"]
        sessions[session_id]["eventCount"] += 1
        counts[kind] += 1
        if kind == "session_end":
            for key in ("attachedModulePath", "attachedModuleSize", "modulePathMatch", "moduleSizeMatch"):
                if key in event:
                    sessions[session_id][key] = event[key]
            closed.add(session_id)
            sessions[session_id]["closed"] = True
            continue
        if kind in {"audio_request", "audio_control_request", "audio_carrier_enter"}:
            capture_id = event.get("captureId")
            if isinstance(capture_id, str) and capture_id:
                by_capture[(session_id, capture_id)] = event
        if kind in {"audio_request_result", "audio_control_result", "audio_carrier_leave"}:
            capture_id = event.get("captureId")
            request = by_capture.get((session_id, capture_id)) if isinstance(capture_id, str) else None
            if request and request.get("arguments") is not None:
                event["requestArguments"] = request["arguments"]
                event["requestSourceKind"] = request.get("sourceKind")
                event["requestHookName"] = request.get("hookName")
        if kind not in {"session_start", "session_end"}:
            resolution = event_resolution(event, lookup)
            if resolution:
                event["eventResolution"] = resolution
            trigger_match = static_trigger_context_candidates(event, trigger_lookup)
            if trigger_match:
                event["staticTriggerContextCandidates"] = trigger_match
                trigger_context_matches += 1
                trigger_context_candidates += trigger_match["candidateCount"]
            observations.append(event)

    if not session_order:
        raise AudioTraceValidationError("audio runtime trace has no session_start")
    module_verification_rows = []
    for session_id in session_order:
        session = sessions[session_id]
        facts = {
            key: session[key]
            for key in ("modulePathMatch", "moduleSizeMatch")
            if key in session
        }
        if facts:
            module_verification_rows.append({"sessionId": session_id, **facts})
    if not module_verification_rows:
        runtime_evidence_status = "notRecorded"
    elif all(
        row.get("modulePathMatch") is True and row.get("moduleSizeMatch") is True
        for row in module_verification_rows
    ) and all(
        "modulePathMatch" in row and "moduleSizeMatch" in row
        for row in module_verification_rows
    ):
        runtime_evidence_status = "verified"
    else:
        runtime_evidence_status = "degraded"
    unresolved = Counter()
    resolved = Counter()
    for event in observations:
        resolution = event.get("eventResolution")
        if not isinstance(resolution, dict):
            continue
        identifier = resolution.get("eventId")
        if identifier is None:
            identifier = resolution.get("eventKey")
        if resolution.get("resolution") in {"staticEventHashJoin", "observedStringKey"}:
            resolved[str(identifier)] += 1
        else:
            unresolved[str(identifier)] += 1
    return {
        "schema": BUNDLE_SCHEMA,
        "eventSchema": EVENT_SCHEMA,
        "sources": sources,
        "audioIndex": str(index_path.resolve()),
        "audioIndexInput": audio_index_input,
        "joinStatus": join_status,
        "runtimeEvidenceStatus": runtime_evidence_status,
        "moduleVerification": module_verification_rows,
        "sessions": [sessions[session_id] for session_id in session_order],
        "countsByKind": dict(sorted(counts.items())),
        "observationCount": len(observations),
        "resolvedEventObservationCount": sum(resolved.values()),
        "unresolvedEventObservationCount": sum(unresolved.values()),
        "resolvedEventObservationsById": dict(sorted(resolved.items())),
        "unresolvedEventObservationsById": dict(sorted(unresolved.items())),
        "observations": observations,
        "triggerContexts": {
            "path": str(trigger_context_path.resolve()) if trigger_context_path else None,
            "input": trigger_context_input,
            "matchedObservationCount": trigger_context_matches,
            "candidateContextCount": trigger_context_candidates,
            "evidenceBoundary": "static trigger-context candidate join; not runtime ownership or execution proof",
        },
        "evidenceBoundary": {
            "runtimeExecution": "carrier and Adapter hook entries are observed managed execution",
            "moduleVerification": "runtime observations are verified only when the attached module path and size match the hash-locked GameAssembly; missing or mismatched facts are not equivalent to verified runtime evidence",
            "adapterBoundary": "AudioAdapter request entry is observed request evidence, not proof of Wwise acceptance",
            "eventHashJoin": "eventHash-to-name/media is a static exported-index candidate join",
            "joinInputs": "missing, malformed, language-mismatched, or schema-mismatched static inputs produce degraded status and no candidates from that input",
            "audibility": "no observation here proves selected Wwise branch, decoded leaf, or audibility",
        },
    }


def markdown(bundle: dict[str, Any]) -> str:
    lines = [
        "# Audio runtime trace",
        "",
        f"- schema: `{bundle['schema']}`",
        f"- observations: {bundle['observationCount']}",
        f"- resolved Event observations: {bundle['resolvedEventObservationCount']}",
        f"- unresolved Event observations: {bundle['unresolvedEventObservationCount']}",
        f"- observations with static trigger-context candidates: {bundle['triggerContexts']['matchedObservationCount']}",
        f"- static join status: `{bundle['joinStatus']}`",
        f"- runtime evidence status: `{bundle['runtimeEvidenceStatus']}`",
        "",
        "## Counts",
        "",
    ]
    for kind, count in bundle["countsByKind"].items():
        lines.append(f"- `{kind}`: {count}")
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "The trace observes managed carrier and AudioAdapter execution. Numeric "
        "Event hashes are joined to exported names/media only as static candidates; "
        "the trace does not prove Wwise acceptance, branch selection, or audibility. "
        "Trigger-context matches are static candidate joins only. Missing or "
        "incompatible static inputs are reported as degraded.",
        "",
    ])
    return "\n".join(lines)


def import_trace(args: argparse.Namespace) -> int:
    events, sources = read_events(args.inputs)
    bundle = build_bundle(
        events,
        sources,
        args.audio_index.resolve(),
        args.trigger_contexts.resolve(),
    )
    output = args.output.resolve()
    markdown_output = core.write_report(
        output,
        bundle,
        markdown(bundle),
        args.markdown_output,
    )
    print(f"wrote JSON: {output}")
    print(f"wrote Markdown: {markdown_output}")
    return 0
