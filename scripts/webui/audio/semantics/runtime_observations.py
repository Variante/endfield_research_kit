"""Project verified offline audio-capture observations onto Audio rows.

The runtime trace importer owns capture normalization. This module owns the
small publication join used by the Audio semantic builder; it never infers a
consumer from static names or from an unverified capture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


BUNDLE_SCHEMA = "audioRuntimeTrace.v1"
MAX_OBSERVATIONS_PER_EVENT = 12
MAX_IDS_PER_ROW = 32
MAX_EXTERNAL_PATH_LENGTH = 4096
EXTERNAL_REQUEST_BOUNDARY = (
    "The full externalSourceKey path and scalar cookie were observed at the "
    "managed external audio request boundary in a verified capture. These "
    "requests are not bound to decoded media because the publication has no "
    "stored original full VFS sourcePath for an exact comparison. They do not "
    "prove native source instance selection, file opening, codec use, or audibility."
)


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


def _file_sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def _external_source_requests(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep captured request paths separate from Event and media ownership."""

    result: dict[str, Any] = {
        "externalSourceRequestsStatus": "notObserved",
        "externalSourceRequestCount": 0,
        "externalSourcePathCount": 0,
        "externalSourceMediaBindingCount": 0,
        "externalSourceRequests": [],
        "externalSourceRequestsTruncated": False,
        "externalSourceRequestEvidenceBoundary": EXTERNAL_REQUEST_BOUNDARY,
    }
    candidates = [
        row for row in payload.get("observations") or ()
        if isinstance(row, dict)
        and row.get("runtimeExecutionObserved") is True
        and row.get("kind") == "audio_request"
        and row.get("sourceKind") == "adapterExternalSourcePostEvent"
        and row.get("hookName") == "AudioAdapter._PostEventWithExternalSource"
    ]
    if not candidates:
        return result
    sessions: dict[str, dict[str, Any]] = {}
    for session in payload.get("sessions") or ():
        if not isinstance(session, dict) or not isinstance(session.get("id"), str):
            continue
        if session["id"] in sessions:
            result.update({"externalSourceRequestsStatus": "degraded", "externalSourceRequestsReason": "duplicate_session_id"})
            return result
        sessions[session["id"]] = session
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        session = sessions.get(str(row.get("sessionId") or ""))
        if (
            session is None
            or session.get("closed") is not True
            or session.get("captureComplete") is not True
            or any(session.get(key) != 0 for key in (
                "droppedEventCount", "activeManagedCallCount", "activeNativeCallCount", "agentDiagnosticCount",
            ))
        ):
            result.update({"externalSourceRequestsStatus": "degraded", "externalSourceRequestsReason": "external_request_session_incomplete"})
            return result
        arguments = row.get("arguments")
        path = arguments.get("externalSourceKey") if isinstance(arguments, dict) else None
        cookie = arguments.get("externalCookie") if isinstance(arguments, dict) else None
        if (
            not isinstance(path, str) or not path or "\x00" in path
            or len(path) > MAX_EXTERNAL_PATH_LENGTH
            or isinstance(cookie, bool) or not isinstance(cookie, int)
            or not 0 <= cookie <= 0xFFFFFFFF
        ):
            result.update({"externalSourceRequestsStatus": "degraded", "externalSourceRequestsReason": "invalid_external_request_arguments"})
            return result
        compact = _compact_observation(row)
        compact["arguments"] = {
            key: arguments[key]
            for key in ("externalSourceKey", "externalCookie", "eventId", "audioObjectId")
            if isinstance(arguments.get(key), (str, int)) and not isinstance(arguments.get(key), bool)
        }
        groups.setdefault(path, []).append(compact)
    summaries = []
    for path, rows in sorted(groups.items()):
        rows.sort(key=lambda row: (str(row.get("sessionId") or ""), int(row.get("seq") or 0)))
        summaries.append({
            "externalSourceKey": path,
            "observationCount": len(rows),
            "sessionIds": sorted({str(row.get("sessionId")) for row in rows})[:MAX_IDS_PER_ROW],
            "externalCookies": sorted({row["arguments"]["externalCookie"] for row in rows})[:MAX_IDS_PER_ROW],
            "observations": rows[:MAX_OBSERVATIONS_PER_EVENT],
            "observationsTruncated": len(rows) > MAX_OBSERVATIONS_PER_EVENT,
            "mediaBindingStatus": "notBoundOriginalVfsSourcePathUnavailable",
            "evidenceBoundary": "direct",
        })
    result.update({
        "externalSourceRequestsStatus": "ready",
        "externalSourceRequestCount": len(candidates),
        "externalSourcePathCount": len(groups),
        "externalSourceRequests": summaries[:MAX_IDS_PER_ROW],
        "externalSourceRequestsTruncated": len(summaries) > MAX_IDS_PER_ROW,
    })
    return result


