"""Project verified offline audio-capture observations onto Audio rows.

The runtime trace importer owns capture normalization. This module owns the
small publication join used by the Audio semantic builder; it never infers a
consumer from static names or from an unverified capture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


BUNDLE_SCHEMA = "audioRuntimeTrace.v1"
MAX_OBSERVATIONS_PER_EVENT = 12
MAX_IDS_PER_ROW = 32


def _input_status(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    status: dict[str, Any] = {
        "path": str(path.resolve()),
        "status": "missing",
        "sha256": None,
    }
    if not path.is_file():
        status["reason"] = "file_missing"
        return status, None
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        status.update({"status": "degraded", "reason": f"invalid_json:{type(exc).__name__}"})
        return status, None
    status["sha256"] = hashlib.sha256(raw).hexdigest()
    if not isinstance(payload, dict):
        status.update({"status": "degraded", "reason": "root_not_object"})
        return status, None
    status.update({
        "status": "ready",
        "schema": payload.get("schema"),
        "runtimeEvidenceStatus": payload.get("runtimeEvidenceStatus"),
        "language": next(
            (
                str(session.get("language"))
                for session in payload.get("sessions") or ()
                if isinstance(session, dict) and session.get("language")
            ),
            None,
        ),
    })
    return status, payload


def _event_key(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip().casefold()
    return None


def _event_hash(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    if isinstance(value, str):
        try:
            return int(value, 0) & 0xFFFFFFFF
        except ValueError:
            return None
    return None


def _compact_observation(row: dict[str, Any]) -> dict[str, Any]:
    resolution = row.get("eventResolution")
    compact: dict[str, Any] = {
        key: row[key]
        for key in ("sessionId", "seq", "monotonicMs", "kind", "sourceKind", "hookName", "captureId", "threadId")
        if row.get(key) not in (None, "", [])
    }
    if isinstance(resolution, dict):
        compact["eventResolution"] = {
            key: resolution[key]
            for key in ("eventId", "eventKey", "resolution", "eventNameCandidates", "mediaCandidates", "categories")
            if resolution.get(key) not in (None, "", [])
        }
    if row.get("runtimeExecutionObserved") is True:
        compact["runtimeExecutionObserved"] = True
    return compact


def apply_verified_runtime_observations(
    events: list[dict[str, Any]],
    media: list[dict[str, Any]],
    bundle_path: Path | None,
    *,
    expected_language: str,
) -> dict[str, Any]:
    """Annotate exact Event/media rows from one verified capture bundle."""

    if bundle_path is None:
        return {
            "schemaVersion": 1,
            "status": "notRequested",
            "bindingCount": 0,
            "eventCount": 0,
            "mediaCount": 0,
            "evidenceBoundary": "No runtime capture bundle was requested.",
        }
    status, payload = _input_status(bundle_path)
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "status": status.get("status"),
        "input": status,
        "bindingCount": 0,
        "eventCount": 0,
        "mediaCount": 0,
        "evidenceBoundary": (
            "Observed managed request rows are published only when the capture "
            "bundle has the current schema, one matching language, and verified "
            "GameAssembly path/size/SHA-256 facts. These rows prove execution of "
            "the captured request, not Wwise branch selection, decoded media, or audibility."
        ),
    }
    if payload is None:
        return result
    if payload.get("schema") != BUNDLE_SCHEMA:
        result.update({"status": "degraded", "reason": "schema_mismatch"})
        return result
    trace_language = status.get("language")
    if trace_language and str(trace_language).upper() != expected_language.upper():
        result.update({"status": "degraded", "reason": "language_mismatch"})
        return result
    if payload.get("runtimeEvidenceStatus") != "verified":
        result.update({"status": "degraded", "reason": "gameassembly_not_verified"})
        return result

    by_hash: dict[int, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = _event_key(event.get("id") or event.get("eventId") or event.get("name"))
        if event_id:
            by_name[event_id] = event
        event_hash = _event_hash(event.get("hash") or event.get("eventHash"))
        if event_hash is not None:
            by_hash[event_hash] = event

    observations_by_event: dict[int, list[dict[str, Any]]] = {}
    unresolved = 0
    for row in payload.get("observations") or ():
        if not isinstance(row, dict) or row.get("runtimeExecutionObserved") is not True:
            continue
        resolution = row.get("eventResolution")
        if not isinstance(resolution, dict):
            unresolved += 1
            continue
        target = None
        event_hash = _event_hash(resolution.get("eventId"))
        if event_hash is not None:
            target = by_hash.get(event_hash)
        if target is None:
            event_name = _event_key(resolution.get("eventKey"))
            if event_name:
                target = by_name.get(event_name)
        if target is None:
            candidates = resolution.get("eventNameCandidates")
            if isinstance(candidates, list) and len(candidates) == 1:
                target = by_name.get(_event_key(candidates[0]) or "")
        if target is None:
            unresolved += 1
            continue
        marker = id(target)
        observations_by_event.setdefault(marker, []).append(_compact_observation(row))

    for event in events:
        rows = observations_by_event.get(id(event))
        if not rows:
            continue
        rows.sort(key=lambda row: (str(row.get("sessionId") or ""), int(row.get("seq") or 0)))
        event["runtimeObservationStatus"] = "verifiedObservedRequest"
        event["runtimeObservationCount"] = len(rows)
        event["runtimeObservations"] = rows[:MAX_OBSERVATIONS_PER_EVENT]
        event["runtimeObservationsTruncated"] = len(rows) > MAX_OBSERVATIONS_PER_EVENT
        event["runtimeObservationSessionIds"] = sorted({str(row.get("sessionId")) for row in rows})[:MAX_IDS_PER_ROW]
        event["runtimeObservationSourceKinds"] = sorted({str(row.get("sourceKind")) for row in rows if row.get("sourceKind")})[:MAX_IDS_PER_ROW]
        result["eventCount"] += 1
        result["bindingCount"] += len(rows)

    observed_by_name = {
        str(event.get("id") or event.get("eventId") or "").casefold(): event
        for event in events
        if event.get("runtimeObservationStatus") == "verifiedObservedRequest"
    }
    for row in media:
        event_ids = {
            str(value).casefold()
            for value in row.get("eventIds") or ()
            if str(value).strip()
        }
        matched = [observed_by_name[event_id] for event_id in event_ids if event_id in observed_by_name]
        if not matched:
            continue
        row["runtimeObservationStatus"] = "verifiedObservedEventRelation"
        row["runtimeObservedEventIds"] = sorted({str(event.get("id")) for event in matched})[:MAX_IDS_PER_ROW]
        row["runtimeObservationSessionIds"] = sorted({session for event in matched for session in event.get("runtimeObservationSessionIds") or ()})[:MAX_IDS_PER_ROW]
        row["runtimeObservationCount"] = sum(int(event.get("runtimeObservationCount") or 0) for event in matched)
        result["mediaCount"] += 1
    result.update({"status": "ready", "unresolvedObservationCount": unresolved})
    return result
