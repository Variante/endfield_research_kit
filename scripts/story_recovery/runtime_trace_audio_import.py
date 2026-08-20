r"""Audio import adapter for :mod:`runtime_trace`.

The importer joins numeric Wwise Event hashes to the current exported audio
index only as a static name/media candidate. It also preserves bounded managed
external-path and native path-string overlaps without upgrading an observed
Adapter request into Wwise acceptance or audible playback.
When native hooks run synchronously inside an attached managed hook, the agent
also carries the managed call stack; those direct path matches are reported as
a stronger bounded relation than a same-session string overlap.
Native hooks also carry an exact same-thread parent capture id for synchronous
native-hook nesting; only resolved parent/child call pairs are summarized.

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
    "audio_native_call",
    "audio_native_result",
    "session_end",
}
DEFAULT_OUTPUT = ROOT / "reports" / "story" / "recovery" / "audio_runtime_trace.json"
DEFAULT_INDEX = ROOT / "export_full" / "structured" / "Audio" / "CN" / "index.json"
DEFAULT_TRIGGER_CONTEXTS = ROOT / "webui" / "data" / "lang" / "CN" / "audio" / "trigger_contexts.json"
MAX_TRIGGER_CONTEXT_SAMPLES = 12
MAX_NATIVE_POINTER_SAMPLES = 64
MAX_AUDIO_PATH_SAMPLES = 64
DECODER_PCM_CALL_RETURN_ADDRESS = "0x1801c4780"
DECODER_RETRY_CALL_RETURN_ADDRESSES = frozenset({"0x1801c49c1", "0x1801c4a43"})
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
        for key in (
            "exportFingerprint", "language", "selectedGameRoot", "expectedModulePath", "attachedModulePath",
            "expectedModuleSha256", "expectedNativeModulePath", "attachedNativeModulePath",
            "expectedNativeModuleSha256",
        ):
            value = optional_text(row, key, source)
            if value is not None:
                event[key] = value
        for key in (
            "expectedModuleSize", "attachedModuleSize",
            "expectedNativeModuleSize", "attachedNativeModuleSize",
        ):
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
        for key in (
            "attachedModulePath", "attachedNativeModulePath",
            "attachedModuleSha256", "attachedNativeModuleSha256",
        ):
            value = optional_text(row, key, source)
            if value is not None:
                event[key] = value
        for key in ("attachedModuleSize", "attachedNativeModuleSize"):
            value = row.get(key)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise fail(source, f"{key} must be a non-negative integer")
                event[key] = value
        for key in (
            "modulePathMatch", "moduleSizeMatch",
            "moduleSha256Match", "nativeModulePathMatch", "nativeModuleSizeMatch",
            "nativeModuleSha256Match",
        ):
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
        for key in (
            "captureId", "parentCaptureId", "nativeParentCaptureId",
            "nativeReturnAddress", "token", "rva",
        ):
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
        if row.get("stackArguments") is not None:
            if not isinstance(row["stackArguments"], dict):
                raise fail(source, "stackArguments must be an object")
            event["stackArguments"] = row["stackArguments"]
        if row.get("decodedArguments") is not None:
            if not isinstance(row["decodedArguments"], dict):
                raise fail(source, "decodedArguments must be an object")
            event["decodedArguments"] = row["decodedArguments"]
        if row.get("decodedArgumentsAfter") is not None:
            if not isinstance(row["decodedArgumentsAfter"], dict):
                raise fail(source, "decodedArgumentsAfter must be an object")
            event["decodedArgumentsAfter"] = row["decodedArgumentsAfter"]
        for key in ("derivedArguments", "derivedArgumentsAfter"):
            if row.get(key) is not None:
                if not isinstance(row[key], dict):
                    raise fail(source, f"{key} must be an object")
                event[key] = row[key]
        if row.get("activeContexts") is not None:
            if not isinstance(row["activeContexts"], list):
                raise fail(source, "activeContexts must be a list")
            event["activeContexts"] = row["activeContexts"]
        if row.get("managedCallStack") is not None:
            if not isinstance(row["managedCallStack"], list):
                raise fail(source, "managedCallStack must be a list")
            event["managedCallStack"] = row["managedCallStack"]
        if row.get("instancePointer") is not None:
            event["instancePointer"] = str(row["instancePointer"])
        if row.get("returnValue") is not None:
            event["returnValue"] = row["returnValue"]
        if row.get("native") is not None:
            if not isinstance(row["native"], bool):
                raise fail(source, "native must be boolean")
            event["native"] = row["native"]
        for key in ("moduleName", "nativeCaptureId"):
            value = optional_text(row, key, source)
            if value is not None:
                event[key] = value
        if row.get("memory") is not None:
            if not isinstance(row["memory"], dict):
                raise fail(source, "memory must be an object")
            event["memory"] = row["memory"]
        if row.get("memoryAfter") is not None:
            if not isinstance(row["memoryAfter"], dict):
                raise fail(source, "memoryAfter must be an object")
            event["memoryAfter"] = row["memoryAfter"]
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


def native_key_values(event: dict[str, Any]) -> set[int]:
    """Extract only explicitly decoded native key fields for bounded joins."""
    values: set[int] = set()
    for container_name in (
        "decodedArguments", "decodedArgumentsAfter", "derivedArguments", "derivedArgumentsAfter",
        "memory", "memoryAfter",
        "nativeCallDecodedArguments", "nativeCallMemory",
    ):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        for field_name in (
            "externalKey", "sourceKey", "descriptorKey",
            "sourceStateKey", "sourceStateKey268",
        ):
            value = numeric_event_id(container.get(field_name))
            if value is not None:
                values.add(value)
    return values


def _native_text_values(event: dict[str, Any], field_name: str) -> set[str]:
    values: set[str] = set()
    for container_name in (
        "decodedArguments", "decodedArgumentsAfter", "derivedArguments", "derivedArgumentsAfter",
        "memory", "memoryAfter",
        "nativeCallDecodedArguments", "nativeCallMemory",
    ):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        value = container.get(field_name)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def _managed_text_values(event: dict[str, Any], field_name: str) -> set[str]:
    """Return string arguments captured at managed request boundaries."""

    values: set[str] = set()
    for container_name in ("arguments", "requestArguments", "stackArguments"):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        value = container.get(field_name)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def _managed_numeric_values(event: dict[str, Any], field_name: str) -> set[int]:
    """Return bounded integer arguments captured at managed request boundaries."""

    values: set[int] = set()
    if field_name == "returnValue":
        value = event.get("returnValue")
        if isinstance(value, bool):
            return values
        if isinstance(value, int):
            values.add(value)
        elif isinstance(value, str):
            text = value.strip()
            try:
                values.add(int(text, 16) if text.lower().startswith("0x") else int(text, 10))
            except ValueError:
                pass
    for container_name in ("arguments", "requestArguments", "stackArguments"):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        value = container.get(field_name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            values.add(value)
            continue
        if isinstance(value, str):
            text = value.strip()
            try:
                if text.lower().startswith("0x"):
                    values.add(int(text, 16))
                elif text.lstrip("-").isdigit():
                    values.add(int(text, 10))
            except ValueError:
                continue
    return values


def _capture_ancestor(
    event: dict[str, Any],
    capture_lookup: dict[tuple[str, str], dict[str, Any]],
    source_kind: str,
) -> dict[str, Any] | None:
    """Find a requested managed ancestor without treating a call stack as playback proof."""

    session_id = event.get("sessionId")
    parent_id = event.get("parentCaptureId")
    if not isinstance(session_id, str):
        return None
    visited: set[str] = set()
    while isinstance(parent_id, str) and parent_id and parent_id not in visited:
        visited.add(parent_id)
        parent = capture_lookup.get((session_id, parent_id))
        if parent is None:
            return None
        if parent.get("sourceKind") == source_kind:
            return parent
        parent_id = parent.get("parentCaptureId")
    return None


def _managed_context_events(
    event: dict[str, Any],
    capture_lookup: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve managed frames carried on a native event.

    The Frida agent records both the carrier-only context stack and the full
    attached managed hook stack on native callbacks.  Treat the capture IDs as
    a bounded synchronous relation; never infer a relation from a matching
    thread alone.
    """

    session_id = event.get("sessionId")
    if not isinstance(session_id, str):
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field_name in ("managedCallStack", "activeContexts"):
        frames = event.get(field_name)
        if not isinstance(frames, list):
            continue
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            capture_id = frame.get("captureId")
            if not isinstance(capture_id, str) or not capture_id or capture_id in seen:
                continue
            seen.add(capture_id)
            managed = capture_lookup.get((session_id, capture_id))
            if managed is not None:
                result.append(managed)
    return result