def _native_source_observations(payload: dict[str, Any], native_context: Any) -> dict[str, Any]:
    """Replay capture proof on the build-selected pair, independent of other Audio contracts."""
    result: dict[str, Any] = {
        "nativeSourceObservationsStatus": "notRequested", "nativeSourceCaptureCount": 0,
        "nativeSourcePairCount": 0, "nativeSourceNestedPairCount": 0,
        "nativeSourceBridgeCaptureCount": 0, "nativeSourceBridgeChainCount": 0,
        "nativeOwnerCarrierCaptureCount": 0, "nativeOwnerDecoderSnapshotMatchCount": 0,
        "nativeSourceCaptures": [], "nativeSourceCapturesTruncated": False,
        "nativeSourceEvidenceBoundary": (
            "Anonymous captured source fields and strict same-thread native consumer/LockDataPtr "
            "relations only. No Event, media, managed path, pointer lifetime, successful lookup, "
            "decoded content or audibility is established."
        ),
    }
    pairing = payload.get("nativePairing")
    proof = pairing.get("sourceObserver") if isinstance(pairing, dict) else None
    if proof is None:
        return result
    result["nativeSourceObservationsStatus"] = "degraded"
    gameassembly = getattr(native_context, "gameassembly_path", None)
    metadata = getattr(native_context, "metadata_path", None)
    if gameassembly is None or metadata is None:
        result["nativeSourceObservationsReason"] = "explicit_selected_native_paths_missing"
        return result
    from scripts.webui.story_recovery import runtime_trace_audio_import as importer

    captures = proof.get("captures") if isinstance(proof, dict) else None
    limits = proof.get("limits") if isinstance(proof, dict) else None
    if (not isinstance(proof, dict) or proof.get("schema") != importer.SOURCE_OBSERVER_SCHEMA
            or proof.get("status") != "verified" or not isinstance(captures, list)
            or not 0 < len(captures) <= MAX_IDS_PER_ROW or not isinstance(limits, dict)):
        result["nativeSourceObservationsReason"] = "invalid_source_observer_proof"
        return result
    try:
        traces = [Path(row["trace"]["path"]) for row in captures]
        manifests = [Path(row["manifest"]["path"]) for row in captures]
        _events, _sources, current = importer.read_source_observer_inputs(
            traces, manifests, Path(gameassembly).resolve().parent,
            max_input_bytes=limits["maxInputBytes"], max_events=limits["maxEvents"],
            gameassembly=Path(gameassembly), metadata=Path(metadata),
        )
        if current != proof:
            result["nativeSourceObservationsReason"] = "source_observer_replay_drift"
            return result
    except (OSError, ValueError, TypeError, KeyError, AttributeError, importer.core.CaptureConfigurationError) as exc:
        result.update({"nativeSourceObservationsReason": "source_observer_replay_failed",
                       "nativeSourceObservationsDetail": str(exc)[:1000]})
        return result
    result.update({
        "nativeSourceObservationsStatus": "ready", "nativeSourceCaptureCount": len(captures),
        "nativeSourcePairCount": sum(row["sourcePairCount"] for row in captures),
        "nativeSourceNestedPairCount": sum(row["sourceSummary"]["sourceConsumerRelations"]["nestedPairCount"] for row in captures),
        "nativeSourceBridgeCaptureCount": sum(
            bool(row["sourceSummary"].get("sourceBridgeRelations", {}).get("pathChainCount", 0))
            for row in captures
        ),
        "nativeSourceBridgeChainCount": sum(
            row["sourceSummary"].get("sourceBridgeRelations", {}).get("pathChainCount", 0)
            for row in captures
        ),
        "nativeOwnerCarrierCaptureCount": sum(
            "ownerCarrierRelations" in row["sourceSummary"] for row in captures
        ),
        "nativeOwnerDecoderSnapshotMatchCount": sum(
            row["sourceSummary"].get("ownerCarrierRelations", {}).get("ownerDecoderSnapshotMatchCount", 0)
            for row in captures
        ),
        "nativeSourceCaptures": [{
            "sessionIds": row["sessionIds"][:MAX_IDS_PER_ROW], "sessionCount": len(row["sessionIds"]),
            "sessionIdsTruncated": len(row["sessionIds"]) > MAX_IDS_PER_ROW,
            "observerProfile": row["observerProfile"],
            "eventCount": row["eventCount"], "sourcePairCount": row["sourcePairCount"],
            "sourceSummary": row["sourceSummary"], "evidenceBoundary": row["evidenceBoundary"],
        } for row in captures[:MAX_IDS_PER_ROW]],
        "nativeSourceCapturesTruncated": len(captures) > MAX_IDS_PER_ROW,
    })
    if result["nativeSourceBridgeChainCount"]:
        result["nativeSourceEvidenceBoundary"] = (
            "Captured native descriptor text to selected source and constructed owner, plus strict "
            "same-thread consumer/LockDataPtr relations. No Event, media, asynchronous managed-request "
            "ownership, pointer lifetime, file opening, decoded content or audibility is established."
        )
    if result["nativeOwnerDecoderSnapshotMatchCount"]:
        result["nativeSourceEvidenceBoundary"] += (
            " Entry-only owner/carrier/decoder snapshots establish local pointer equality, without "
            "atomicity, internal branch execution or continuity from an earlier source generation."
        )
    return result


