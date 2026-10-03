"""Audit bounded source entry/result observations against the selected native build.

This reads JSONL and authenticated files only; it never attaches to a process or
reads pointers. A valid pair proves the recorded fixed fields, not media-key
ownership, successful registry lookup, file/codec identity or audible playback.
All admitted pairs contribute to bounded caller/kind summaries; LockDataPtr
representatives group only the observed entry flags word's bit-eight state.
Declared consumer pairs have their own sample budget, retaining parent IDs
even when startup source traffic fills the generic sample list.
Selected consumer fields also support bounded checks of synchronous native
parent intervals and matching owner/source/output snapshots.
Every summary is withheld with the original samples if any audit check fails.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

if __name__ == "__main__" and not __package__:
    raise SystemExit("run as: python -m scripts.webui.story_recovery.audit_audio_source_capture")

from scripts.game_data.il2cpp.native_image import pe_mapped_image_size
from scripts.game_data.wwise_source_native import CONTRACT_PATH, load_validated_source_contract
from scripts.repo_paths import REPO_ROOT
from scripts.webui.story_recovery import prepare_audio_source_observer as observer
from scripts.webui.story_recovery import runtime_trace_audio_capture as capture
from scripts.webui.story_recovery import runtime_trace_audio_import as importer
from scripts.webui.story_recovery import runtime_trace_core as core

SCHEMA = "endfield.audio-source-capture-audit.v1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 256 * 1024
MAX_EVENTS = 100000
MAX_DIAGNOSTICS = 64
MAX_PAIR_SAMPLES = 64
MAX_CALLER_COUNTS = 32
MAX_LOCK_STATE_SAMPLES = 4
MAX_CONSUMER_PAIR_SAMPLES = 4
DEFAULT_OUTPUT = REPO_ROOT / "reports/audio/source_observer_capture_audit.json"
POINTER = re.compile(r"0x[0-9a-fA-F]{1,16}\Z")


def _scalar(value: Any, kind: str, *, nonzero: bool = False) -> bool:
    if kind == "u32":
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0xffffffff
    if kind == "pointer":
        return (isinstance(value, str) and POINTER.fullmatch(value) is not None
                and 0 <= int(value, 16) < 0x800000000000 and (not nonzero or int(value, 16) > 0))
    if kind in ("utf16", "utf16Direct"):
        return (isinstance(value, str) and "\x00" not in value
                and len(value.encode("utf-16-le", errors="surrogatepass")) // 2 < 4096)
    return False


def _positive_budget(value: int, name: str) -> int:
    if type(value) is not int or not 0 < value < sys.maxsize:
        raise ValueError(f"{name} must be a positive integer below {sys.maxsize}")
    return value


def read_bounded_snapshot(path: Path, *, max_input_bytes: int | None = None) -> bytes:
    limit = _positive_budget(MAX_INPUT_BYTES if max_input_bytes is None else max_input_bytes, "max_input_bytes")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"{path.name}: input exceeds {limit} bytes")
    return raw


def read_bounded_rows(raw: bytes, path: Path, *, max_events: int | None = None) -> Iterable[dict[str, Any]]:
    limit = _positive_budget(MAX_EVENTS if max_events is None else max_events, "max_events")
    with io.BytesIO(raw) as stream:
        count = 0
        number = 0
        while line := stream.readline(MAX_LINE_BYTES + 1):
            number += 1
            if len(line) > MAX_LINE_BYTES:
                raise ValueError(f"{path.name}:{number}: trace row exceeds {MAX_LINE_BYTES} bytes")
            if not line.strip():
                continue
            count += 1
            if count > limit:
                raise ValueError(f"trace exceeds {limit} events")
            row = json.loads(line.decode("utf-8"))
            if not isinstance(row, dict):
                raise ValueError(f"{path.name}:{number}: expected object")
            yield row


def read_bounded_events(
    path: Path, raw: bytes | None = None, *, max_input_bytes: int | None = None,
    max_events: int | None = None,
) -> Iterable[dict[str, Any]]:
    byte_limit = _positive_budget(MAX_INPUT_BYTES if max_input_bytes is None else max_input_bytes, "max_input_bytes")
    snapshot = read_bounded_snapshot(path, max_input_bytes=byte_limit) if raw is None else raw
    if len(snapshot) > byte_limit:
        raise ValueError(f"{path.name}: input exceeds {byte_limit} bytes")
    for number, row in enumerate(read_bounded_rows(snapshot, path, max_events=max_events), 1):
        yield importer.normalize_event(row, f"{path.name}:{number}")


def _consumer_relation_layout(consumer: dict[str, Any], lock: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any] | None:
    """Use only field roles and offsets declared by the authenticated profile."""
    if not isinstance(boundary, dict) or not all(isinstance(boundary.get(key), str) and boundary[key] for key in ("exact", "direct")):
        return None
    owner = consumer["args"].get("anonymousCallerOwnerPointer", {})
    source = lock["args"].get("sourceThisPointer", {})
    output = lock["args"].get("mediaRefOutputPointer", {})
    if any(row.get("kind") != "pointer" or type(row.get("index")) is not int for row in (owner, source, output)):
        return None
    parent_fields = {row["name"]: row for row in consumer["memory"]}
    child_fields = {row["name"]: row for row in lock["memory"]}
    names = ("mediaRefEntryPointer", "mediaRefAuxPointer", "mediaRefDataPointer", "mediaRefByteCount")
    source_field = parent_fields.get("sourceThisPointer", {})
    if source_field.get("kind") != "pointer" or source_field.get("argIndex") != owner["index"]:
        return None
    offsets = []
    for name in names:
        parent, child = parent_fields.get(name, {}), child_fields.get(name, {})
        if (parent.get("kind") != child.get("kind") or parent.get("kind") not in ("pointer", "u32")
                or parent.get("argIndex") != owner["index"] or child.get("argIndex") != output["index"]
                or any(type(row.get("offset")) is not int or row["offset"] < 0 for row in (parent, child))):
            return None
        offsets.append(parent["offset"] - child["offset"])
    if (len(set(offsets)) != 1 or offsets[0] < 0 or type(source_field.get("offset")) is not int
            or source_field["offset"] < 0):
        return None
    return {"ownerArgument": "anonymousCallerOwnerPointer", "sourceField": "sourceThisPointer",
            "sourceOwnerOffset": source_field["offset"], "outputOwnerOffset": offsets[0], "outputFields": names,
            "fieldKinds": {name: parent_fields[name]["kind"] for name in names}}


def _audit_consumer_relations(admitted: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]],
        hooks: dict[str, dict[str, Any]], profile: dict[str, Any], issue: Any,
        recorded: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    """Check recorded synchronous intervals; unknown parents remain unresolved."""
    boundaries = profile.get("sourceConsumerEvidenceBoundary", {})
    interval_pairs = dict(admitted)
    for key, pair in recorded.items():
        if key in interval_pairs or pair["duplicate"] or len(pair["calls"]) != 1 or len(pair["results"]) != 1:
            continue
        call, result = pair["calls"][0], pair["results"][0]
        thread = call.get("threadId")
        valid_thread = (type(thread) in (int, str) and str(thread).isdigit() and len(str(thread)) <= 10
                        and 0 < int(thread) <= 0xffffffff)
        if (valid_thread and thread == result.get("threadId") and call["seq"] < result["seq"]
                and isinstance(call.get("sourceKind"), str) and call.get("sourceKind") == result.get("sourceKind")):
            interval_pairs[key] = (call, result)
    intervals = sorted((event["seq"], phase, key, event) for key, pair in interval_pairs.items()
                       for phase, event in enumerate(pair))
    stacks: dict[tuple[str, Any], list[str]] = {}
    active_parents = {}
    for _seq, phase, key, event in intervals:
        stack = stacks.setdefault((key[0], event["threadId"]), [])
        if phase == 0:
            active_parents[key] = stack[-1] if stack else None
            stack.append(key[1])
        elif key[1] in stack:
            stack.remove(key[1])
    totals, unresolved = Counter(), Counter()
    grouped: dict[str, dict[str, Any]] = {}
    for key, (call, result) in admitted.items():
        if call["sourceKind"] != "sourceLockDataPtr":
            continue
        totals["lockPairs"] += 1
        parent_id = call.get("nativeParentCaptureId")
        if parent_id is None:
            unresolved["noRecordedParent"] += 1
            continue
        parent = interval_pairs.get((key[0], parent_id))
        if parent is None:
            issue("consumerParentMissing", call, expected="admitted native parent pair in this session", actual=parent_id)
            continue
        before, after = parent
        if (before["threadId"] != call["threadId"] or after["threadId"] != call["threadId"]
                or not before["seq"] < call["seq"] < result["seq"] < after["seq"]
                or active_parents.get(key) != parent_id):
            issue("consumerParentInterval", call, expected="same-thread immediate active recorded parent",
                  actual={"parentId": parent_id, "activeParentId": active_parents.get(key),
                          "parentThread": before["threadId"], "childThread": call["threadId"],
                          "sequence": [before["seq"], call["seq"], result["seq"], after["seq"]]})
            continue
        times = [row.get("monotonicMs") for row in (before, call, result, after)]
        if (any(type(value) not in (int, float) or not 0 <= value < sys.float_info.max for value in times)
                or times != sorted(times)):
            issue("consumerParentTime", call, expected="finite nondecreasing parent/child interval", actual=times)
            continue
        kind = before["sourceKind"]
        if kind not in boundaries or (key[0], parent_id) not in admitted:
            unresolved["undeclaredConsumerKind"] += 1
            continue
        layout = _consumer_relation_layout(hooks[kind], hooks[call["sourceKind"]], boundaries[kind])
        if layout is None:
            unresolved["undeclaredRelationFields"] += 1
            continue
        owner = before["decodedArguments"][layout["ownerArgument"]]
        child_source = call["decodedArguments"]["sourceThisPointer"]
        child_output = call["decodedArguments"]["mediaRefOutputPointer"]
        expected_output = int(owner, 16) + layout["outputOwnerOffset"]
        checks = {"outputAddress": expected_output < 0x800000000000 and expected_output == int(child_output, 16)}
        for phase, parent_values, child_values, child_args in (
                ("entry", before["memory"], call["memory"], call["decodedArguments"]),
                ("result", after["memoryAfter"], result["memoryAfter"], result["decodedArgumentsAfter"])):
            checks[phase + ".sourcePointer"] = int(parent_values[layout["sourceField"]], 16) == int(child_args["sourceThisPointer"], 16)
            for name in layout["outputFields"]:
                a, b = parent_values[name], child_values[name]
                checks[phase + "." + name] = int(a, 16) == int(b, 16) if layout["fieldKinds"][name] == "pointer" else a == b
        failed = [name for name, valid in checks.items() if not valid]
        if failed:
            issue("consumerOwnerFields", call, expected="declared owner/source/output relation and matching snapshots",
                  actual={"failedFields": failed, "ownerPointer": owner, "sourcePointer": child_source,
                          "outputPointer": child_output, "outputOwnerOffset": layout["outputOwnerOffset"]})
            continue
        totals["nestedPairs"] += 1
        flags = call["memory"].get("sourceFlagsWord")
        declared = any(row["name"] == "sourceFlagsWord" and row["kind"] == "u32" for row in hooks[call["sourceKind"]]["memory"])
        state = ("set" if flags & (1 << 8) else "clear") if declared and _scalar(flags, "u32") else "unavailable"
        entry = grouped.setdefault(kind, {"sourceKind": kind, "pairCount": 0,
            "stateCounts": {name: 0 for name in ("clear", "set", "unavailable")},
            "samples": {name: [] for name in ("clear", "set", "unavailable")}})
        entry["pairCount"] += 1
        entry["stateCounts"][state] += 1
        if len(entry["samples"][state]) < MAX_CONSUMER_PAIR_SAMPLES:
            entry["samples"][state].append({"sessionId": key[0], "consumerCaptureId": parent_id,
                "lockCaptureId": key[1], "threadId": call["threadId"],
                "sequence": [before["seq"], call["seq"], result["seq"], after["seq"]], "monotonicMs": times,
                "anonymousOwnerPointer": owner, "sourcePointer": child_source, "outputPointer": child_output,
                "sourceOwnerOffset": layout["sourceOwnerOffset"], "outputOwnerOffset": layout["outputOwnerOffset"],
                "outputBefore": {name: call["memory"][name] for name in layout["outputFields"]},
                "outputAfter": {name: result["memoryAfter"][name] for name in layout["outputFields"]}})
    for entry in grouped.values():
        entry["samplesTruncated"] = {state: count > len(entry["samples"][state]) for state, count in entry["stateCounts"].items()}
    return {"lockPairCount": totals["lockPairs"], "nestedPairCount": totals["nestedPairs"],
            "unresolvedPairCount": sum(unresolved.values()), "unresolvedReasons": dict(sorted(unresolved.items())),
            "perStateSampleLimit": MAX_CONSUMER_PAIR_SAMPLES, "rows": [grouped[kind] for kind in sorted(grouped)],
            "evidenceBoundary": "Same-thread recorded native parent interval and selected profile's fixed owner/source/output fields only. No asynchronous managed path, source lifetime, successful lookup, decoded content or audibility is established."}


def audit_events(
    events: Iterable[dict[str, Any]], profile: dict[str, Any], module_expectations: dict[str, dict[str, Any]],
    diagnostic_events: Iterable[dict[str, Any]] | None = None, *, max_events: int | None = None,
    bridge_declaration: dict[str, Any] | None = None,
    owner_carrier_declaration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure bounded audit; callers authenticate profile and selected file facts."""
    event_limit = _positive_budget(MAX_EVENTS if max_events is None else max_events, "max_events")
    hooks = {row["sourceKind"]: row for row in profile["nativeHooks"]}
    hook_names = {row["name"] for row in hooks.values()}
    sessions: dict[str, dict[str, Any]] = {}
    native: dict[tuple[str, str], dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    diagnostics: list[dict[str, Any]] = []
    diagnostic_count = 0

    def issue(code: str, event: dict[str, Any] | None = None, **detail: Any) -> None:
        nonlocal diagnostic_count
        diagnostic_count += 1
        if len(diagnostics) < MAX_DIAGNOSTICS:
            diagnostics.append({"check": code, **({"sessionId": event.get("sessionId"), "seq": event.get("seq"),
                                "nativeCaptureId": event.get("nativeCaptureId")} if event else {}), **detail})

    event_count = 0
    for event in events:
        event_count += 1
        if event_count > event_limit:
            issue("eventLimit", maximum=event_limit)
            break
        session_id, kind, seq = event["sessionId"], event["kind"], event["seq"]
        counts[kind] += 1
        session = sessions.setdefault(session_id, {"start": None, "end": None, "lastSeq": -1, "count": 0})
        if seq != session["lastSeq"] + 1:
            issue("sequenceGap", event, expected=session["lastSeq"] + 1, actual=seq)
        session["lastSeq"] = seq
        session["count"] += 1
        if session["end"] is not None:
            issue("eventAfterSessionEnd", event)
        if kind == "session_start":
            if session["start"] is not None:
                issue("duplicateSessionStart", event)
            session["start"] = event
            for key, expected in (("gameBuild", profile["gameBuild"]),
                                  ("exportFingerprint", profile["files"]["metadata"]["sha256"])):
                if event.get(key) != expected:
                    issue("sessionIdentity", event, field=key, expected=expected, actual=event.get(key))
        elif session["start"] is None:
            issue("missingSessionStart", event)
        if kind not in {"session_start", "session_end"} and event.get("agentEventSeq") != seq - 1:
            issue("agentSequenceGap", event, expected=seq - 1, actual=event.get("agentEventSeq"))
        if kind == "session_end":
            if session["end"] is not None:
                issue("duplicateSessionEnd", event)
            session["end"] = event
            receipt_counts = ("droppedEventCount", "activeNativeCallCount", "activeManagedCallCount",
                              "agentDiagnosticCount", "deliveredAgentDiagnosticCount", "agentEventCount")
            valid_counts = all(type(event.get(key)) is int and event[key] >= 0 for key in receipt_counts)
            if (not valid_counts or event.get("captureComplete") is not True or event.get("droppedEventCount") != 0
                    or event.get("activeNativeCallCount") != 0 or event.get("activeManagedCallCount") != 0
                    or event.get("agentDiagnosticCount") != 0
                    or event.get("agentDiagnosticCount") != event.get("deliveredAgentDiagnosticCount")
                    or event.get("agentEventCount") != session["count"] - 2):
                issue("incompleteCapture", event, captureComplete=event.get("captureComplete"),
                      droppedEventCount=event.get("droppedEventCount"), activeNativeCallCount=event.get("activeNativeCallCount"),
                      activeManagedCallCount=event.get("activeManagedCallCount"),
                      agentEventCount=event.get("agentEventCount"), recordedAgentEventCount=session["count"] - 2,
                      invalidReceiptCounts={key: event.get(key) for key in receipt_counts
                                            if type(event.get(key)) is not int or event[key] < 0})
            # Saved recordings predate cooperative draining. When a recording
            # declares the new receipt, require its complete responsive-agent
            # protocol rather than trusting captureComplete alone.
            if ("captureStopProtocol" in event or "captureDrained" in event) and (
                    event.get("captureStopProtocol") != "drain-v1" or event.get("captureDrained") is not True):
                issue("captureDrainReceipt", event, expectedProtocol="drain-v1", expectedDrained=True,
                      actualProtocol=event.get("captureStopProtocol"), actualDrained=event.get("captureDrained"))
        source = event.get("sourceKind") in hooks or event.get("hookName") in hook_names
        if source and kind not in {"audio_native_call", "audio_native_result"}:
            issue("sourceEventKind", event, actual=kind)
        if kind not in {"audio_native_call", "audio_native_result"}:
            continue
        capture_id = event.get("nativeCaptureId")
        if not isinstance(capture_id, str) or not capture_id or len(capture_id) > 128:
            if source:
                issue("missingNativeCaptureId", event)
            continue
        pair = native.setdefault((session_id, capture_id), {"calls": [], "results": [], "source": False, "duplicate": False})
        pair["source"] |= source
        phase = "calls" if kind == "audio_native_call" else "results"
        if pair[phase]:
            pair["duplicate"] = True
        if len(pair[phase]) < 2:
            pair[phase].append(event)

    ranges: dict[str, list[dict[str, Any]]] = {}
    relation_sessions: set[str] = set()
    for session_id, session in sessions.items():
        start, end = session["start"], session["end"]
        if start is None or end is None:
            issue("unclosedSession", sessionId=session_id)
            continue
        ranges[session_id] = []
        module_diagnostics_before = diagnostic_count
        for prefix, expectation in module_expectations.items():
            native_prefix = prefix == "NativeModule"
            flag = "nativeModule" if native_prefix else "module"
            for suffix in ("PathMatch", "SizeMatch", "Sha256Match", "NameMatch"):
                if end.get(flag + suffix) is not True:
                    issue("moduleVerification", end, field=flag + suffix, actual=end.get(flag + suffix))
            for suffix, expected in (("Path", expectation["path"]), ("Size", expectation["size"]),
                                     ("FileSize", expectation["fileSize"]), ("Sha256", expectation["sha256"])):
                value = start.get("expected" + prefix + suffix)
                equal = core.normalized_path(value) == core.normalized_path(expected) if suffix == "Path" and isinstance(value, str) else value == expected
                if not equal:
                    issue("moduleHeaderIdentity", start, field="expected" + prefix + suffix, expected=expected, actual=value)
            for suffix, expected in (("Path", expectation["path"]), ("Size", expectation["size"]),
                                     ("Sha256", expectation["sha256"]), ("Name", expectation["name"])):
                value = end.get("attached" + prefix + suffix)
                equal = core.normalized_path(value) == core.normalized_path(expected) if suffix == "Path" and isinstance(value, str) else value == expected
                if not equal:
                    issue("attachedModuleIdentity", end, field="attached" + prefix + suffix, expected=expected, actual=value)
            try:
                base = capture.validated_module_base(end.get("attached" + prefix + "Base"), expectation["size"], prefix)
                ranges[session_id].append({"moduleName": expectation["name"], "base": base, "size": expectation["size"]})
            except RuntimeError as exc:
                issue("moduleBase", end, detail=str(exc))
        if len(ranges[session_id]) == 2:
            first, second = ranges[session_id]
            a, b = int(first["base"], 16), int(second["base"], 16)
            if max(a, b) < min(a + first["size"], b + second["size"]):
                issue("overlappingModuleExtents", end)
            if diagnostic_count == module_diagnostics_before:
                relation_sessions.add(session_id)

    samples: list[dict[str, Any]] = []
    source_kind_counts: Counter[str] = Counter()
    caller_counts: Counter[tuple[str, str, int]] = Counter()
    lock_states = ("clear", "set", "unavailable")
    lock_state_counts: Counter[str] = Counter({state: 0 for state in lock_states})
    lock_samples: dict[str, list[dict[str, Any]]] = {state: [] for state in lock_states}
    consumer_kinds = sorted(set(profile.get("sourceConsumerEvidenceBoundary", {})) & hooks.keys())
    consumer_samples: dict[str, list[dict[str, Any]]] = {kind: [] for kind in consumer_kinds}
    admitted: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    pair_count = 0
    for (session_id, capture_id), pair in native.items():
        before_pair_diagnostics = diagnostic_count
        context = {"sessionId": session_id, "nativeCaptureId": capture_id}
        if pair["duplicate"]:
            issue("duplicateNativeCaptureId", **context)
        if not pair["source"]:
            continue
        if len(pair["calls"]) != 1 or len(pair["results"]) != 1:
            issue("missingCallOrResult", **context, calls=len(pair["calls"]), results=len(pair["results"]))
            continue
        call, result = pair["calls"][0], pair["results"][0]
        hook = hooks.get(call.get("sourceKind"))
        if hook is None:
            issue("unexpectedSourceKind", call)
            continue
        thread = str(call.get("threadId", ""))
        if (call.get("threadId") != result.get("threadId") or not thread.isdigit() or len(thread) > 10
                or not 0 < int(thread) <= 0xffffffff):
            issue("threadMismatch", result, callThread=call.get("threadId"), resultThread=result.get("threadId"))
        if result["seq"] <= call["seq"]:
            issue("resultBeforeCall", result, callSeq=call["seq"])
        if not _scalar(call.get("nativeReturnAddress"), "pointer", nonzero=True):
            issue("invalidReturnAddress", call)
        for key in ("nativeReturnAddress", "nativeParentCaptureId"):
            if call.get(key) != result.get(key):
                issue("nativeLineageMismatch", result, field=key)
        parent_id = call.get("nativeParentCaptureId")
        if parent_id is not None and (not isinstance(parent_id, str) or not parent_id or len(parent_id) > 128):
            issue("invalidNativeParentCaptureId", call, expected="null or a bounded nonempty capture ID",
                  actualType=type(parent_id).__name__)
        for row in (call, result):
            for key, expected in (("sourceKind", hook["sourceKind"]), ("hookName", hook["name"]),
                                  ("rva", hook["rva"]), ("moduleName", profile["nativeModuleName"]),
                                  ("native", True), ("runtimeExecutionObserved", True)):
                if row.get(key) != expected:
                    issue("sourceEventIdentity", row, field=key, expected=expected, actual=row.get(key))
        before, after = call.get("decodedArguments", {}), result.get("decodedArgumentsAfter", {})
        for name, spec in hook["args"].items():
            for phase, values in (("entry", before), ("result", after)):
                nonzero = (spec["kind"] == "pointer" and name != "sourceInputDataPointer"
                           and spec.get("allowNull") is not True)
                if not _scalar(values.get(name), spec["kind"], nonzero=nonzero):
                    issue("argumentSampleFailure", call if phase == "entry" else result, phase=phase, field=name)
            if before.get(name) != after.get(name):
                issue("argumentChanged", result, field=name)
        for phase, row, values in (("entry", call, call.get("memory", {})), ("result", result, result.get("memoryAfter", {}))):
            for spec in hook["memory"]:
                argument_condition = spec.get("requireArgument")
                argument_values = before if phase == "entry" else after
                skipped = ((spec.get("samplePhase") is not None and spec["samplePhase"] != phase)
                           or (argument_condition is not None
                               and not _scalar(argument_values.get(argument_condition["name"]), "pointer", nonzero=True)))
                if skipped:
                    if spec["name"] not in values or values[spec["name"]] is not None:
                        issue("inapplicableMemorySample", row, phase=phase, field=spec["name"])
                    continue
                condition = spec.get("requireMemory")
                if condition is not None:
                    observed = values.get(condition["name"])
                    applicable = (_scalar(observed, "pointer", nonzero=True) if condition.get("nonzero") is True
                                  else type(observed) is int and observed == condition["equals"])
                    if not applicable:
                        if spec["name"] not in values or values[spec["name"]] is not None:
                            issue("inapplicableMemorySample", row, phase=phase, field=spec["name"])
                        continue
                if not _scalar(values.get(spec["name"]), spec["kind"]):
                    issue("memorySampleFailure", row, phase=phase, field=spec["name"])
        if hook.get("returnKind") == "pointer" and not _scalar(result.get("returnValue"), "pointer"):
            issue("returnSampleFailure", result, field="returnValue")
        if diagnostic_count == before_pair_diagnostics:
            admitted[(session_id, capture_id)] = (call, result)
        pair_count += 1
        source_kind = hook["sourceKind"]
        source_kind_counts[source_kind] += 1
        address = call.get("nativeReturnAddress")
        caller = None
        if _scalar(address, "pointer", nonzero=True):
            for extent in ranges.get(session_id, []):
                relative = int(address, 16) - int(extent["base"], 16)
                if 0 <= relative < extent["size"]:
                    caller = {"moduleName": extent["moduleName"], "rva": hex(relative)}
                    caller_counts[(source_kind, extent["moduleName"], relative)] += 1
                    break
        lock_state = None
        if source_kind == "sourceLockDataPtr":
            flags = call.get("memory", {}).get("sourceFlagsWord")
            declared_flags = any(spec["name"] == "sourceFlagsWord" and spec["kind"] == "u32"
                                 for spec in hook["memory"])
            lock_state = ("set" if flags & (1 << 8) else "clear") if declared_flags and _scalar(flags, "u32") else "unavailable"
            lock_state_counts[lock_state] += 1
        if len(samples) < MAX_PAIR_SAMPLES or (lock_state is not None
                and len(lock_samples[lock_state]) < MAX_LOCK_STATE_SAMPLES) or (
                source_kind in consumer_samples and len(consumer_samples[source_kind]) < MAX_CONSUMER_PAIR_SAMPLES):
            sample = {**context, "sourceKind": call["sourceKind"], "threadId": call.get("threadId"),
                      "callSeq": call["seq"], "resultSeq": result["seq"], "arguments": before,
                      "memoryBefore": call.get("memory"), "memoryAfter": result.get("memoryAfter"),
                      "nativeReturnAddress": address, "nativeParentCaptureId": parent_id, "boundedCaller": caller}
            if hook.get("returnKind") == "pointer":
                sample["returnValue"] = result["returnValue"]
            if len(samples) < MAX_PAIR_SAMPLES:
                samples.append(sample)
            if lock_state is not None and len(lock_samples[lock_state]) < MAX_LOCK_STATE_SAMPLES:
                lock_samples[lock_state].append({
                    **sample,
                    "arguments": {name: before.get(name) for name in hook["args"]},
                    "memoryBefore": {spec["name"]: call.get("memory", {}).get(spec["name"])
                                     for spec in hook["memory"]},
                    "memoryAfter": {spec["name"]: result.get("memoryAfter", {}).get(spec["name"])
                                    for spec in hook["memory"]},
                })
            if source_kind in consumer_samples and len(consumer_samples[source_kind]) < MAX_CONSUMER_PAIR_SAMPLES:
                consumer_samples[source_kind].append({
                    **sample,
                    "arguments": {name: before.get(name) for name in hook["args"]},
                    "memoryBefore": {spec["name"]: call.get("memory", {}).get(spec["name"])
                                     for spec in hook["memory"]},
                    "memoryAfter": {spec["name"]: result.get("memoryAfter", {}).get(spec["name"])
                                    for spec in hook["memory"]},
                })
    relations = _audit_consumer_relations(admitted, hooks, profile, issue, native)
    # A missing/invalid closure already fails the session. Without authenticated
    # module extents, derived caller checks would merely report null RVAs as
    # spurious callsite mismatches. Keep validating every pair's fixed fields
    # above, and only run rebased relations where their prerequisite succeeded.
    rebased_admitted = {key: pair for key, pair in admitted.items() if key[0] in relation_sessions}
    rebased_recorded = {key: pair for key, pair in native.items() if key[0] in relation_sessions}
    bridge_relations = {}
    if bridge_declaration is not None and relation_sessions:
        from scripts.webui.story_recovery.audio_source_bridge_relations import audit_bridge_relations

        bridge_relations = audit_bridge_relations(
            rebased_admitted, hooks, profile, ranges, bridge_declaration, issue, recorded=rebased_recorded,
        )
    owner_carrier_relations = {}
    if owner_carrier_declaration is not None and relation_sessions:
        from scripts.webui.story_recovery.audio_owner_carrier_relations import audit_owner_carrier_relations

        owner_carrier_relations = audit_owner_carrier_relations(
            rebased_admitted, hooks, profile, ranges, owner_carrier_declaration, issue,
        )
    if not sessions:
        issue("noSessions")
    if diagnostic_events is not None:
        seen_verified: set[str] = set()
        for diagnostic_index, row in enumerate(diagnostic_events, 1):
            if diagnostic_index > event_limit:
                issue("diagnosticEventLimit", maximum=event_limit)
                break
            session_id = row.get("sessionId")
            kind = row.get("kind")
            if (not isinstance(session_id, str) or session_id not in sessions or not isinstance(kind, str)
                    or kind not in {"attached_module_verified", "capture_cleanup_detached"}):
                issue("captureDiagnostic", sessionId=session_id, kind=row.get("kind"))
            elif row["kind"] == "attached_module_verified":
                seen_verified.add(session_id)
        for session_id in sessions.keys() - seen_verified:
            issue("missingVerificationDiagnostic", sessionId=session_id)
    if not any(row["source"] for row in native.values()):
        issue("noSourceCalls")
    source_summary: dict[str, Any] = {}
    if diagnostic_count == 0:
        ranked_callers = sorted(caller_counts.items(), key=lambda item: (-item[1], *item[0]))
        shown_callers = ranked_callers[:MAX_CALLER_COUNTS]
        authenticated_pairs = sum(caller_counts.values())
        source_summary = {
            "sourceKindCounts": dict(sorted(source_kind_counts.items())),
            "unobservedSourceKinds": sorted(set(hooks) - source_kind_counts.keys()),
            "authenticatedCallerCounts": {
                "rows": [{"sourceKind": kind, "moduleName": module, "rva": hex(rva), "pairs": count}
                         for (kind, module, rva), count in shown_callers],
                "rowLimit": MAX_CALLER_COUNTS,
                "distinctCallerCount": len(ranked_callers),
                "authenticatedPairCount": authenticated_pairs,
                "unresolvedPairCount": pair_count - authenticated_pairs,
                "truncated": len(ranked_callers) > len(shown_callers),
                "omittedCallerCount": len(ranked_callers) - len(shown_callers),
                "omittedPairCount": sum(count for _key, count in ranked_callers[MAX_CALLER_COUNTS:]),
            },
            "lockDataPtr": {
                "flagPhase": "entry", "flagField": "sourceFlagsWord", "flagBit": 8,
                "stateCounts": dict(lock_state_counts), "samples": lock_samples,
                "perStateSampleLimit": MAX_LOCK_STATE_SAMPLES,
                "samplesTruncated": {state: lock_state_counts[state] > len(lock_samples[state])
                                     for state in lock_states},
                "evidenceBoundary": "Observed entry wire-state bit only; unavailable means no declared valid flag sample. No codec branch, lookup success, decoded bytes or voice ownership is established.",
            },
            "sourceConsumers": {
                "perKindSampleLimit": MAX_CONSUMER_PAIR_SAMPLES,
                "rows": [{"sourceKind": kind, "pairCount": source_kind_counts[kind],
                          "samples": consumer_samples[kind],
                          "samplesTruncated": source_kind_counts[kind] > len(consumer_samples[kind])}
                         for kind in consumer_kinds],
                "evidenceBoundary": "Recorded consumer entry/result fields and parent capture IDs only. Parent IDs are retained for raw-trace nesting verification; they do not establish asynchronous path ownership, pointer lifetime or successful lookup.",
            },
            "sourceConsumerRelations": relations,
        }
        if bridge_relations:
            source_summary["sourceBridgeRelations"] = bridge_relations
        if owner_carrier_relations:
            source_summary["ownerCarrierRelations"] = owner_carrier_relations
    return {"schema": SCHEMA, "status": "validated" if diagnostic_count == 0 else "incomplete",
            "claimsAvailable": diagnostic_count == 0, "eventCount": event_count, "eventKinds": dict(counts),
            "sessionCount": len(sessions), "sourcePairCount": pair_count, "diagnosticCount": diagnostic_count,
            "diagnostics": diagnostics, "diagnosticsTruncated": diagnostic_count > len(diagnostics),
            "moduleFacts": ranges if diagnostic_count == 0 else {}, "sourcePairs": samples if diagnostic_count == 0 else [],
            "sourceSummary": source_summary,
            "pairSamplesTruncated": pair_count > MAX_PAIR_SAMPLES,
            "evidenceBoundary": {"direct": "Complete recorded source entry/result pairs and fixed scalar fields only. Module facts authenticate reported path/name/extent against selected disk files, not mapped code-page contents.",
                "conditional": "ASLR caller RVA is emitted only inside authenticated module extents.",
                "unresolved": "Source pointer lifetime, successful registry lookup, external-cookie ownership, file/codec identity and audibility remain open. Integer equality creates no ownership edge."}}


def audit_capture(
    game_root: Path, manifest: Path, trace: Path, output: Path, diagnostics: Path | None = None,
    *, max_input_bytes: int | None = None, max_events: int | None = None,
) -> dict[str, Any]:
    byte_limit = _positive_budget(MAX_INPUT_BYTES if max_input_bytes is None else max_input_bytes, "max_input_bytes")
    event_limit = _positive_budget(MAX_EVENTS if max_events is None else max_events, "max_events")
    game_root, manifest, trace = game_root.resolve(), manifest.resolve(), trace.resolve()
    output = observer._check_generated_path(output)
    diagnostics = (diagnostics or core.diagnostics_path(trace)).resolve()
    for protected in (manifest, trace, diagnostics, CONTRACT_PATH, *(game_root / path for path in (
            "Endfield.exe", "GameAssembly.dll", "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
            "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll"))):
        if observer._same_file(output, protected):
            raise core.CaptureConfigurationError(f"audit output aliases selected evidence: {protected}")
    contract, native_gate = load_validated_source_contract(
        gameassembly=game_root / "GameAssembly.dll",
        metadata=game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        ak_sound_engine=game_root / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll")
    if contract is None:
        report = {"schema": SCHEMA, "status": native_gate["status"], "claimsAvailable": False, "nativeGate": native_gate,
                  "sourcePairs": [], "diagnostics": [{"check": "selectedNativeInputs", "detail": native_gate["detail"]}]}
    else:
        profile = capture.load_manifest(manifest)
        recipe_gate = observer.validate_profile_recipe(profile, contract, game_root)
        verified = core.verify_game_files(game_root, profile)
        expectations = {prefix: {"path": str(verified[key]), "name": verified[key].name,
                        "size": pe_mapped_image_size(verified[key]), "fileSize": verified[key].stat().st_size,
                        "sha256": profile["files"][key]["sha256"]}
                        for prefix, key in (("Module", "gameAssembly"), ("NativeModule", "akSoundEngine"))}
        try:
            # The report hashes exactly the bounded immutable bytes it audits,
            # so concurrent appends cannot be associated with an unscanned trace.
            trace_raw = read_bounded_snapshot(trace, max_input_bytes=byte_limit)
            diagnostic_raw = read_bounded_snapshot(diagnostics, max_input_bytes=byte_limit)
            report = audit_events(read_bounded_events(trace, trace_raw, max_input_bytes=byte_limit, max_events=event_limit), profile, expectations,
                                  read_bounded_rows(diagnostic_raw, diagnostics, max_events=event_limit),
                                  max_events=event_limit,
                                  bridge_declaration=recipe_gate.get("queueNativeGate", {}).get("sourceBridgeRelationSpec"),
                                  owner_carrier_declaration=recipe_gate.get("ownerCarrierNativeGate", {}).get("ownerCarrierObserverSpec"))
            report["snapshotSha256"] = {"trace": hashlib.sha256(trace_raw).hexdigest(),
                                        "diagnostics": hashlib.sha256(diagnostic_raw).hexdigest()}
            core.verify_game_files(game_root, profile)
        except core.CaptureConfigurationError as exc:
            report = {"schema": SCHEMA, "status": "mismatched", "claimsAvailable": False, "sourcePairs": [],
                      "diagnostics": [{"check": "selectedFileRecheck", "detail": str(exc)[:1024]}]}
        except (ValueError, OSError, UnicodeError) as exc:
            report = {"schema": SCHEMA, "status": "incomplete", "claimsAvailable": False, "sourcePairs": [],
                      "diagnostics": [{"check": "traceFraming", "detail": str(exc)[:1024]}]}
        report["nativeGate"] = native_gate
        report["profileRecipeGate"] = recipe_gate
    report.setdefault("sourceSummary", {})
    report["limits"] = {"maxInputBytes": byte_limit, "maxEvents": event_limit, "maxLineBytes": MAX_LINE_BYTES}
    report["inputs"] = {"trace": str(trace), "diagnostics": str(diagnostics), "manifest": str(manifest), "selectedGameRoot": str(game_root)}
    observer._atomic_json(output, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=observer.DEFAULT_OUTPUT)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, help="Default: the capture's adjacent .diagnostics.jsonl stream.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-input-bytes", type=int, default=MAX_INPUT_BYTES,
                        help="Maximum immutable bytes per input; raise explicitly for a larger local recording.")
    parser.add_argument("--max-events", type=int, default=MAX_EVENTS,
                        help="Maximum rows per input and audited trace events; every admitted row is still checked.")
    args = parser.parse_args(argv)
    try:
        report = audit_capture(args.game_root, args.manifest, args.input, args.output, args.diagnostics,
                               max_input_bytes=args.max_input_bytes, max_events=args.max_events)
    except (core.CaptureConfigurationError, OSError, ValueError, KeyError) as exc:
        print(f"Audio source capture audit failed: {exc}", file=sys.stderr)
        return 1
    print(f"Audio source capture: {report['status']}; claimsAvailable={report['claimsAvailable']} -> {args.output}")
    if report.get("diagnostics"):
        print(json.dumps(report["diagnostics"][0], ensure_ascii=False), file=sys.stderr)
    return 0 if report["claimsAvailable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