def summarize_managed_external_path_lifecycle(
    observations: list[dict[str, Any]],
    session_order: list[str],
) -> list[dict[str, Any]]:
    """Summarize managed external paths and their bounded native path overlaps.

    The optional VoicePlayer hook and the Adapter hook are joined only through
    the Frida parent-capture chain or exact same-session path strings. These
    joins do not establish a native handle, selected Wwise branch, or PCM.
    """

    capture_lookup = {
        (event["sessionId"], event["captureId"]): event
        for event in observations
        if event.get("kind") in {"audio_request", "audio_control_request", "audio_carrier_enter"}
        and isinstance(event.get("sessionId"), str)
        and isinstance(event.get("captureId"), str)
    }
    summaries: dict[str, dict[str, Any]] = {}
    for event in observations:
        session_id = event.get("sessionId")
        source_kind = event.get("sourceKind")
        if not isinstance(session_id, str) or not isinstance(source_kind, str):
            continue
        is_managed_request = event.get("kind") == "audio_request"
        is_native_observation = event.get("kind") in {"audio_native_call", "audio_native_result"}
        if not (
            (is_managed_request and source_kind in {
                "voiceExternalSourcePreparation",
                "adapterExternalSourcePostEvent",
            })
            or (is_native_observation and source_kind in {
                "externalDescriptorCopy",
                "wwiseSourceProviderPreparation",
                "wwiseDefaultIoOpenDispatch",
            })
        ):
            continue
        summary = summaries.setdefault(
            session_id,
            {
                "sessionId": session_id,
                "voicePreparationPaths": set(),
                "adapterExternalPaths": set(),
                "voicePreparationReturnValues": set(),
                "voicePreparationHandleIds": set(),
                "voicePreparationCodecs": set(),
                "adapterExternalPostReturnValues": set(),
                "adapterExternalCookieValues": set(),
                "externalDescriptorFiles": set(),
                "sourceProviderPaths": set(),
                "fileOpenPaths": set(),
                "parentCorrelations": [],
                "nativeContextCorrelations": [],
            },
        )
        if is_managed_request:
            paths = _managed_text_values(event, "externalSourceKey")
            if source_kind == "voiceExternalSourcePreparation":
                summary["voicePreparationPaths"].update(paths)
                summary["voicePreparationReturnValues"].update(
                    _managed_numeric_values(event, "returnValue")
                )
                summary["voicePreparationHandleIds"].update(
                    _managed_numeric_values(event, "handleId")
                )
                summary["voicePreparationCodecs"].update(
                    _managed_numeric_values(event, "codec")
                )
            elif source_kind == "adapterExternalSourcePostEvent":
                summary["adapterExternalPaths"].update(paths)
                summary["adapterExternalPostReturnValues"].update(
                    _managed_numeric_values(event, "returnValue")
                )
                summary["adapterExternalCookieValues"].update(
                    _managed_numeric_values(event, "externalCookie")
                )
                voice = _capture_ancestor(event, capture_lookup, "voiceExternalSourcePreparation")
                if voice is not None:
                    voice_paths = sorted(_managed_text_values(voice, "externalSourceKey"))
                    adapter_paths = sorted(paths)
                    voice_path = voice_paths[0] if len(voice_paths) == 1 else None
                    adapter_path = adapter_paths[0] if len(adapter_paths) == 1 else None
                    summary["parentCorrelations"].append({
                        "voicePreparationCaptureId": voice.get("captureId"),
                        "adapterCaptureId": event.get("captureId"),
                        "voiceExternalSourceKey": voice_path,
                        "adapterExternalSourceKey": adapter_path,
                        "exactPathMatch": (
                            voice_path is not None
                            and adapter_path is not None
                            and voice_path == adapter_path
                        ),
                        "pathEvidenceStatus": (
                            "exact_match"
                            if voice_path is not None and adapter_path is not None and voice_path == adapter_path
                            else "different_or_ambiguous"
                        ),
                    })
            continue
        if source_kind == "externalDescriptorCopy":
            summary["externalDescriptorFiles"].update(_native_text_values(event, "externalFile"))
        elif source_kind == "wwiseSourceProviderPreparation":
            summary["sourceProviderPaths"].update(_native_text_values(event, "sourceInfoPath"))
        elif source_kind == "wwiseDefaultIoOpenDispatch":
            summary["fileOpenPaths"].update(_native_text_values(event, "filePath"))
        if is_native_observation and event.get("kind") == "audio_native_call":
            native_path_fields = {
                "externalDescriptorCopy": "externalFile",
                "wwiseSourceProviderPreparation": "sourceInfoPath",
                "wwiseDefaultIoOpenDispatch": "filePath",
            }
            native_field = native_path_fields.get(source_kind)
            native_paths = sorted(_native_text_values(event, native_field)) if native_field else []
            if native_paths:
                for managed in _managed_context_events(event, capture_lookup):
                    managed_source_kind = managed.get("sourceKind")
                    if managed_source_kind not in {
                        "voiceExternalSourcePreparation",
                        "adapterExternalSourcePostEvent",
                    }:
                        continue
                    managed_paths = sorted(_managed_text_values(managed, "externalSourceKey"))
                    if not managed_paths:
                        continue
                    exact = sorted(set(managed_paths) & set(native_paths))
                    summary["nativeContextCorrelations"].append({
                        "nativeCaptureId": event.get("nativeCaptureId"),
                        "nativeSourceKind": source_kind,
                        "managedCaptureId": managed.get("captureId"),
                        "managedSourceKind": managed_source_kind,
                        "managedExternalSourceKeys": managed_paths,
                        "nativePaths": native_paths,
                        "exactPathMatches": exact,
                        "pathEvidenceStatus": "exact_match" if exact else "different",
                    })

    result: list[dict[str, Any]] = []
    for session_id in session_order:
        summary = summaries.get(session_id)
        if summary is None:
            continue
        row: dict[str, Any] = {"sessionId": session_id}
        path_fields = (
            "voicePreparationPaths",
            "adapterExternalPaths",
            "externalDescriptorFiles",
            "sourceProviderPaths",
            "fileOpenPaths",
        )
        for field_name in path_fields:
            values = sorted(summary[field_name])
            row[field_name] = values[:MAX_AUDIO_PATH_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_AUDIO_PATH_SAMPLES
        for field_name in (
            "voicePreparationReturnValues", "voicePreparationHandleIds",
            "voicePreparationCodecs",
            "adapterExternalPostReturnValues", "adapterExternalCookieValues",
        ):
            row[field_name] = sorted(summary[field_name])[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(summary[field_name]) > MAX_NATIVE_POINTER_SAMPLES
        row["sharedVoiceAdapterPaths"] = sorted(
            summary["voicePreparationPaths"] & summary["adapterExternalPaths"]
        )[:MAX_AUDIO_PATH_SAMPLES]
        row["sharedVoiceDescriptorPaths"] = sorted(
            summary["voicePreparationPaths"] & summary["externalDescriptorFiles"]
        )[:MAX_AUDIO_PATH_SAMPLES]
        row["sharedVoiceProviderPaths"] = sorted(
            summary["voicePreparationPaths"] & summary["sourceProviderPaths"]
        )[:MAX_AUDIO_PATH_SAMPLES]
        row["sharedVoiceOpenPaths"] = sorted(
            summary["voicePreparationPaths"] & summary["fileOpenPaths"]
        )[:MAX_AUDIO_PATH_SAMPLES]
        row["sharedAdapterDescriptorPaths"] = sorted(
            summary["adapterExternalPaths"] & summary["externalDescriptorFiles"]
        )[:MAX_AUDIO_PATH_SAMPLES]
        row["sharedAdapterOpenPaths"] = sorted(
            summary["adapterExternalPaths"] & summary["fileOpenPaths"]
        )[:MAX_AUDIO_PATH_SAMPLES]
        correlations = summary["parentCorrelations"]
        row["managedParentCorrelationCount"] = len(correlations)
        row["managedParentPathMatchCount"] = sum(
            item.get("exactPathMatch") is True for item in correlations
        )
        row["managedParentCorrelations"] = correlations[:MAX_AUDIO_PATH_SAMPLES]
        row["managedParentCorrelationsTruncated"] = len(correlations) > MAX_AUDIO_PATH_SAMPLES
        native_correlations = summary["nativeContextCorrelations"]
        row["managedNativeContextCorrelationCount"] = len(native_correlations)
        row["managedNativeContextPathMatchCount"] = sum(
            bool(item.get("exactPathMatches")) for item in native_correlations
        )
        row["managedNativeContextCorrelations"] = native_correlations[:MAX_AUDIO_PATH_SAMPLES]
        row["managedNativeContextCorrelationsTruncated"] = len(native_correlations) > MAX_AUDIO_PATH_SAMPLES
        row["evidenceBoundary"] = (
            "Managed path rows are exact string observations from the optional VoicePlayer and "
            "Adapter hooks. Parent-capture matches show a bounded managed call-stack relation; "
            "native events carrying the same managed stack provide a stronger synchronous "
            "managed-to-native boundary, but still do not prove one sourceInfo instance, file "
            "handle, codec stream, selected branch, or audible PCM. Same-session path overlaps "
            "remain weaker than that direct stack relation. Voice preparation return values are "
            "reported separately from Adapter external-post return values: the latter is the "
            "managed internal-playing-id result, not the native registration serial. The captured "
            "externalCookie is also kept separate from both values."
        )
        result.append(row)
    return result


def _native_nonzero_pointer_values(event: dict[str, Any], field_name: str) -> set[str]:
    """Return pointer observations while excluding null sentinels from joins."""

    values: set[str] = set()
    for value in _native_text_values(event, field_name):
        try:
            if int(value, 0) == 0:
                continue
        except ValueError:
            continue
        values.add(value)
    return values


def _native_after_nonzero_pointer_values(event: dict[str, Any], field_name: str) -> set[str]:
    """Return post-call pointer observations without mixing pre-call state."""

    container = event.get("memoryAfter")
    if not isinstance(container, dict):
        return set()
    value = container.get(field_name)
    if not isinstance(value, str) or not value:
        return set()
    try:
        if int(value, 0) == 0:
            return set()
    except ValueError:
        return set()
    return {value}


def _pointer_text(value: Any) -> str | None:
    """Normalize a captured pointer-like value for bounded identity joins."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = hex(value)
    elif isinstance(value, str) and value.strip():
        text = value.strip()
    else:
        return None
    try:
        if int(text, 0) == 0:
            return None
    except ValueError:
        return None
    return text


def _native_pointer_values(event: dict[str, Any], *field_names: str) -> set[str]:
    """Read bounded pointer fields from decoded native arguments/results."""

    values: set[str] = set()
    for container_name in (
        "arguments", "decodedArguments", "decodedArgumentsAfter", "derivedArguments",
        "derivedArgumentsAfter", "nativeCallDecodedArguments", "nativeCallMemory",
    ):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        for field_name in field_names:
            pointer = _pointer_text(container.get(field_name))
            if pointer is not None:
                values.add(pointer)
    return values


def _native_return_pointer(event: dict[str, Any]) -> set[str]:
    pointer = _pointer_text(event.get("returnValue"))
    return {pointer} if pointer is not None else set()


def _native_numeric_values(event: dict[str, Any], field_name: str) -> set[int]:
    values: set[int] = set()
    if field_name == "returnValue":
        value = event.get("returnValue")
        if isinstance(value, int) and not isinstance(value, bool):
            values.add(value)
        elif isinstance(value, str):
            try:
                values.add(int(value, 0))
            except ValueError:
                pass
    for container_name in (
        "decodedArguments", "decodedArgumentsAfter", "derivedArguments", "derivedArgumentsAfter",
        "memory", "memoryAfter",
        "nativeCallDecodedArguments", "nativeCallMemory",
    ):
        container = event.get(container_name)
        if not isinstance(container, dict):
            continue
        value = container.get(field_name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            values.add(value)
        elif isinstance(value, str):
            try:
                values.add(int(value, 0))
            except ValueError:
                continue
    return values


def _native_nonzero_numeric_values(event: dict[str, Any], field_name: str) -> set[int]:
    """Return numeric handles while dropping null/invalid-handle sentinels."""

    return {
        value for value in _native_numeric_values(event, field_name)
        if value not in {0, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}
    }


def summarize_native_key_lifecycle(
    observations: list[dict[str, Any]],
    session_order: list[str],
) -> list[dict[str, Any]]:
    """Summarize runtime key transport without inventing a file/PCM join.

    The source-manager join and decoder registry are deliberately reported as
    separate boundaries. A shared integer is useful evidence, but the trace
    still needs pointer/handle and read/codec correlation before it can claim
    that one external path produced one decoded stream.
    """
    field_sets = (
        ("externalSourceRegistration", "sourceKey", "registrationKeys"),
        ("externalSourceLookup", "externalKey", "externalLookupKeys"),
        ("externalSourceLookup", "descriptorKey", "externalDescriptorKeys"),
        ("externalSourceSiblingLookup", "sourceKey", "externalSiblingLookupKeys"),
        ("externalSourceManagerJoin", "sourceKey", "managerJoinRequestedKeys"),
        ("externalSourceManagerJoin", "sourceStateKey", "managerJoinStateKeys"),
        ("externalSourceManagerJoin", "sourceStateKey268", "managerJoinStateKeys268"),
        ("sourceKeyDecoderRegistry", "sourceKey", "decoderRegistryKeys"),
        ("wwiseSourceMediaLookup", "sourceKey", "sourceMediaLookupKeys"),
        ("sourceInfoSelectionConsumer", "sourceInfoKey", "sourceInfoSelectionKeys"),
        ("sourceInfoSelector", "sourceInfoKey", "sourceInfoSelectorKeys"),
        ("wwiseSourceProviderPreparation", "sourceInfoKey", "sourceInfoProviderKeys"),
        ("sourceStateInitializer", "sourceStateKey268", "sourceStateInitializerKeys"),
        ("sourceStateInitializer", "sourceConfigKey34", "sourceStateInitializerConfigKeys"),
        ("sourceStateInitializer", "sourceInfoKey", "sourceStateInitializerInfoKeys"),
    )
    summaries: dict[str, dict[str, Any]] = {}
    for event in observations:
        if event.get("kind") not in {"audio_native_call", "audio_native_result"}:
            continue
        session_id = event.get("sessionId")
        source_kind = event.get("sourceKind")
        if not isinstance(session_id, str) or not isinstance(source_kind, str):
            continue
        fields = [item for item in field_sets if item[0] == source_kind]
        if not fields and source_kind not in {
            "wwiseSourceProviderPreparation", "externalDescriptorCopy",
            "wwiseDefaultIoOpenDispatch", "wwiseDeviceQueueDispatch",
            "wwiseDefaultIoProviderBatchDispatch", "wwiseAsyncBatchRead",
            "wwiseAsyncBatchReadAlternate", "externalSourceStateCallback",
            "sourceInfoSelectionConsumer", "sourceInfoSelector",
            "wwiseCodecDecoderDecode",
        }:
            continue
        summary = summaries.setdefault(
            session_id,
            {
                "sessionId": session_id,
                "registrationKeys": set(),
                "registrationStatuses": set(),
                "managerEntryPointers": set(),
                "registrationManagerEntryPointers": set(),
                "managerJoinEntryPointers": set(),
                "externalLookupEntryPointers": set(),
                "managerEntryDescriptorInfoPointers": set(),
                "descriptorAllocationBases": set(),
                "externalLookupKeys": set(),
                "externalDescriptorKeys": set(),
                "externalSiblingLookupKeys": set(),
                "managerJoinRequestedKeys": set(),
                "managerJoinStateKeys": set(),
                "managerJoinStateKeys268": set(),
                "decoderRegistryKeys": set(),
                "sourceMediaLookupKeys": set(),
                "sourceInfoSelectionKeys": set(),
                "sourceInfoSelectorKeys": set(),
                "sourceInfoSelectedEntryKeys": set(),
                "sourceInfoSelectedDescriptorPointers": set(),
                "sourceInfoSelectedDescriptorAux": set(),
                "sourceInfoProviderKeys": set(),
                "sourceStateInitializerKeys": set(),
                "sourceStateInitializerConfigKeys": set(),
                "sourceStateInitializerInfoKeys": set(),
                "decoderPointers": set(),
                "sourceProviderPointers": set(),
                "sourceProviderOwnerPointers": set(),
                "sourceInfoPointers": set(),
                "sourceObjectSelectedDescriptorPointers": set(),
                "sourceOwnerSelectedDescriptorPointers": set(),
                "sourceStateInitializerPointers": set(),
                "sourceStateInitializerSourceInfoPointers": set(),
                "sourceStateInitializerConfigPointers": set(),
                "sourceStateInitializerReturnAddresses": set(),
                "ioProviderPointers": set(),
                "asyncDescriptorProviderPointers": set(),
                "sourceStateCallbackKeys": set(),
                "sourceStateCallbackContexts": set(),
                "sourceProviderPaths": set(),
                "externalDescriptorFiles": set(),
                "externalDescriptorAllocationBases": set(),
                "fileOpenPaths": set(),
                "fileOpenProviderContexts": set(),
                "fileOpenHandles": set(),
                "asyncDescriptorProviderHandles": set(),
                "decoderDecodePointers": set(),
                "decoderDecodeOwnerPointers": set(),
                "decoderDecodeOwnerKeys": set(),
                "decoderDecodeProviderPointers": set(),
                "decoderDecodeFloatBuffers": set(),
                "decoderDecodeFrameCounts": set(),
                "decoderReturnAddresses": set(),
                "decoderPcmCallCaptureIds": set(),
                "decoderRetryCallCaptureIds": set(),
            },
        )
        for _boundary, field_name, output_name in fields:
            summary[output_name].update(_native_numeric_values(event, field_name))
        entry_pointers = _native_text_values(event, "managerEntryPointer")
        summary["managerEntryPointers"].update(entry_pointers)
        summary["managerEntryDescriptorInfoPointers"].update(
            _native_nonzero_pointer_values(event, "managerEntryDescriptorInfo")
        )
        if source_kind == "externalSourceRegistration":
            summary["registrationStatuses"].update(
                _native_numeric_values(event, "returnValue")
            )
            summary["registrationManagerEntryPointers"].update(entry_pointers)
        elif source_kind == "externalSourceManagerJoin":
            summary["managerJoinEntryPointers"].update(entry_pointers)
        elif source_kind in {"externalSourceLookup", "externalSourceSiblingLookup"}:
            summary["externalLookupEntryPointers"].update(entry_pointers)
        if source_kind == "sourceKeyDecoderRegistry":
            summary["decoderPointers"].update(_native_text_values(event, "decoder"))
        elif source_kind == "externalSourceStateCallback":
            summary["sourceStateCallbackKeys"].update(
                _native_numeric_values(event, "sourceKeyFromContext")
            )
            summary["sourceStateCallbackContexts"].update(
                _native_nonzero_pointer_values(event, "sourceContext")
            )
        elif source_kind == "wwiseSourceProviderPreparation":
            summary["sourceProviderPointers"].update(
                _native_after_nonzero_pointer_values(event, "decoderProvider")
            )
            summary["sourceProviderOwnerPointers"].update(
                _native_nonzero_pointer_values(event, "sourceOwner")
            )
            summary["sourceInfoPointers"].update(
                _native_nonzero_pointer_values(event, "sourceInfoPointer")
            )
            summary["sourceOwnerSelectedDescriptorPointers"].update(
                _native_nonzero_pointer_values(event, "sourceOwnerSelectedDescriptor")
            )
            summary["sourceProviderPaths"].update(_native_text_values(event, "sourceInfoPath"))
        elif source_kind == "sourceInfoSelector":
            summary["sourceInfoSelectedEntryKeys"].update(
                _native_numeric_values(event, "selectedEntryKey")
            )
            summary["sourceInfoSelectedDescriptorPointers"].update(
                _native_nonzero_pointer_values(event, "selectedDescriptor")
            )
            summary["sourceInfoSelectedDescriptorAux"].update(
                _native_numeric_values(event, "selectedDescriptorAux")
            )
        elif source_kind == "sourceInfoSelectionConsumer":
            summary["sourceObjectSelectedDescriptorPointers"].update(
                _native_nonzero_pointer_values(event, "sourceObjectSelectedDescriptor")
            )
        elif source_kind == "sourceStateInitializer":
            return_address = _pointer_text(event.get("nativeReturnAddress"))
            if return_address is not None:
                summary["sourceStateInitializerReturnAddresses"].add(return_address)
            summary["sourceStateInitializerPointers"].update(
                _native_pointer_values(event, "sourceState")
            )
            summary["sourceStateInitializerSourceInfoPointers"].update(
                _native_nonzero_pointer_values(event, "sourceStateSourceInfo")
            )
            summary["sourceStateInitializerConfigPointers"].update(
                _native_pointer_values(event, "sourceConfig")
            )
        elif source_kind in {
            "wwiseDeviceQueueDispatch", "wwiseDefaultIoProviderBatchDispatch",
        }:
            for field_name in ("provider0", "provider1"):
                summary["ioProviderPointers"].update(
                    _native_nonzero_pointer_values(event, field_name)
                )
        elif source_kind in {"wwiseAsyncBatchRead", "wwiseAsyncBatchReadAlternate"}:
            summary["asyncDescriptorProviderPointers"].update(
                _native_nonzero_pointer_values(event, "descriptorProviderObject")
            )
            summary["asyncDescriptorProviderHandles"].update(
                _native_nonzero_numeric_values(event, "descriptorProviderHandle")
            )
        elif source_kind == "externalSourceRegistration":
            summary["descriptorAllocationBases"].update(
                _native_nonzero_pointer_values(event, "descriptorAllocationBase")
            )
        elif source_kind == "externalDescriptorCopy":
            summary["externalDescriptorFiles"].update(_native_text_values(event, "externalFile"))
            summary["externalDescriptorAllocationBases"].update(
                _native_nonzero_pointer_values(event, "copiedAllocationBase")
            )
        elif source_kind == "wwiseDefaultIoOpenDispatch":
            summary["fileOpenPaths"].update(_native_text_values(event, "filePath"))
            summary["fileOpenProviderContexts"].update(
                _native_nonzero_pointer_values(event, "openProviderContext")
            )
            summary["fileOpenHandles"].update(
                _native_nonzero_numeric_values(event, "openHandle")
            )
        elif source_kind == "wwiseCodecDecoderDecode":
            return_address = _pointer_text(event.get("nativeReturnAddress"))
            if return_address is not None:
                summary["decoderReturnAddresses"].add(return_address)
                capture_id = event.get("nativeCaptureId")
                if isinstance(capture_id, str) and capture_id:
                    if return_address == DECODER_PCM_CALL_RETURN_ADDRESS:
                        summary["decoderPcmCallCaptureIds"].add(capture_id)
                    elif return_address in DECODER_RETRY_CALL_RETURN_ADDRESSES:
                        summary["decoderRetryCallCaptureIds"].add(capture_id)
            summary["decoderDecodePointers"].update(_native_nonzero_pointer_values(event, "decoder"))
            summary["decoderDecodeOwnerPointers"].update(
                _native_nonzero_pointer_values(event, "decoderOwner")
            )
            summary["decoderDecodeOwnerKeys"].update(
                _native_numeric_values(event, "decoderOwnerKey")
            )
            summary["decoderDecodeProviderPointers"].update(
                _native_nonzero_pointer_values(event, "decoderProviderInterface")
            )
            summary["decoderDecodeFloatBuffers"].update(
                _native_nonzero_pointer_values(event, "decodedFloatBuffer")
            )
            summary["decoderDecodeFrameCounts"].update(
                _native_numeric_values(event, "decodedFrameCount")
            )

    result: list[dict[str, Any]] = []
    for session_id in session_order:
        summary = summaries.get(session_id)
        if summary is None:
            continue
        row = {"sessionId": session_id}
        for field_name in (
            "registrationKeys", "descriptorAllocationBases", "externalLookupKeys", "externalDescriptorKeys",
            "externalSiblingLookupKeys",
            "registrationStatuses",
            "managerJoinRequestedKeys", "managerJoinStateKeys",
            "managerJoinStateKeys268", "decoderRegistryKeys", "sourceMediaLookupKeys",
            "sourceStateCallbackKeys", "sourceInfoSelectionKeys", "sourceInfoSelectorKeys",
            "sourceInfoSelectedEntryKeys", "sourceInfoSelectedDescriptorAux",
            "sourceInfoProviderKeys", "sourceStateInitializerKeys",
            "sourceStateInitializerConfigKeys", "sourceStateInitializerInfoKeys",
        ):
            row[field_name] = sorted(summary[field_name])
        row["sourceStateInitializerReturnAddresses"] = sorted(
            summary["sourceStateInitializerReturnAddresses"]
        )[:MAX_NATIVE_POINTER_SAMPLES]
        row["sourceStateInitializerReturnAddressesTruncated"] = (
            len(summary["sourceStateInitializerReturnAddresses"]) > MAX_NATIVE_POINTER_SAMPLES
        )
        for field_name in (
            "managerEntryPointers", "registrationManagerEntryPointers",
            "managerJoinEntryPointers", "externalLookupEntryPointers",
        ):
            values = sorted(summary[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        row["sharedRegistrationJoinEntryPointers"] = sorted(
            summary["registrationManagerEntryPointers"] & summary["managerJoinEntryPointers"]
        )
        row["sharedRegistrationLookupEntryPointers"] = sorted(
            summary["registrationManagerEntryPointers"] & summary["externalLookupEntryPointers"]
        )
        descriptor_info_pointers = sorted(summary["managerEntryDescriptorInfoPointers"])
        row["managerEntryDescriptorInfoPointers"] = descriptor_info_pointers[:MAX_NATIVE_POINTER_SAMPLES]
        row["managerEntryDescriptorInfoPointersTruncated"] = (
            len(descriptor_info_pointers) > MAX_NATIVE_POINTER_SAMPLES
        )
        for field_name in (
            "decoderPointers", "sourceProviderPaths", "externalDescriptorFiles",
            "externalDescriptorAllocationBases",
            "fileOpenPaths",
        ):
            values = sorted(summary[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        for field_name in (
            "sourceProviderPointers", "ioProviderPointers",
            "asyncDescriptorProviderPointers",
            "sourceStateCallbackContexts", "fileOpenProviderContexts",
            "decoderDecodePointers", "decoderDecodeProviderPointers",
            "decoderDecodeFloatBuffers", "sourceProviderOwnerPointers",
            "sourceInfoPointers", "decoderDecodeOwnerPointers",
            "sourceInfoSelectedDescriptorPointers", "sourceObjectSelectedDescriptorPointers",
            "sourceOwnerSelectedDescriptorPointers",
            "sourceStateInitializerPointers", "sourceStateInitializerSourceInfoPointers",
            "sourceStateInitializerConfigPointers",
        ):
            values = sorted(summary[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        for field_name in ("fileOpenHandles", "asyncDescriptorProviderHandles"):
            row[field_name] = sorted(summary[field_name])[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(summary[field_name]) > MAX_NATIVE_POINTER_SAMPLES
        row["decoderDecodeOwnerKeys"] = sorted(summary["decoderDecodeOwnerKeys"])
        row["decoderDecodeFrameCounts"] = sorted(summary["decoderDecodeFrameCounts"])
        row["decoderReturnAddresses"] = sorted(summary["decoderReturnAddresses"])
        row["pcmConversionCallerReturnAddresses"] = sorted(
            address for address in summary["decoderReturnAddresses"]
            if address == DECODER_PCM_CALL_RETURN_ADDRESS
        )
        row["pcmConversionDecoderCaptureCount"] = len(summary["decoderPcmCallCaptureIds"])
        row["decoderRetryCaptureCount"] = len(summary["decoderRetryCallCaptureIds"])
        row["sameJoinArgumentAndStateKeys"] = sorted(
            summary["managerJoinRequestedKeys"] & summary["managerJoinStateKeys"]
        )
        row["sameJoinArgumentAndStateKeys268"] = sorted(
            summary["managerJoinRequestedKeys"] & summary["managerJoinStateKeys268"]
        )
        # These intersections are the shortest runtime test for the current
        # static gap: the manager constructor stores a generated registration
        # serial at +0x4c, while source setup supplies a separately sourced
        # numeric key.  Keep each downstream boundary separate so an observed
        # equality cannot be mistaken for a path/open/PCM join.
        row["registrationManagerJoinRequestedKeys"] = sorted(
            summary["registrationKeys"] & summary["managerJoinRequestedKeys"]
        )
        row["registrationManagerJoinStateKeys"] = sorted(
            summary["registrationKeys"] & summary["managerJoinStateKeys"]
        )
        row["registrationManagerJoinStateKeys268"] = sorted(
            summary["registrationKeys"] & summary["managerJoinStateKeys268"]
        )
        row["registrationExternalLookupKeys"] = sorted(
            summary["registrationKeys"] & summary["externalLookupKeys"]
        )
        row["registrationSourceMediaLookupKeys"] = sorted(
            summary["registrationKeys"] & summary["sourceMediaLookupKeys"]
        )
        row["sharedManagerJoinDecoderKeys"] = sorted(
            summary["managerJoinRequestedKeys"] & summary["decoderRegistryKeys"]
        )
        row["sharedStateMediaLookupKeys"] = sorted(
            summary["managerJoinStateKeys268"] & summary["sourceMediaLookupKeys"]
        )
        row["sharedExternalLookupManagerKeys"] = sorted(
            summary["externalLookupKeys"] & summary["managerJoinRequestedKeys"]
        )
        row["sharedSourceStateSiblingKeys"] = sorted(
            summary["sourceStateCallbackKeys"] & summary["externalSiblingLookupKeys"]
        )
        row["sharedSourceStateManagerJoinKeys"] = sorted(
            summary["sourceStateCallbackKeys"] & summary["managerJoinRequestedKeys"]
        )
        row["sharedSourceStateSourceInfoKeys"] = sorted(
            summary["sourceStateCallbackKeys"]
            & (summary["sourceInfoSelectionKeys"] | summary["sourceInfoSelectorKeys"])
        )
        row["registrationSourceInfoKeys"] = sorted(
            summary["registrationKeys"]
            & (summary["sourceInfoSelectionKeys"] | summary["sourceInfoSelectorKeys"])
        )
        row["sourceInfoSelectionMediaKeys"] = sorted(
            (summary["sourceInfoSelectionKeys"] | summary["sourceInfoSelectorKeys"])
            & summary["sourceMediaLookupKeys"]
        )
        row["sharedSourceInfoSelectorEntryKeys"] = sorted(
            summary["sourceInfoSelectorKeys"] & summary["sourceInfoSelectedEntryKeys"]
        )
        row["sharedSourceInfoSelectorObjectDescriptorPointers"] = sorted(
            summary["sourceInfoSelectedDescriptorPointers"]
            & summary["sourceObjectSelectedDescriptorPointers"]
        )
        row["sharedSourceInfoSelectorProviderDescriptorPointers"] = sorted(
            summary["sourceInfoSelectedDescriptorPointers"]
            & summary["sourceOwnerSelectedDescriptorPointers"]
        )
        row["sharedSourceObjectProviderDescriptorPointers"] = sorted(
            summary["sourceObjectSelectedDescriptorPointers"]
            & summary["sourceOwnerSelectedDescriptorPointers"]
        )
        row["sharedSourceStateInitializerProviderOwnerPointers"] = sorted(
            summary["sourceStateInitializerPointers"]
            & summary["sourceProviderOwnerPointers"]
        )
        row["sharedSourceStateInitializerDecoderOwnerPointers"] = sorted(
            summary["sourceStateInitializerPointers"]
            & summary["decoderDecodeOwnerPointers"]
        )
        row["sharedSourceStateInitializerInfoPointers"] = sorted(
            summary["sourceStateInitializerSourceInfoPointers"]
            & summary["sourceInfoPointers"]
        )
        row["sharedSourceStateInitializerJoinKeys"] = sorted(
            summary["sourceStateInitializerKeys"]
            & summary["managerJoinStateKeys268"]
        )
        row["sharedSourceStateInitializerDecoderKeys"] = sorted(
            summary["sourceStateInitializerKeys"]
            & summary["decoderDecodeOwnerKeys"]
        )
        row["sharedSourceInfoProviderKeys"] = sorted(
            summary["sourceInfoProviderKeys"]
            & (summary["sourceInfoSelectionKeys"] | summary["sourceInfoSelectorKeys"])
        )
        row["sharedSourceStateProviderKeys"] = sorted(
            summary["sourceStateCallbackKeys"] & summary["sourceInfoProviderKeys"]
        )
        row["sharedDescriptorAllocationBases"] = sorted(
            summary["descriptorAllocationBases"]
            & summary["externalDescriptorAllocationBases"]
        )
        row["sharedManagerDescriptorAllocationBases"] = sorted(
            summary["managerEntryDescriptorInfoPointers"]
            & summary["externalDescriptorAllocationBases"]
        )
        row["sharedProviderOpenPaths"] = sorted(
            summary["sourceProviderPaths"] & summary["fileOpenPaths"]
        )
        row["sharedDescriptorOpenPaths"] = sorted(
            summary["externalDescriptorFiles"] & summary["fileOpenPaths"]
        )
        row["sharedSourceProviderIoPointers"] = sorted(
            summary["sourceProviderPointers"] & summary["ioProviderPointers"]
        )
        row["sharedSourceProviderAsyncPointers"] = sorted(
            summary["sourceProviderPointers"] & summary["asyncDescriptorProviderPointers"]
        )
        row["sharedOpenAsyncHandles"] = sorted(
            summary["fileOpenHandles"] & summary["asyncDescriptorProviderHandles"]
        )
        row["sharedDecoderRegistryDecodePointers"] = sorted(
            summary["decoderPointers"] & summary["decoderDecodePointers"]
        )
        row["sharedSourceProviderDecoderPointers"] = sorted(
            summary["sourceProviderPointers"] & summary["decoderDecodeProviderPointers"]
        )
        row["sharedSourceProviderOwnerDecoderPointers"] = sorted(
            summary["sourceProviderOwnerPointers"]
            & summary["decoderDecodeOwnerPointers"]
        )
        row["sharedDecoderRegistryDecodeKeys"] = sorted(
            summary["decoderRegistryKeys"] & summary["decoderDecodeOwnerKeys"]
        )
        row["sharedManagerJoinDecoderDecodeKeys"] = sorted(
            summary["managerJoinRequestedKeys"] & summary["decoderDecodeOwnerKeys"]
        )
        row["sharedSourceInfoDecoderDecodeKeys"] = sorted(
            (summary["sourceInfoSelectionKeys"] | summary["sourceInfoSelectorKeys"])
            & summary["decoderDecodeOwnerKeys"]
        )
        row["evidenceBoundary"] = (
            "Same-session numeric key intersections are bounded runtime evidence "
            "across the named native boundaries. They do not prove one manager "
            "entry, file handle, read request, codec stream, or audible PCM. "
            "The registration-to-join fields explicitly test whether the "
            "generated manager serial equals a later requested/state key; an "
            "intersection is still same-session unless a capture's pointer or "
            "managed call-chain evidence narrows it to one request. The manager "
            "entry pointer intersections are a stronger same-entry observation "
            "because the agent resolves the exact hash-table node by its serial, "
            "and a manager +0x38 pointer intersection additionally checks the "
            "descriptor copier allocation; they still do not prove a file "
            "handle, read request, codec "
            "stream, or audible PCM. "
            "A shared copied-descriptor allocation pointer links the descriptor "
            "copier output to the manager-constructor input, but does not by "
            "itself join sourceInfo/path selection or decoded PCM; descriptor "
            "paths and file-open paths remain separately observed. Provider "
            "pointer intersections are a bounded same-object check from the "
            "decoder +0x58 output into device/async-read descriptors; they do "
            "not establish key, path, handle, codec, or PCM identity. The "
            "openHandle/descriptorProviderHandle intersection is an exact "
            "same-native-handle check across the default open and async-read "
            "boundaries; it still does not establish key, path ownership, "
            "decoder, PCM, or audibility. The decoder-decode hook is an exact "
            "invocation of the selected generic decoder: its decoder pointer, "
            "owner +0x268 key, provider interface +0x58, float-output slot, "
            "and produced frame-count slot are sampled before/after the call. "
            "Intersections with the key registry, source-state keys, and source "
            "provider pointer prove bounded runtime continuity into a decoder "
            "call. The decoder return address identifies the primary callsite "
            "whose static body performs float-to-PCM16 writes, distinct from "
            "the refill retry callsites; this still is not proof of an audible "
            "output. The sourceOwner/decoderOwner intersection is a bounded "
            "same-native-owner check across provider preparation and decode; it "
            "does not by itself prove the sourceInfo path was selected for the "
            "external key. The source-state initializer additionally records "
            "the source-state object, sourceInfo pointer, config +0x34 key, and "
            "post-write +0x268 key; intersections with provider/decoder owners, "
            "sourceInfo pointers, manager-join keys, or decoder-owner keys are "
            "bounded initialization continuity, not a file, handle, or PCM join. "
            "source-state callback key is reported separately from the manager "
            "serial and only an exact same-session intersection with sibling "
            "lookup/join keys is exposed; sourceInfo selector/provider key "
            "intersections are likewise bounded identity evidence and still do "
            "not prove path, handle, decoder, or PCM."
        )
        result.append(row)
    return result


def summarize_callback_lifecycle(
    observations: list[dict[str, Any]],
    session_order: list[str],
) -> list[dict[str, Any]]:
    """Join the native resolver context pointer to the managed callback cookie.

    The external-source callback cookie is the temporary managed mapping
    object, not the Wwise ``iExternalSrcCookie`` value.  A same-session pointer
    intersection across the resolver bridge and managed callback is useful
    callback-transport evidence, but it does not select a file or decoder.
    """

    capture_lookup = {
        (event["sessionId"], event["captureId"]): event
        for event in observations
        if event.get("kind") in {
            "audio_request",
            "audio_control_request",
            "audio_carrier_enter",
        }
        and isinstance(event.get("sessionId"), str)
        and isinstance(event.get("captureId"), str)
    }
    summaries: dict[str, dict[str, Any]] = {}
    native_fields = {
        "externalSourceRegistration": "callbackCookie",
        "externalSourceLookup": "descriptor0",
        "externalSourceResolverCallback": "descriptor0",
        "externalSourceCallbackBridge": "descriptor0",
        "externalSourceCallbackQueueAppend": "record0",
    }
    for event in observations:
        session_id = event.get("sessionId")
        source_kind = event.get("sourceKind")
        if not isinstance(session_id, str) or not isinstance(source_kind, str):
            continue
        summary = summaries.setdefault(
            session_id,
            {
                "managedCallbackCookies": set(),
                "nativeRegistrationContexts": set(),
                "nativeResolverContexts": set(),
                "nativeQueueContexts": set(),
                "nativeQueueRecordPointers": set(),
                "nativeQueueDetachHeadPointers": set(),
                "nativeQueueGetterRecordPointers": set(),
                "nativeQueueGetterRecords": defaultdict(
                    lambda: {"cookies": set(), "types": set(), "payloads": set()}
                ),
                "managedWwisePumpCaptures": set(),
                "managedWwiseDispatchCaptures": set(),
                "managedWwiseDispatchTypes": set(),
                "managedExternalCallbackCaptures": set(),
                "managedExternalCallbackTypes": set(),
                "managedExternalCallbackChains": [],
            },
        )
        if event.get("kind") == "audio_request" and source_kind == "wwiseCallbackPump":
            capture_id = event.get("captureId")
            if isinstance(capture_id, str) and capture_id:
                summary["managedWwisePumpCaptures"].add(capture_id)
            continue
        if event.get("kind") == "audio_request" and source_kind == "wwiseCallbackDispatch":
            capture_id = event.get("captureId")
            if isinstance(capture_id, str) and capture_id:
                summary["managedWwiseDispatchCaptures"].add(capture_id)
            summary["managedWwiseDispatchTypes"].update(
                _managed_numeric_values(event, "callbackType")
            )
            continue
        if event.get("kind") == "audio_request" and source_kind == "adapterExternalSourceCallback":
            summary["managedCallbackCookies"].update(
                _managed_text_values(event, "callbackCookie")
            )
            capture_id = event.get("captureId")
            if isinstance(capture_id, str) and capture_id:
                summary["managedExternalCallbackCaptures"].add(capture_id)
            summary["managedExternalCallbackTypes"].update(
                _managed_numeric_values(event, "callbackType")
            )
            dispatch = _capture_ancestor(
                event, capture_lookup, "wwiseCallbackDispatch"
            )
            pump = _capture_ancestor(event, capture_lookup, "wwiseCallbackPump")
            if dispatch is not None:
                dispatch_capture_id = dispatch.get("captureId")
                pump_ancestor = _capture_ancestor(
                    dispatch, capture_lookup, "wwiseCallbackPump"
                )
                summary["managedExternalCallbackChains"].append({
                    "externalCallbackCaptureId": capture_id,
                    "dispatchCaptureId": dispatch_capture_id,
                    "pumpCaptureId": (
                        pump_ancestor.get("captureId")
                        if pump_ancestor is not None
                        else (pump.get("captureId") if pump is not None else None)
                    ),
                    "callbackTypes": sorted(
                        _managed_numeric_values(event, "callbackType")
                    ),
                })
            continue
        if source_kind == "externalSourceCallbackQueueAppend":
            if event.get("kind") == "audio_native_call":
                summary["nativeQueueRecordPointers"].update(
                    _native_pointer_values(event, "arg0", "record")
                )
            # Keep the existing cookie/context join below as a separate field.
        elif source_kind == "externalSourceCallbackQueueDetach":
            if event.get("kind") == "audio_native_result":
                summary["nativeQueueDetachHeadPointers"].update(
                    _native_return_pointer(event)
                )
            continue
        elif source_kind in {
            "externalSourceCallbackRecordCookieGetter",
            "externalSourceCallbackRecordTypeGetter",
            "externalSourceCallbackRecordPayloadGetter",
        }:
            if event.get("kind") == "audio_native_result":
                records = _native_pointer_values(event, "arg0", "record")
                summary["nativeQueueGetterRecordPointers"].update(records)
                for record in records:
                    getter = summary["nativeQueueGetterRecords"][record]
                    if source_kind == "externalSourceCallbackRecordCookieGetter":
                        getter["cookies"].update(_native_return_pointer(event))
                    elif source_kind == "externalSourceCallbackRecordPayloadGetter":
                        getter["payloads"].update(_native_return_pointer(event))
                    else:
                        value = event.get("returnValue")
                        if isinstance(value, bool):
                            continue
                        if isinstance(value, int):
                            getter["types"].add(value)
                        elif isinstance(value, str):
                            try:
                                getter["types"].add(int(value, 0))
                            except ValueError:
                                pass
            continue
        field_name = native_fields.get(source_kind)
        if field_name is None:
            continue
        values = _native_nonzero_pointer_values(event, field_name)
        if source_kind == "externalSourceRegistration":
            summary["nativeRegistrationContexts"].update(values)
        elif source_kind == "externalSourceCallbackQueueAppend":
            summary["nativeQueueContexts"].update(values)
        else:
            summary["nativeResolverContexts"].update(values)

    result: list[dict[str, Any]] = []
    for session_id in session_order:
        summary = summaries.get(session_id)
        if summary is None:
            continue
        managed = sorted(summary["managedCallbackCookies"])
        registration = sorted(summary["nativeRegistrationContexts"])
        resolver = sorted(summary["nativeResolverContexts"])
        queue = sorted(summary["nativeQueueContexts"])
        callback_chains = summary["managedExternalCallbackChains"]
        shared_resolver = sorted(set(managed) & set(resolver))
        shared_registration = sorted(set(managed) & set(registration))
        shared_queue = sorted(set(managed) & set(queue))
        queue_records = sorted(summary["nativeQueueRecordPointers"])
        queue_detach_heads = sorted(summary["nativeQueueDetachHeadPointers"])
        queue_getter_records = sorted(summary["nativeQueueGetterRecordPointers"])
        shared_queue_getter_records = sorted(
            set(queue_records) & set(queue_getter_records)
        )
        shared_queue_detach_records = sorted(
            set(queue_records) & set(queue_detach_heads)
        )
        getter_rows = []
        operation20_records = []
        queue_record_set = set(queue_records)
        for record in queue_getter_records:
            getter = summary["nativeQueueGetterRecords"].get(record, {})
            types = sorted(getter.get("types", set()))
            if 0x20 in types and record in queue_record_set:
                operation20_records.append(record)
            getter_rows.append({
                "recordPointer": record,
                "cookies": sorted(getter.get("cookies", set()))[:MAX_NATIVE_POINTER_SAMPLES],
                "types": types,
                "payloads": sorted(getter.get("payloads", set()))[:MAX_NATIVE_POINTER_SAMPLES],
            })
        result.append({
            "sessionId": session_id,
            "managedCallbackCookies": managed[:MAX_NATIVE_POINTER_SAMPLES],
            "managedCallbackCookiesTruncated": len(managed) > MAX_NATIVE_POINTER_SAMPLES,
            "nativeRegistrationContexts": registration[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeRegistrationContextsTruncated": len(registration) > MAX_NATIVE_POINTER_SAMPLES,
            "nativeResolverContexts": resolver[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeResolverContextsTruncated": len(resolver) > MAX_NATIVE_POINTER_SAMPLES,
            "nativeQueueContexts": queue[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeQueueContextsTruncated": len(queue) > MAX_NATIVE_POINTER_SAMPLES,
            "nativeQueueRecordPointers": queue_records[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeQueueRecordPointersTruncated": len(queue_records) > MAX_NATIVE_POINTER_SAMPLES,
            "nativeQueueDetachHeadPointers": queue_detach_heads[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeQueueDetachHeadPointersTruncated": len(queue_detach_heads) > MAX_NATIVE_POINTER_SAMPLES,
            "nativeQueueGetterRecordPointers": queue_getter_records[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeQueueGetterRecordPointersTruncated": len(queue_getter_records) > MAX_NATIVE_POINTER_SAMPLES,
            "sharedQueueAppendGetterRecordPointers": shared_queue_getter_records[:MAX_NATIVE_POINTER_SAMPLES],
            "sharedQueueAppendDetachHeadPointers": shared_queue_detach_records[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeQueueGetterRecords": getter_rows[:MAX_NATIVE_POINTER_SAMPLES],
            "nativeQueueGetterRecordsTruncated": len(getter_rows) > MAX_NATIVE_POINTER_SAMPLES,
            "consumedOperation20RecordPointers": operation20_records[:MAX_NATIVE_POINTER_SAMPLES],
            "sharedManagedResolverContexts": shared_resolver,
            "sharedManagedRegistrationContexts": shared_registration,
            "sharedManagedQueueContexts": shared_queue,
            "managedWwisePumpCaptures": sorted(
                summary["managedWwisePumpCaptures"]
            )[:MAX_NATIVE_POINTER_SAMPLES],
            "managedWwisePumpCaptureCount": len(
                summary["managedWwisePumpCaptures"]
            ),
            "managedWwiseDispatchCaptures": sorted(
                summary["managedWwiseDispatchCaptures"]
            )[:MAX_NATIVE_POINTER_SAMPLES],
            "managedWwiseDispatchCaptureCount": len(
                summary["managedWwiseDispatchCaptures"]
            ),
            "managedWwiseDispatchTypes": sorted(
                summary["managedWwiseDispatchTypes"]
            ),
            "managedExternalCallbackCaptures": sorted(
                summary["managedExternalCallbackCaptures"]
            )[:MAX_NATIVE_POINTER_SAMPLES],
            "managedExternalCallbackCaptureCount": len(
                summary["managedExternalCallbackCaptures"]
            ),
            "managedExternalCallbackTypes": sorted(
                summary["managedExternalCallbackTypes"]
            ),
            "managedExternalCallbackChainCount": len(callback_chains),
            "managedExternalCallbackChains": callback_chains[
                :MAX_NATIVE_POINTER_SAMPLES
            ],
            "managedExternalCallbackChainsTruncated": len(callback_chains)
            > MAX_NATIVE_POINTER_SAMPLES,
            "evidenceBoundary": (
                "Same pointer observed at native registration/resolver/queue and "
                "managed external-source callback boundaries is bounded "
                "callback-context transport evidence. It does not prove the "
                "external-source key, selected file, handle, decoder, PCM, or "
                "audibility. A parent-capture chain through the managed Wwise "
                "callback pump and callback-info dispatcher proves managed "
                "callback delivery in that capture, but still does not join "
                "the native resolver descriptor or file/PCM path. A shared "
                "queue record pointer between append and getter proves that a "
                "native node reached the managed callback-pump getters; an "
                "operation-0x20 row still carries only callback cookie/payload "
                "data and does not identify sourceInfo, a file handle, decoder, "
                "or PCM."
            ),
        })
    return result


def summarize_codec_stream_callbacks(
    observations: list[dict[str, Any]],
    session_order: list[str],
) -> list[dict[str, Any]]:
    """Summarize indirect codec callback observations without inferring I/O."""
    summaries: dict[str, dict[str, Any]] = {}
    for event in observations:
        if event.get("sourceKind") != "wwiseCodecStreamRead":
            continue
        session_id = event.get("sessionId")
        if not isinstance(session_id, str):
            continue
        summary = summaries.setdefault(
            session_id,
            {
                "sessionId": session_id,
                "callCount": 0,
                "resultCount": 0,
                "callbackPointers": set(),
                "contextPointers": set(),
                "bufferPointers": set(),
                "streamCapacities": set(),
                "streamCursors": set(),
                "requestedBytes": set(),
            },
        )
        if event.get("kind") == "audio_native_call":
            summary["callCount"] += 1
        elif event.get("kind") == "audio_native_result":
            summary["resultCount"] += 1
        for field_name, output_name in (
            ("streamCallback", "callbackPointers"),
            ("streamCallbackContext", "contextPointers"),
            ("streamBuffer", "bufferPointers"),
        ):
            summary[output_name].update(_native_text_values(event, field_name))
        for field_name, output_name in (
            ("streamCapacity", "streamCapacities"),
            ("streamCursor", "streamCursors"),
        ):
            summary[output_name].update(_native_numeric_values(event, field_name))
        summary["requestedBytes"].update(_native_numeric_values(event, "requestedBytes"))

    result: list[dict[str, Any]] = []
    for session_id in session_order:
        summary = summaries.get(session_id)
        if summary is None:
            continue
        row = dict(summary)
        for field_name in ("callbackPointers", "contextPointers", "bufferPointers"):
            values = sorted(row[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        for field_name in ("streamCapacities", "streamCursors", "requestedBytes"):
            values = sorted(row[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        row["evidenceBoundary"] = (
            "Indirect callback/context and bounded stream-state observations; "
            "pointer identity is not proof of the default I/O object, external-key "
            "ownership, or decoded PCM."
        )
        result.append(row)
    return result


def summarize_codec_memory_source_copies(
    observations: list[dict[str, Any]],
    session_order: list[str],
) -> list[dict[str, Any]]:
    """Summarize the bounded memory-source copier/refill boundary."""
    summaries: dict[str, dict[str, Any]] = {}
    for event in observations:
        if event.get("sourceKind") != "wwiseCodecMemorySourceCopy":
            continue
        session_id = event.get("sessionId")
        if not isinstance(session_id, str):
            continue
        summary = summaries.setdefault(
            session_id,
            {
                "sessionId": session_id,
                "callCount": 0,
                "resultCount": 0,
                "sourceBufferPointers": set(),
                "refillObjectPointers": set(),
                "sourceAvailable": set(),
                "sourceOffsets": set(),
                "requestedBytes": set(),
            },
        )
        if event.get("kind") == "audio_native_call":
            summary["callCount"] += 1
        elif event.get("kind") == "audio_native_result":
            summary["resultCount"] += 1
        summary["sourceBufferPointers"].update(_native_text_values(event, "sourceBuffer"))
        summary["refillObjectPointers"].update(_native_text_values(event, "refillObject"))
        for field_name, output_name in (
            ("sourceAvailable", "sourceAvailable"),
            ("sourceOffset", "sourceOffsets"),
            ("requestedBytes", "requestedBytes"),
        ):
            summary[output_name].update(_native_numeric_values(event, field_name))

    result: list[dict[str, Any]] = []
    for session_id in session_order:
        summary = summaries.get(session_id)
        if summary is None:
            continue
        row = dict(summary)
        for field_name in ("sourceBufferPointers", "refillObjectPointers"):
            values = sorted(row[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        for field_name in ("sourceAvailable", "sourceOffsets", "requestedBytes"):
            values = sorted(row[field_name])
            row[field_name] = values[:MAX_NATIVE_POINTER_SAMPLES]
            row[f"{field_name}Truncated"] = len(values) > MAX_NATIVE_POINTER_SAMPLES
        row["evidenceBoundary"] = (
            "Memory-source copy/refill observations only; the indirect refill "
            "vtable and source ownership are not identified by these rows."
        )
        result.append(row)
    return result


def summarize_native_call_relations(
    observations: list[dict[str, Any]],
    session_order: list[str],
) -> list[dict[str, Any]]:
    """Report exact same-thread synchronous native-hook nesting.

    ``nativeParentCaptureId`` is assigned by the Frida agent from a per-thread
    native interceptor stack.  Only resolve a relation when the parent id is a
    native call in the same session; timing or same-session adjacency is not
    enough to create a relation.
    """
    calls: dict[tuple[str, str], dict[str, Any]] = {}
    for event in observations:
        if event.get("kind") != "audio_native_call":
            continue
        capture_id = event.get("nativeCaptureId")
        session_id = event.get("sessionId")
        if isinstance(session_id, str) and isinstance(capture_id, str) and capture_id:
            calls[(session_id, capture_id)] = event

    relations: list[dict[str, Any]] = []
    for event in observations:
        if event.get("kind") != "audio_native_call":
            continue
        session_id = event.get("sessionId")
        child_id = event.get("nativeCaptureId")
        parent_id = event.get("nativeParentCaptureId")
        if not (
            isinstance(session_id, str)
            and isinstance(child_id, str)
            and isinstance(parent_id, str)
            and parent_id
        ):
            continue
        parent = calls.get((session_id, parent_id))
        if parent is None:
            continue
        relations.append({
            "sessionId": session_id,
            "parentNativeCaptureId": parent_id,
            "childNativeCaptureId": child_id,
            "parentSourceKind": parent.get("sourceKind"),
            "childSourceKind": event.get("sourceKind"),
            "parentHookName": parent.get("hookName"),
            "childHookName": event.get("hookName"),
            "relation": "synchronousNativeHookNesting",
        })
    session_rank = {session_id: index for index, session_id in enumerate(session_order)}
    relations.sort(
        key=lambda row: (
            session_rank.get(row["sessionId"], len(session_rank)),
            row["parentNativeCaptureId"],
            row["childNativeCaptureId"],
        )
    )
    return relations


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
    by_native_capture: dict[tuple[str, str], dict[str, Any]] = {}
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
    native_pairs = 0
    native_unpaired_results = 0

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
                "selectedGameRoot": event.get("selectedGameRoot"),
                "expectedModulePath": event.get("expectedModulePath"),
                "expectedModuleSize": event.get("expectedModuleSize"),
                "expectedModuleSha256": event.get("expectedModuleSha256"),
                "attachedModulePath": event.get("attachedModulePath"),
                "attachedModuleSize": event.get("attachedModuleSize"),
                "attachedModuleSha256": event.get("attachedModuleSha256"),
                "expectedNativeModulePath": event.get("expectedNativeModulePath"),
                "expectedNativeModuleSize": event.get("expectedNativeModuleSize"),
                "expectedNativeModuleSha256": event.get("expectedNativeModuleSha256"),
                "attachedNativeModulePath": event.get("attachedNativeModulePath"),
                "attachedNativeModuleSize": event.get("attachedNativeModuleSize"),
                "attachedNativeModuleSha256": event.get("attachedNativeModuleSha256"),
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
            for key in (
                "attachedModulePath", "attachedModuleSize", "attachedModuleSha256",
                "modulePathMatch", "moduleSizeMatch", "moduleSha256Match",
                "attachedNativeModulePath", "attachedNativeModuleSize",
                "attachedNativeModuleSha256", "nativeModulePathMatch", "nativeModuleSizeMatch",
                "nativeModuleSha256Match",
            ):
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
        if kind == "audio_native_call":
            native_capture_id = event.get("nativeCaptureId")
            if isinstance(native_capture_id, str) and native_capture_id:
                by_native_capture[(session_id, native_capture_id)] = event
        if kind == "audio_native_result":
            native_capture_id = event.get("nativeCaptureId")
            native_call = (
                by_native_capture.get((session_id, native_capture_id))
                if isinstance(native_capture_id, str) else None
            )
            if native_call:
                native_pairs += 1
                event["nativeCallArguments"] = native_call.get("arguments")
                event["nativeCallDecodedArguments"] = native_call.get("decodedArguments")
                event["nativeCallMemory"] = native_call.get("memory")
                event["nativeCallHookName"] = native_call.get("hookName")
            else:
                native_unpaired_results += 1
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
            for key in (
                "modulePathMatch", "moduleSizeMatch", "moduleSha256Match",
                "nativeModulePathMatch", "nativeModuleSizeMatch", "nativeModuleSha256Match",
            )
            if key in session
        }
        if facts:
            module_verification_rows.append({"sessionId": session_id, **facts})
    if not module_verification_rows:
        runtime_evidence_status = "notRecorded"
    elif all(
        row.get("modulePathMatch") is True
        and row.get("moduleSizeMatch") is True
        and row.get("moduleSha256Match") is True
        for row in module_verification_rows
    ) and all(
        all(key in row for key in ("modulePathMatch", "moduleSizeMatch", "moduleSha256Match"))
        for row in module_verification_rows
    ):
        runtime_evidence_status = "verified"
    else:
        runtime_evidence_status = "degraded"
    native_rows = [
        row for row in module_verification_rows
        if "nativeModulePathMatch" in row or "nativeModuleSizeMatch" in row
    ]
    if not native_rows:
        native_runtime_evidence_status = "notRecorded"
    elif all(
        row.get("nativeModulePathMatch") is True
        and row.get("nativeModuleSizeMatch") is True
        and row.get("nativeModuleSha256Match") is True
        for row in native_rows
    ):
        native_runtime_evidence_status = "verified"
    else:
        native_runtime_evidence_status = "degraded"
    native_key_sets: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for event in observations:
        if event.get("kind") not in {"audio_native_call", "audio_native_result"}:
            continue
        source_kind = event.get("sourceKind")
        if not isinstance(source_kind, str):
            continue
        keys = native_key_values(event)
        if keys:
            for key in keys:
                native_key_sets[event["sessionId"]][source_kind].add(key)
    native_key_correlations = []
    for session_id in session_order:
        source_sets = native_key_sets.get(session_id, {})
        external_keys = source_sets.get("externalSourceLookup", set())
        source_media_keys = source_sets.get("wwiseSourceMediaLookup", set())
        shared_keys = external_keys & source_media_keys
        if not external_keys and not source_media_keys:
            continue
        native_key_correlations.append({
            "sessionId": session_id,
            "externalSourceLookupKeys": sorted(external_keys),
            "wwiseSourceMediaLookupKeys": sorted(source_media_keys),
            "sharedKeys": sorted(shared_keys),
            "evidenceBoundary": "same decoded numeric key observed at two native boundaries; not proof of one handle, read request, or decoded stream",
        })
    native_key_lifecycle = summarize_native_key_lifecycle(observations, session_order)
    native_call_relations = summarize_native_call_relations(observations, session_order)
    managed_external_path_lifecycle = summarize_managed_external_path_lifecycle(
        observations,
        session_order,
    )
    callback_lifecycle = summarize_callback_lifecycle(observations, session_order)
    codec_stream_callbacks = summarize_codec_stream_callbacks(observations, session_order)
    codec_memory_source_copies = summarize_codec_memory_source_copies(observations, session_order)
    native_pairing_gate = native_runtime_evidence_status == "verified"
    if not native_pairing_gate:
        native_pairs = 0
        native_unpaired_results = 0
        native_key_correlations = []
        native_key_lifecycle = []
        native_call_relations = []
        managed_external_path_lifecycle = []
        callback_lifecycle = []
        codec_stream_callbacks = []
        codec_memory_source_copies = []
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
        "nativeRuntimeEvidenceStatus": native_runtime_evidence_status,
        "nativePairing": {
            "status": native_runtime_evidence_status,
            "available": native_pairing_gate,
            "reason": (
                "Native lifecycle summaries are withheld until session_end records "
                "matching path, size, and SHA-256 facts for AkSoundEngine.dll."
                if not native_pairing_gate else "verified native module gate"
            ),
            "pairedCallResultCount": native_pairs,
            "unpairedResultCount": native_unpaired_results,
            "keyCorrelations": native_key_correlations,
            "keyLifecycle": native_key_lifecycle,
            "managedExternalPathLifecycle": managed_external_path_lifecycle,
            "callbackLifecycle": callback_lifecycle,
            "codecStreamCallbacks": codec_stream_callbacks,
            "codecMemorySourceCopies": codec_memory_source_copies,
            "nativeCallRelations": native_call_relations,
            "evidenceBoundary": "call/result pairing uses the probe's capture id; native call relations use exact same-thread synchronous parent ids; key correlations and decoder-entry intersections are bounded native observations, not a file-handle or PCM join",
        },
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
            "moduleVerification": "runtime observations are verified only when the attached module path, size, and SHA-256 match the hash-locked GameAssembly; missing or mismatched facts are not equivalent to verified runtime evidence",
            "nativeModuleVerification": "native lifecycle summaries are emitted only when the attached AkSoundEngine path, size, and SHA-256 match the hash-locked file; they do not by themselves correlate an external key to a file handle or decoded PCM",
            "nativeKeyLifecycle": "same-session key intersections across registration, manager join, decoder registry, source-media lookup, decoder-entry invocation, and observed path boundaries are bounded evidence only; exact manager-entry and retained-descriptor pointer intersections are stronger same-entry/ownership evidence, while decoder-entry/provider intersections add continuity into a decode call but pointer, handle, read, codec-output, and PCM identity must still be correlated",
            "nativeCallRelations": "nativeParentCaptureId resolves only exact same-thread synchronous nesting between attached native hooks; it does not prove asynchronous ownership, file selection, handle identity, decoder stream, PCM, or audibility",
            "managedExternalPathLifecycle": "VoicePlayer and Adapter externalSourceKey observations are joined through the bounded parent-capture chain and exact same-session path strings only; these do not prove a native descriptor, file handle, codec stream, selected branch, or audible PCM",
            "callbackLifecycle": "Same-session pointer intersections between native resolver/queue contexts and the managed callback cookie are bounded callback-transport evidence; a parent-capture chain through the managed Wwise pump and callback-info dispatcher proves managed callback delivery in that capture, but neither relation proves key, file, handle, decoder, PCM, or audibility",
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
        f"- native module evidence status: `{bundle['nativeRuntimeEvidenceStatus']}`",
        f"- paired native call/results: `{bundle['nativePairing']['pairedCallResultCount']}`",
        f"- synchronous native call relations: `{len(bundle['nativePairing']['nativeCallRelations'])}`",
        f"- sessions with codec stream callback observations: `{len(bundle['nativePairing']['codecStreamCallbacks'])}`",
        f"- sessions with codec memory-source copy observations: `{len(bundle['nativePairing']['codecMemorySourceCopies'])}`",
        f"- sessions with managed external-path observations: `{len(bundle['nativePairing']['managedExternalPathLifecycle'])}`",
        f"- sessions with shared registration/join manager-entry pointers: `{sum(bool(row.get('sharedRegistrationJoinEntryPointers')) for row in bundle['nativePairing']['keyLifecycle'])}`",
        f"- sessions with shared manager-entry/descriptor allocations: `{sum(bool(row.get('sharedManagerDescriptorAllocationBases')) for row in bundle['nativePairing']['keyLifecycle'])}`",
        f"- sessions with callback-context observations: `{len(bundle['nativePairing']['callbackLifecycle'])}`",
        f"- sessions with managed Wwise callback-chain observations: `{sum(bool(row.get('managedExternalCallbackChainCount')) for row in bundle['nativePairing']['callbackLifecycle'])}`",
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
        "incompatible static inputs are reported as degraded. Native calls are "
        "accepted only from the hash-locked AkSoundEngine module and still need "
        "capture-time correlation before they establish a key-to-file mapping. "
        "Codec stream callback summaries preserve indirect callback/context and "
        "buffer-state observations without treating them as decoded PCM. Memory-source "
        "copy summaries remain separate from the unresolved refill producer. Managed "
        "external-path lifecycle rows preserve parent-capture and exact path-string "
        "matches without promoting them to native handle or PCM identity. Callback "
        "lifecycle rows preserve bounded native-context to managed-cookie matches "
        "without promoting them to key, file, decoder, or PCM identity. Decoder "
        "entry rows preserve the actual generic-decoder invocation, owner key, "
        "provider interface, float output pointer, and produced frame count; "
        "registry/provider intersections are continuity evidence into decoding, "
        "not a standalone PCM or audibility claim. A "
        "parent-capture chain through the managed Wwise pump and callback-info "
        "dispatcher is reported separately as callback-delivery evidence, not "
        "as a native file or PCM join.",
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