def refresh_native_source_observations(
    current_observations: dict[str, Any], bundle_path: Path, *,
    gameassembly: Path, metadata: Path,
) -> dict[str, Any]:
    """Re-audit only the source child of the already published runtime bundle.

    Request/Event/media annotations remain valid only for exactly the same
    bundle. The selected native pair is authenticated by the strict source
    replay, independently of other Audio contracts. This function owns no file
    publication; the caller atomically replaces the surrounding index.
    """
    if not isinstance(current_observations, dict) or current_observations.get("status") != "ready":
        raise ValueError("runtime source refresh requires a ready published runtime bundle")
    previous_input = current_observations.get("input")
    if not isinstance(previous_input, dict) or previous_input.get("status") != "ready":
        raise ValueError("runtime source refresh requires the published bundle input receipt")
    if not isinstance(previous_input.get("path"), str) or not previous_input["path"]:
        raise ValueError("runtime source refresh requires the published bundle path")
    selected = Path(bundle_path).resolve()
    if Path(previous_input["path"]).resolve() != selected:
        raise ValueError("runtime source refresh bundle path differs from the publication")
    current_input, payload = _input_status(selected)
    if (payload is None or current_input.get("status") != "ready"
            or current_input.get("sha256") != previous_input.get("sha256")
            or payload.get("schema") != BUNDLE_SCHEMA
            or payload.get("runtimeEvidenceStatus") != "verified"):
        raise ValueError("runtime source refresh bundle digest/schema/status differs from the publication")
    pairing = payload.get("nativePairing")
    if not isinstance(pairing, dict) or "sourceObserver" not in pairing:
        raise ValueError("published runtime bundle has no source-observer proof to refresh")
    if gameassembly is None or metadata is None:
        raise ValueError("runtime source refresh requires an explicit selected native pair")
    native = _native_source_observations(payload, SimpleNamespace(
        gameassembly_path=Path(gameassembly).resolve(), metadata_path=Path(metadata).resolve(),
    ))
    if _file_sha256(selected) != current_input["sha256"]:
        raise ValueError("runtime source bundle changed during replay; publication withheld")
    return {**{key: value for key, value in current_observations.items()
               if not key.startswith(("nativeSource", "nativeOwner"))}, **native}


def apply_verified_runtime_observations(
    events: list[dict[str, Any]],
    media: list[dict[str, Any]],
    bundle_path: Path | None,
    *,
    expected_language: str,
    native_context: Any = None,
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
            "the captured request, not Wwise branch selection, decoded media, or audibility. "
            "External-source path requests remain separate metadata and never bind media "
            "through a basename, cookie, or reconstructed path."
        ),
    }
    if payload is None:
        return result
    if payload.get("schema") != BUNDLE_SCHEMA:
        result.update({"status": "degraded", "reason": "schema_mismatch"})
        return result
    trace_languages = {
        str(session.get("language")).upper()
        for session in payload.get("sessions") or ()
        if isinstance(session, dict) and session.get("language")
    }
    if any(language != expected_language.upper() for language in trace_languages):
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
    pairing = payload.get("nativePairing")
    anonymous_native_scope = isinstance(pairing, dict) and "sourceObserver" in pairing
    for row in payload.get("observations") or ():
        if not isinstance(row, dict) or row.get("runtimeExecutionObserved") is not True:
            continue
        if anonymous_native_scope and row.get("kind") in {"audio_native_call", "audio_native_result"}:
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

    external_requests = _external_source_requests(payload)
    native_sources = _native_source_observations(payload, native_context)
    if _file_sha256(bundle_path) != status.get("sha256"):
        result.update({"status": "degraded", "reason": "bundle_changed_before_projection"})
        if anonymous_native_scope:
            result.update({"nativeSourceObservationsStatus": "degraded",
                           "nativeSourceObservationsReason": "bundle_changed_before_projection"})
        return result
    result.update(external_requests)
    result.update(native_sources)

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
