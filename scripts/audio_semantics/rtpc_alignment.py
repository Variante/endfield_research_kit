"""Static GameParameter/RTPC alignment for the Audio semantic dataset.

This module joins three already recovered, authored surfaces:

* the six metadata ``AU_RTPC_*`` fields and their numeric HIRC IDs,
* serialized InitialRTPC curve/property evidence, and
* serialized Set/ResetGameParameter Action rows.

The metadata field names are native/static facts.  They are therefore only
published after the shared explicit ``global-metadata.dat`` + ``GameAssembly``
gate has validated the selected files.  No row in this module is a runtime
value, target-object, branch, DSP, or audibility observation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

if __package__ == "scripts.audio_semantics":
    from . import native_evidence
    from .rtpc_contract import (
        CANONICAL_METADATA_PREFIX,
        CANONICAL_RTPC_HEX,
        CANONICAL_RTPC_IDS,
    )
else:  # pragma: no cover - package modules are not direct-file entry points.
    from audio_semantics import native_evidence
    from audio_semantics.rtpc_contract import (
        CANONICAL_METADATA_PREFIX,
        CANONICAL_RTPC_HEX,
        CANONICAL_RTPC_IDS,
    )


SCHEMA_VERSION = 1
NATIVE_GATE_ID = "selected-global-metadata-and-gameassembly-exact-hash"
MAX_EVENT_IDS = 24
MAX_CONTROL_ROWS = 32
MAX_CURVE_EVIDENCE = 32
MAX_DIAGNOSTICS = 64

# This six-row contract is the projection boundary for the existing
# ``HIRC_GAME_PARAMETER_NAME_EVIDENCE`` catalog.  It deliberately does not
# accept arbitrary AU_RTPC-looking strings: a changed client or stale index
# must degrade instead of creating a plausible new native name/ID join.

EVIDENCE_BOUNDARY = (
    "AU_RTPC_* names and numeric IDs are exact static metadata field/value "
    "evidence cross-matched to serialized Wwise HIRC RTPC IDs. Curve/property "
    "and Set/ResetGameParameter rows are authored serialized controls. This "
    "catalog does not observe runtime parameter values, setter execution, target "
    "objects, selected branches, DSP state, or audibility."
)


def _u32(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            parsed = int(raw, 0)
        else:
            parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed & 0xFFFFFFFF


def _strict_u32(value: Any) -> int | None:
    """Parse one serialized uint32 without silently wrapping conflicts."""

    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            parsed = int(raw, 0)
        else:
            return None
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if 0 <= parsed <= 0xFFFFFFFF else None


def _paired_u32(
    row: Mapping[str, Any],
    numeric_key: str,
    hex_key: str,
    *,
    label: str,
) -> tuple[int | None, str | None]:
    """Parse paired numeric/hex identity fields without preferring either."""

    has_numeric = numeric_key in row and row.get(numeric_key) is not None
    has_hex = hex_key in row and row.get(hex_key) is not None
    if not has_numeric and not has_hex:
        return None, None
    numeric = _strict_u32(row.get(numeric_key)) if has_numeric else None
    hexadecimal = _strict_u32(row.get(hex_key)) if has_hex else None
    if has_numeric and numeric is None:
        return None, f"malformed {label} {numeric_key}"
    if has_hex and hexadecimal is None:
        return None, f"malformed {label} {hex_key}"
    if has_numeric and has_hex and numeric != hexadecimal:
        return None, f"conflicting {label} {numeric_key}/{hex_key}"
    return numeric if has_numeric else hexadecimal, None


def _hex(value: Any) -> str:
    parsed = _u32(value)
    return f"0x{parsed:08x}" if parsed is not None else ""


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


def _record_diagnostic(result: dict[str, Any], message: str) -> None:
    diagnostics = result.setdefault("diagnostics", [])
    if len(diagnostics) < MAX_DIAGNOSTICS:
        diagnostics.append(str(message)[:200])
    result["diagnosticCount"] = min(
        MAX_DIAGNOSTICS,
        int(result.get("diagnosticCount") or 0) + 1,
    )
    if result.get("status") == "validated":
        result["status"] = "degraded"


def _list_or_none(
    value: Any,
    result: dict[str, Any],
    *,
    label: str,
    allow_tuple: bool = False,
) -> list[Any] | None:
    if value is None:
        return []
    if allow_tuple and isinstance(value, tuple):
        return list(value)
    if not isinstance(value, list):
        _record_diagnostic(result, f"malformed {label}: expected list")
        return None
    return value


def _native_gate(native_context: Any) -> dict[str, Any]:
    """Return a strict publication gate without trusting synthetic contexts."""

    if native_context is None:
        return {
            "status": "missing",
            "reason": "selected native inputs were not provided",
            "gateVerified": False,
        }
    status = str(getattr(native_context, "status", "missing") or "missing")
    metadata_sha = str(getattr(native_context, "metadata_sha256", "") or "")
    gameassembly_sha = str(
        getattr(native_context, "gameassembly_sha256", "") or ""
    )
    gate_verified = bool(getattr(native_context, "gate_verified", False))
    if not gate_verified:
        return {
            "status": "unverified",
            "reason": (
                "native context did not record the explicit selected "
                "global-metadata.dat + GameAssembly.dll gate"
            ),
            "gateVerified": False,
            "metadataSha256": metadata_sha or None,
            "gameAssemblySha256": gameassembly_sha or None,
        }
    if status != "validated":
        return {
            "status": status,
            "reason": str(
                getattr(native_context, "reason", "")
                or "selected native inputs failed the exact hash gate"
            ),
            "gateVerified": True,
            "metadataSha256": metadata_sha or None,
            "gameAssemblySha256": gameassembly_sha or None,
        }
    if metadata_sha.casefold() != native_evidence.EXPECTED_METADATA_SHA256.casefold():
        return {
            "status": "mismatched",
            "reason": "validated native context has an unexpected metadata hash",
            "gateVerified": True,
            "metadataSha256": metadata_sha or None,
            "gameAssemblySha256": gameassembly_sha or None,
        }
    if gameassembly_sha.casefold() != native_evidence.EXPECTED_GAMEASSEMBLY_SHA256.casefold():
        return {
            "status": "mismatched",
            "reason": "validated native context has an unexpected GameAssembly hash",
            "gateVerified": True,
            "metadataSha256": metadata_sha or None,
            "gameAssemblySha256": gameassembly_sha or None,
        }
    return {
        "status": "validated",
        "reason": "explicit selected global-metadata.dat + GameAssembly.dll hashes",
        "gateVerified": True,
        "metadataSha256": metadata_sha,
        "gameAssemblySha256": gameassembly_sha,
    }


def _static_entries(
    audio_index: Mapping[str, Any],
    supplied: Iterable[Mapping[str, Any]] | None,
    selected_metadata_sha: str,
) -> tuple[list[dict[str, Any]], str, str]:
    """Validate the complete six-row static contract.

    The returned diagnostic is intentionally bounded and deterministic.  Any
    malformed shape, missing hash, unknown name, duplicate, ID/hex mismatch,
    or incomplete six-row set rejects the complete catalog.
    """

    if not isinstance(audio_index, Mapping):
        return [], "", "malformed hircSummary: audio index is not a mapping"
    summary = audio_index.get("hircSummary")
    if not isinstance(summary, Mapping):
        return [], "", "malformed hircSummary: expected mapping"
    post = summary.get("postProcessSummary")
    if not isinstance(post, Mapping):
        return [], "", "malformed postProcessSummary: expected mapping"
    evidence = post.get("gameParameterNameEvidence")
    if not isinstance(evidence, Mapping):
        return [], "", "malformed gameParameterNameEvidence: expected mapping"
    source = str(evidence.get("source") or "hircSummary.gameParameterNameEvidence")
    source_metadata_sha = str(evidence.get("metadataSha256") or "").strip()
    if not source_metadata_sha:
        return [], source, "static GameParameter evidence metadataSha256 is missing"
    if source_metadata_sha.casefold() != selected_metadata_sha.casefold():
        return [], source, "static GameParameter evidence metadataSha256 mismatches selected metadata"
    evidence_rows = evidence.get("entries")
    if not isinstance(evidence_rows, list):
        return [], source, "malformed gameParameterNameEvidence.entries: expected list"
    rows = evidence_rows if supplied is None else supplied
    if not isinstance(rows, list):
        return [], source, "malformed supplied static GameParameter entries: expected list"
    if supplied is not None and rows != evidence_rows:
        return [], source, "supplied static GameParameter entries differ from HIRC evidence"
    if len(rows) != len(CANONICAL_RTPC_IDS):
        return [], source, "static GameParameter evidence must contain exactly six entries"

    valid: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    seen_ids: set[int] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            return [], source, f"malformed static GameParameter entry {index}: expected mapping"
        field = raw.get("metadataField")
        if not isinstance(field, str) or not field.strip():
            return [], source, f"malformed static GameParameter entry {index}: metadataField missing"
        parameter_name = field.rsplit(".", 1)[-1].strip()
        expected_id = CANONICAL_RTPC_IDS.get(parameter_name)
        if expected_id is None:
            return [], source, f"unknown static GameParameter name: {parameter_name[:80]}"
        if field.strip() != CANONICAL_METADATA_PREFIX + parameter_name:
            return [], source, f"static GameParameter {parameter_name} metadataField mismatch"
        if parameter_name in seen_names:
            return [], source, f"duplicate static GameParameter name: {parameter_name}"
        seen_names.add(parameter_name)

        parameter_id = raw.get("parameterId")
        if isinstance(parameter_id, bool) or not isinstance(parameter_id, int):
            return [], source, f"static GameParameter {parameter_name} parameterId is not an int"
        raw_parameter_id = parameter_id
        parameter_id &= 0xFFFFFFFF
        parameter_id_hex = raw.get("parameterIdHex")
        expected_hex = CANONICAL_RTPC_HEX[parameter_name]
        if not isinstance(parameter_id_hex, str):
            return [], source, f"static GameParameter {parameter_name} parameterIdHex is missing"
        if parameter_id_hex.casefold() != expected_hex:
            return [], source, f"static GameParameter {parameter_name} parameterIdHex mismatch"
        if raw_parameter_id != expected_id or parameter_id != expected_id:
            return [], source, f"static GameParameter {parameter_name} parameterId mismatch"
        if _u32(parameter_id_hex) != parameter_id:
            return [], source, f"static GameParameter {parameter_name} parameterId/hex disagree"
        if parameter_id in seen_ids:
            return [], source, f"duplicate static GameParameter ID: {expected_hex}"
        seen_ids.add(parameter_id)
        if raw.get("serializedHircMatch") is not True:
            return [], source, f"static GameParameter {parameter_name} lacks serialized HIRC match"
        valid.append({
            "parameterId": parameter_id,
            "parameterIdHex": expected_hex,
            "rtpcId": parameter_id,
            "rtpcIdHex": expected_hex,
            "metadataField": field.strip(),
            "parameterName": parameter_name,
            "nodeRtpcCurveCount": _count(raw.get("nodeRtpcCurveCount")),
            "busRtpcCurveCount": _count(raw.get("busRtpcCurveCount")),
            "serializedHircMatch": True,
        })
    if seen_names != set(CANONICAL_RTPC_IDS):
        return [], source, "static GameParameter evidence does not cover the canonical six names"
    if seen_ids != set(CANONICAL_RTPC_IDS.values()):
        return [], source, "static GameParameter evidence does not cover the canonical six IDs"
    valid.sort(key=lambda row: int(row["parameterId"]))
    return valid, source, ""


def _compact_curve(
    curve: Mapping[str, Any],
    *,
    source: str,
    event_id: str = "",
    bank_id: Any = None,
    bus_id_hex: str = "",
    rtpc_id: int | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source": source,
        "eventId": event_id or None,
        "bankId": bank_id,
        "busIdHex": bus_id_hex or None,
        "rtpcId": rtpc_id,
        "rtpcIdHex": _hex(rtpc_id),
        "parameterId": curve.get("parameterId"),
        "parameterLabel": curve.get("parameterLabel"),
        "rtpcTypeLabel": curve.get("rtpcTypeLabel"),
        "accumLabel": curve.get("accumLabel"),
        "scalingLabel": curve.get("scalingLabel"),
        "pointCount": curve.get("pointCount"),
        "evidenceClass": "authoredStatic",
    }
    return {
        key: value for key, value in row.items()
        if value not in (None, "", [])
    }


def _empty_row(base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "evidenceClass": "authoredStatic",
        "alignmentStatus": "exactStaticMetadataFieldAndHircRtpcId",
        "serializedCurveCount": int(base.get("nodeRtpcCurveCount") or 0)
        + int(base.get("busRtpcCurveCount") or 0),
        "eventNodeCurveCount": 0,
        "eventNodePointCount": 0,
        "busDefinitionCurveCount": 0,
        "busDefinitionPointCount": 0,
        "mediaBusControlRowCount": 0,
        "controlledProperties": Counter(),
        "eventIds": set(),
        "controlRows": [],
        "curveEvidence": [],
        "setGameParameterCount": 0,
        "resetGameParameterCount": 0,
        "runtimeValueStatus": "unobserved",
        "targetObjectStatus": "unresolved",
        "selectedBranchStatus": "unobserved",
        "dspAudibilityStatus": "unobserved",
    }


def _post_summary(
    event: Mapping[str, Any],
    result: dict[str, Any],
) -> Iterable[Mapping[str, Any]]:
    evidence_rows = event.get("evidence")
    if evidence_rows is None:
        return
    if not isinstance(evidence_rows, list):
        _record_diagnostic(result, "malformed event.evidence: expected list")
        return
    for evidence in evidence_rows:
        if not isinstance(evidence, Mapping):
            _record_diagnostic(result, "malformed event.evidence row: expected mapping")
            continue
        if "postProcessSummary" not in evidence:
            yield evidence
            continue
        post = evidence.get("postProcessSummary")
        if not isinstance(post, Mapping):
            _record_diagnostic(
                result,
                "malformed event evidence postProcessSummary: expected mapping",
            )
            continue
        yield evidence


def build_static_rtpc_alignment(
    audio_index: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]] = (),
    media: Iterable[Mapping[str, Any]] = (),
    *,
    native_context: Any,
    static_entries: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Join gated static names to serialized RTPC and Action evidence."""

    gate = _native_gate(native_context)
    result: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "nativeGate": {
            "gateId": NATIVE_GATE_ID,
            **gate,
            "selectedInputs": ["global-metadata.dat", "GameAssembly.dll"],
        },
        "status": gate["status"],
        "source": "hircSummary.gameParameterNameEvidence",
        "evidenceClass": "authoredStatic",
        "runtimeObservationStatus": "unobserved",
        "entries": [],
        "diagnostics": [],
        "diagnosticCount": 0,
        "counts": {
            "staticParameterCount": 0,
            "serializedHircMatchedParameterCount": 0,
            "serializedNodeRtpcCurveCount": 0,
            "serializedBusRtpcCurveCount": 0,
            "eventNodeCurveEvidenceCount": 0,
            "eventNodePointEvidenceCount": 0,
            "busDefinitionCurveEvidenceCount": 0,
            "busDefinitionPointEvidenceCount": 0,
            "mediaBusControlRowCount": 0,
            "setGameParameterControlCount": 0,
            "resetGameParameterControlCount": 0,
        },
        "evidenceBoundary": EVIDENCE_BOUNDARY,
    }
    if gate["status"] != "validated":
        result["evidenceBoundary"] = (
            EVIDENCE_BOUNDARY + " Native/static names are withheld because the "
            "explicit selected native-input gate is unavailable or mismatched."
        )
        return result

    bases, source, diagnostic = _static_entries(
        audio_index,
        static_entries,
        str(gate.get("metadataSha256") or ""),
    )
    if diagnostic:
        # A stale/malformed catalog is a publication failure, not a partial
        # result.  In particular, callers must not retain old HIRC names when
        # this branch is reached.
        result["status"] = (
            "mismatched"
            if "metadataSha256 mismatches selected metadata" in diagnostic
            else "malformed"
        )
        result["nativeGate"]["status"] = result["status"]
        result["nativeGate"]["reason"] = diagnostic
        result["evidenceBoundary"] = (
            EVIDENCE_BOUNDARY + " Static names are withheld because the "
            "serialized six-name contract is missing, malformed, or stale."
        )
        return result
    result["source"] = source
    by_id = {
        int(base["parameterId"]): _empty_row(base)
        for base in bases
    }
    event_rows = _list_or_none(events, result, label="events", allow_tuple=True)
    media_rows = _list_or_none(media, result, label="media", allow_tuple=True)
    events: list[Mapping[str, Any]] = []
    for event in event_rows or ():
        if not isinstance(event, Mapping):
            _record_diagnostic(result, "malformed event row: expected mapping")
            continue
        events.append(event)
    media: list[Mapping[str, Any]] = []
    for row in media_rows or ():
        if not isinstance(row, Mapping):
            _record_diagnostic(result, "malformed media row: expected mapping")
            continue
        media.append(row)

    def target(raw_id: Any) -> dict[str, Any] | None:
        parameter_id = _strict_u32(raw_id)
        return by_id.get(parameter_id) if parameter_id is not None else None

    for event in events:
        event_id = str(event.get("id") or event.get("eventId") or "").strip()
        for evidence in _post_summary(event, result):
            post = evidence.get("postProcessSummary") or {}
            rtpc_summary_rows = _list_or_none(
                post.get("rtpcIds"),
                result,
                label="event postProcessSummary.rtpcIds",
            )
            rtpc_summaries_by_id: dict[int, tuple[Mapping[str, Any], int]] = {}
            for curve_summary in rtpc_summary_rows or ():
                if not isinstance(curve_summary, Mapping):
                    _record_diagnostic(
                        result,
                        "malformed event postProcessSummary.rtpcIds row: expected mapping",
                    )
                    continue
                rtpc_id, diagnostic = _paired_u32(
                    curve_summary,
                    "rtpcId",
                    "rtpcIdHex",
                    label="event RTPC summary",
                )
                if diagnostic:
                    _record_diagnostic(result, diagnostic)
                    continue
                if rtpc_id is not None:
                    rtpc_summaries_by_id[rtpc_id] = (curve_summary, rtpc_id)
            try:
                bank_id = int(evidence.get("bankId"))
            except (TypeError, ValueError):
                bank_id = None
            state_nodes = _list_or_none(
                post.get("stateRtpcNodes"),
                result,
                label="event postProcessSummary.stateRtpcNodes",
            )
            for node in state_nodes or ():
                if not isinstance(node, Mapping):
                    _record_diagnostic(
                        result,
                        "malformed event stateRtpcNodes row: expected mapping",
                    )
                    continue
                node_curves = _list_or_none(
                    node.get("rtpcCurves"),
                    result,
                    label="event stateRtpcNodes.rtpcCurves",
                )
                for curve in node_curves or ():
                    if not isinstance(curve, Mapping):
                        _record_diagnostic(
                            result,
                            "malformed event stateRtpcNodes curve: expected mapping",
                        )
                        continue
                    points = _list_or_none(
                        curve.get("points"),
                        result,
                        label="event RTPC curve points",
                    )
                    if points is None:
                        continue
                    rtpc_id, diagnostic = _paired_u32(
                        curve,
                        "rtpcId",
                        "rtpcIdHex",
                        label="event RTPC curve",
                    )
                    if diagnostic:
                        _record_diagnostic(result, diagnostic)
                        continue
                    row = target(rtpc_id)
                    if row is None:
                        continue
                    row["eventNodeCurveCount"] += 1
                    row["eventNodePointCount"] += max(
                        0,
                        _count(curve.get("pointCount") or len(points)),
                    )
                    label = str(curve.get("parameterLabel") or "").strip()
                    if label:
                        row["controlledProperties"][label] += 1
                    if event_id:
                        row["eventIds"].add(event_id)
                    if len(row["curveEvidence"]) < MAX_CURVE_EVIDENCE:
                        row["curveEvidence"].append(_compact_curve(
                            curve,
                            source="eventNodeInitialRtpc",
                            event_id=event_id,
                            bank_id=bank_id,
                            rtpc_id=rtpc_id,
                        ))

            # The compact rtpcIds rows are exact per-evidence curve summaries;
            # use them only as event placement evidence, not as a second curve
            # count (the HIRC totals above remain authoritative).
            for curve_summary in rtpc_summary_rows or ():
                if not isinstance(curve_summary, Mapping):
                    continue
                rtpc_id, diagnostic = _paired_u32(
                    curve_summary,
                    "rtpcId",
                    "rtpcIdHex",
                    label="event RTPC summary",
                )
                if diagnostic:
                    continue
                row = target(rtpc_id)
                if row is not None and event_id:
                    row["eventIds"].add(event_id)

            action_rows = _list_or_none(
                evidence.get("actionEvidence"),
                result,
                label="event actionEvidence",
            )
            for action in action_rows or ():
                if not isinstance(action, Mapping):
                    _record_diagnostic(
                        result,
                        "malformed event actionEvidence row: expected mapping",
                    )
                    continue
                operation = str(action.get("operation") or "")
                if operation not in {"setGameParameter", "resetGameParameter"}:
                    continue
                action_id, diagnostic = _paired_u32(
                    action,
                    "idExt",
                    "idExtHex",
                    label="GameParameter action",
                )
                if diagnostic:
                    _record_diagnostic(result, diagnostic)
                    continue
                row = target(action_id)
                if row is None:
                    continue
                if operation == "setGameParameter":
                    row["setGameParameterCount"] += 1
                else:
                    row["resetGameParameterCount"] += 1
                if event_id:
                    row["eventIds"].add(event_id)
                if len(row["controlRows"]) >= MAX_CONTROL_ROWS:
                    continue
                control: dict[str, Any] = {
                    "eventId": event_id or None,
                    "bankId": bank_id,
                    "actionId": action.get("actionId"),
                    "operation": operation,
                    "parameterId": action_id,
                    "parameterIdHex": _hex(action_id),
                    "rtpcId": action_id,
                    "rtpcIdHex": _hex(action_id),
                    "actionControlParserStatus": action.get("actionControlParserStatus"),
                    "evidenceClass": "authoredStatic",
                    "runtimeValueStatus": "unobserved",
                }
                joined_rtpc = rtpc_summaries_by_id.get(action_id)
                if joined_rtpc is not None:
                    joined_summary, joined_id = joined_rtpc
                    control["initialRtpcJoin"] = {
                        "rtpcId": joined_id,
                        "rtpcIdHex": _hex(joined_id),
                        "curveCount": _count(joined_summary.get("curveCount")),
                        "joinStatus": "sameEventSerializedInitialRtpcId",
                        "evidenceClass": "authoredStatic",
                    }
                if isinstance(action.get("valueRange"), Mapping):
                    control["authoredValueRange"] = dict(action["valueRange"])
                elif action.get("valueRange") is not None:
                    _record_diagnostic(
                        result,
                        "malformed GameParameter action valueRange: expected mapping",
                    )
                row["controlRows"].append({
                    key: value for key, value in control.items()
                    if value not in (None, "", [])
                })

    # Bus definitions are part of the exact HIRC summary and carry the full
    # curve/property labels even when no Event leaf reaches that bus.
    post_summary = (audio_index.get("hircSummary") or {}).get("postProcessSummary") or {}
    bus_definitions = _list_or_none(
        post_summary.get("busDefinitions"),
        result,
        label="hircSummary.postProcessSummary.busDefinitions",
    )
    for bus in bus_definitions or ():
        if not isinstance(bus, Mapping):
            _record_diagnostic(result, "malformed busDefinitions row: expected mapping")
            continue
        bus_id, diagnostic = _paired_u32(
            bus,
            "busId",
            "busIdHex",
            label="bus definition",
        )
        if diagnostic:
            _record_diagnostic(result, diagnostic)
            continue
        bus_id_hex = _hex(bus_id)
        state = bus.get("serializedStateAndRtpc")
        if state is None and "serializedStateAndRtpc" not in bus:
            state = {}
        if not isinstance(state, Mapping):
            _record_diagnostic(
                result,
                "malformed bus serializedStateAndRtpc: expected mapping",
            )
            continue
        bus_curves = _list_or_none(
            state.get("rtpcCurves"),
            result,
            label="bus serializedStateAndRtpc.rtpcCurves",
        )
        for curve in bus_curves or ():
            if not isinstance(curve, Mapping):
                _record_diagnostic(result, "malformed bus rtpcCurves row: expected mapping")
                continue
            points = _list_or_none(
                curve.get("points"),
                result,
                label="bus RTPC curve points",
            )
            if points is None:
                continue
            rtpc_id, diagnostic = _paired_u32(
                curve,
                "rtpcId",
                "rtpcIdHex",
                label="bus RTPC curve",
            )
            if diagnostic:
                _record_diagnostic(result, diagnostic)
                continue
            row = target(rtpc_id)
            if row is None:
                continue
            row["busDefinitionCurveCount"] += 1
            row["busDefinitionPointCount"] += _count(
                curve.get("pointCount") or len(points)
            )
            label = str(curve.get("parameterLabel") or "").strip()
            if label:
                row["controlledProperties"][label] += 1
            if len(row["curveEvidence"]) < MAX_CURVE_EVIDENCE:
                row["curveEvidence"].append(_compact_curve(
                    curve,
                    source="busInitialRtpc",
                    bus_id_hex=bus_id_hex,
                    rtpc_id=rtpc_id,
                ))

    for media_row in media:
        event_id_values = _list_or_none(
            media_row.get("eventIds"),
            result,
            label="media eventIds",
        )
        event_ids = [
            str(value) for value in event_id_values or () if str(value)
        ]
        control_rows = _list_or_none(
            media_row.get("postProcessBusControls"),
            result,
            label="media postProcessBusControls",
        )
        for control_row in control_rows or ():
            if not isinstance(control_row, Mapping):
                _record_diagnostic(
                    result,
                    "malformed media postProcessBusControls row: expected mapping",
                )
                continue
            raw_rtpc_ids = _list_or_none(
                control_row.get("rtpcIds"),
                result,
                label="media postProcessBusControls.rtpcIds",
            )
            for raw_id in raw_rtpc_ids or ():
                row = target(raw_id)
                if row is None:
                    continue
                row["mediaBusControlRowCount"] += 1
                row["eventIds"].update(event_ids)

    output_entries: list[dict[str, Any]] = []
    for parameter_id in sorted(by_id):
        row = by_id[parameter_id]
        serialized_hirc_match = bool(
            row.get("serializedHircMatch")
            or row.get("serializedCurveCount")
            or row.get("busDefinitionCurveCount")
        )
        row["serializedHircMatch"] = serialized_hirc_match
        row["alignmentStatus"] = (
            "exactStaticMetadataFieldAndHircRtpcId"
            if serialized_hirc_match
            else "staticMetadataIdWithoutSerializedHircMatch"
        )
        event_ids = sorted(row["eventIds"])
        row["eventIds"] = event_ids[:MAX_EVENT_IDS]
        row["eventIdsTruncated"] = len(event_ids) > MAX_EVENT_IDS
        row["controlledProperties"] = dict(sorted(row["controlledProperties"].items()))
        curve_evidence = row["curveEvidence"]
        row["curveEvidence"] = curve_evidence[:MAX_CURVE_EVIDENCE]
        row["curveEvidenceTruncated"] = len(curve_evidence) > MAX_CURVE_EVIDENCE
        control_rows = row["controlRows"]
        row["controlRowsTruncated"] = len(control_rows) > MAX_CONTROL_ROWS
        row["controlRows"] = control_rows[:MAX_CONTROL_ROWS]
        output_entries.append(row)

    result["entries"] = output_entries
    result["counts"] = {
        "staticParameterCount": len(output_entries),
        "serializedHircMatchedParameterCount": sum(
            bool(row["serializedHircMatch"]) for row in output_entries
        ),
        "serializedNodeRtpcCurveCount": sum(
            int(row["nodeRtpcCurveCount"]) for row in output_entries
        ),
        "serializedBusRtpcCurveCount": sum(
            int(row["busRtpcCurveCount"]) for row in output_entries
        ),
        "eventNodeCurveEvidenceCount": sum(
            int(row["eventNodeCurveCount"]) for row in output_entries
        ),
        "eventNodePointEvidenceCount": sum(
            int(row["eventNodePointCount"]) for row in output_entries
        ),
        "busDefinitionCurveEvidenceCount": sum(
            int(row["busDefinitionCurveCount"]) for row in output_entries
        ),
        "busDefinitionPointEvidenceCount": sum(
            int(row["busDefinitionPointCount"]) for row in output_entries
        ),
        "mediaBusControlRowCount": sum(
            int(row["mediaBusControlRowCount"]) for row in output_entries
        ),
        "setGameParameterControlCount": sum(
            int(row["setGameParameterCount"]) for row in output_entries
        ),
        "resetGameParameterControlCount": sum(
            int(row["resetGameParameterCount"]) for row in output_entries
        ),
    }
    return result


__all__ = [
    "EVIDENCE_BOUNDARY",
    "NATIVE_GATE_ID",
    "SCHEMA_VERSION",
    "build_static_rtpc_alignment",
]
