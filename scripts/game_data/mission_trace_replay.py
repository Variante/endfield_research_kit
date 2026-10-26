"""Reuse a passing Mission entry inspection with raw and receipt bindings intact.

This reads saved files only. Retained inventory consistency authenticates neither
the external origin of a package nor live ABI/IFix selection.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data import mission_trace_invocations


class ReplayError(trace.InspectionError):
    """A bounded admission diagnostic suitable for both a report and the CLI."""

    def __init__(self, detail: str, diagnostic: dict[str, Any]):
        super().__init__(detail)
        self.diagnostic = {"validator": "mission_trace_replay", **diagnostic}


def require_bound(condition: bool, check: str, detail: str, pin: dict[str, Any],
                  expected: Any, actual: Any, **identity: Any) -> None:
    if not condition:
        raise ReplayError(detail, {"failedCheck": check, "sourcePath": pin["path"],
                                   "sourceSha256": pin["sha256"], "expected": expected,
                                   "actual": actual, **identity})


def fingerprint(path: Path, limit: int) -> dict[str, Any]:
    before = path.stat()
    trace.require(before.st_size <= limit, f"Mission replay: input budget exceeded: {path}")
    digest, length = hashlib.sha256(), 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            length += len(block)
            trace.require(length <= limit, f"Mission replay: input grew beyond budget: {path}")
            digest.update(block)
    after = path.stat()
    trace.require(length == before.st_size and (before.st_size, before.st_mtime_ns) ==
                  (after.st_size, after.st_mtime_ns), f"Mission replay: input changed while hashing: {path}")
    return {"path": str(path.resolve()), "bytes": length, "sha256": digest.hexdigest()}


@dataclass
class Replay:
    session: Path
    report: dict[str, Any]
    inventory: dict[str, Any]
    artifacts: dict[str, dict[str, Any]]
    profile: dict[str, Any]
    entries: list[dict[str, Any]]
    inputs: list[dict[str, Any]]

    def unchanged(self, limits: trace.Limits) -> None:
        for pin in self.inputs:
            actual = fingerprint(Path(pin["path"]), max(limits.output_bytes, limits.json_bytes))
            trace.require(actual == pin, f"Mission replay: input changed during projection: {pin['path']}")


def load_inspection(inspection_dir: Path, *, limits: trace.Limits = trace.Limits()) -> Replay:
    """Rebind saved decoded rows; do not rerun native preparation or collection."""
    inspection_dir = inspection_dir.resolve(strict=True)
    report_path = inspection_dir / "inspection.json"
    report_pin = fingerprint(report_path, limits.json_bytes)
    report = trace.read_object(report_path, limits.json_bytes)
    facts = report.get("receiptFacts", {})
    expected_facts = {key: True for key in ("captureCompleteClaim", "healthyClaim", "allJournalRowsAccounted",
                                           "strictTransitionReceiptsConsistent")}
    require_bound(report.get("schema") in {"endfield.mission-trace-inspection.v1", "endfield.mission-trace-inspection.v2"} and
                  report.get("status") == "inspected" and isinstance(facts, dict) and
                  all(facts.get(key) is True for key in expected_facts),
                  "complete_inspection", "Mission replay: requires a complete healthy loss-free passing inspection",
                  report_pin, {"status": "inspected", **expected_facts},
                  {"status": report.get("status"), **{key: facts.get(key) if isinstance(facts, dict) else None
                                                      for key in expected_facts}})
    trace.require(facts.get("collectionBoundFailureMarkers") == [],
                  "Mission replay: inspection retains a failure marker")
    session = Path(report["session"]).resolve(strict=True)
    artifacts, inventory = trace.verify_inventory(session, limits)
    trace.require(inventory["inventorySha256"] == report["inventory"]["inventorySha256"],
                  "Mission replay: inspection/retained inventory SHA256 differs")
    profile, summary, hooks = trace.bindings(artifacts, limits)
    trace.require(artifacts["private/mission-trace-build-manifest.json"]["sha256"] == report["profileSha256"] and
                  artifacts["mission-trace/summary.json"]["sha256"] == report["providerSummarySha256"],
                  "Mission replay: inspection/profile/summary SHA256 differs")
    retained_session = trace.bound_object(artifacts, "session.json", limits)
    trace.require(retained_session.get("sessionId") == inventory["sessionId"],
                  "Mission replay: collection/session identity differs")
    paired = summary.get('schema') == 'endfieldCapture.missionTraceSummary.v3'
    trace.require(report['schema'] == ('endfield.mission-trace-inspection.v2' if paired else 'endfield.mission-trace-inspection.v1'),
                  'Mission replay: inspection/phase schema differs')
    trace.require(not paired or summary.get('pairingFailures') == 0, 'Mission replay: invocation pairing failures')
    trace.require(summary.get("complete") is True and summary.get("healthy") is True and
                  summary.get("writeComplete") is True and summary.get("finalCountersStable") is True and
                  all(type(summary.get(key)) is int and summary[key] == 0 for key in
                      ("dropped", "unrecorded", "undrainedRecordsAtStop", "activeCallbacksAtStop",
                       "unreadableFields", "truncatedFields", "strictRecoveryAttempts")) and
                  summary.get("firstFailure") is None and summary.get("strictRecovery") is None and
                  summary.get("failureReason") == "none" and summary.get("entryOnly") is (not paired) and
                  summary.get("missionFiltered") is False and summary.get("returnValuesObserved") is paired and
                  all(summary.get(key) is True for key in
                      ("installed", "hooksEverEnabled", "stopped", "quiescent",
                       "disabledTrampolinesRetainedUntilProcessExit")) and
                  all(summary.get(key) is False for key in
                      ("budgetExhausted", "durationBudgetExhausted", "strictPendingRecovery")) and
                  trace.strict_enable_history_consistent(summary, len(hooks)) and
                  all(trace.strict_receipt_consistent(summary.get(key), len(hooks))
                      for key in ("strictEnable", "strictDisable")),
                  "Mission replay: retained provider receipt is incomplete or inconsistent")
    trace.require(not any(name in artifacts and artifacts[name]["bytes"] for name in
                          ("runtime.error", "mission-trace/aborted.json", "mission-trace/strict-fatal.txt")),
                  "Mission replay: retained package has a failure marker")
    decoded_path = trace.safe_path(inspection_dir, report["decodedOutput"])
    decoded_pin = fingerprint(decoded_path, limits.output_bytes)
    journal = artifacts["mission-trace/events.jsonl"]
    trace.require(journal["bytes"] <= limits.journal_bytes, "Mission replay: journal byte budget exceeded")
    frequency = trace.integer(summary["qpcFrequency"], "QPC frequency")
    trace.require(frequency > 0, "Mission replay: zero QPC frequency")
    numeric = {key: trace.integer(summary[key], f"receipt {key}") for key in
               ("startQpc", "statusQpc", "startTickNs", "statusTickNs", "moduleBase", "moduleImageSize",
                "written", "attempted", "admitted", "bytesWritten", "nullFields", "startUtcFileTime100ns")}
    start, end = numeric["startQpc"], numeric["statusQpc"]
    start_tick, end_tick = numeric["startTickNs"], numeric["statusTickNs"]
    base, image_size = numeric["moduleBase"], numeric["moduleImageSize"]
    trace.require(end >= start and end_tick >= start_tick and numeric["startUtcFileTime100ns"] > 0,
                  "Mission replay: invalid receipt clocks")
    digest, raw_bytes, decoded_bytes = hashlib.sha256(), 0, 0
    entries, seen, calls, states = [], set(), Counter(), Counter()
    invocations = trace.Invocations()
    with journal["path"].open("rb") as raw, decoded_path.open("rb") as decoded:
        while line := raw.readline(limits.input_line_bytes + 1):
            trace.require(len(entries) < limits.rows and len(line) <= limits.input_line_bytes and line.endswith(b"\n"),
                          "Mission replay: raw row/line budget exceeded")
            interpreted = decoded.readline(limits.output_line_bytes + 1)
            trace.require(interpreted and len(interpreted) <= limits.output_line_bytes and interpreted.endswith(b"\n"),
                          "Mission replay: decoded row missing or oversized")
            raw_bytes += len(line)
            decoded_bytes += len(interpreted)
            trace.require(raw_bytes <= limits.journal_bytes and decoded_bytes <= limits.output_bytes,
                          "Mission replay: event byte budget exceeded")
            digest.update(line)
            source, value = trace.parse_json(line, "retained entry"), trace.parse_json(interpreted, "decoded entry")
            trace.require(isinstance(source, dict) and source.get("schema") == ('endfieldCapture.missionTraceEntry.v2' if paired else 'endfieldCapture.missionTraceEntry.v1'),
                          "Mission replay: unsupported raw entry schema")
            index = trace.integer(source["hookIndex"], "hook index", len(hooks) - 1)
            hook = hooks[index]
            sequence = trace.integer(source["sequence"], "entry sequence")
            label = f"Mission replay: sequence {sequence}, hook {hook['name']}"
            trace.require(sequence > 0 and sequence not in seen, label + ": duplicate or zero sequence")
            seen.add(sequence)
            qpc, tick = trace.integer(source["qpc"], "entry QPC"), trace.integer(source["tickNs"], "entry tickNs")
            thread = trace.integer(source["threadId"], "thread ID", (1 << 32) - 1)
            trace.require(thread > 0 and start <= qpc <= end and start_tick <= tick <= end_tick,
                          label + ": entry outside receipt clocks or zero thread")
            args, mask = source["args"], source["argsReadMask"]
            trace.require(isinstance(args, list) and len(args) == 8 and mask in (15, 255), label + ": invalid arguments/mask")
            for argument in args:
                trace.integer(argument, "raw argument")
            return_address = trace.integer(source["returnAddress"], "return address")
            caller = return_address - base if base <= return_address < base + image_size else 0
            trace.require(source["callerGameAssemblyRva"] == caller and source["hook"] == hook["name"],
                          label + ": raw caller/hook differs")
            observed = source["fields"]
            trace.require(isinstance(observed, list) and len(observed) == len(hook["fields"]), label + ": field count differs")
            expected_fields = []
            for spec, field in zip(hook["fields"], observed):
                trace.require(isinstance(field, dict) and field.get("state") in (1, 4) and mask & (1 << spec["arg"]),
                              label + f": field {spec['label']} is unreadable or truncated")
                if spec["kind"] == 4 and field["state"] == 1:
                    trace.require(field["value"] == args[spec["arg"]], label + ": scalar/raw argument differs")
                if spec["kind"] == 3 and spec["chain0"] == 4097 and field["state"] == 4:
                    trace.require(args[spec["arg"]] == 0, label + ": direct string null differs")
                expected_fields.append(trace.decode_field(spec, field, profile.get("enumDefinitions", {})))
                states[field["state"]] += 1
            expected = {"schema": "endfield.mission-trace-decoded-entry.v2" if paired else "endfield.mission-trace-decoded-entry.v1", "sequence": sequence,
                        "qpc": qpc, "tickNs": tick, "qpcOffset": qpc - start, "qpcFrequency": frequency,
                        "secondsFromStart": (qpc - start) / frequency, "threadId": thread, "hookIndex": index,
                        "hook": hook["name"], "returnAddress": return_address, "callerGameAssemblyRva": caller,
                        "argsReadMask": mask, "rawArgs": args, "fields": expected_fields}
            if paired:
                try:
                    pair = invocations.observe(source, hook)
                except trace.InvocationError as exc:
                    raise trace.InspectionError(str(exc)) from exc
                expected.update({k: source[k] for k in ('invocationId','parentInvocationId','depth','phase','returnValue')})
                if pair is not None:
                    expected['invocationReceipt'] = pair
            receiver = hook.get("receiverIdentity")
            if isinstance(receiver, dict):
                argument = trace.integer(receiver.get("arg"), "receiver argument", 7)
                trace.require(argument == (1 if "anonymousEntryProof" in hook else 0), label + ": receiver argument differs")
                expected["receiverIdentity"] = {"rawPointer": args[argument], "type": receiver["type"],
                                                "boundary": "Observed entry pointer only; object lifetime and causal ownership unresolved."}
            # JSON type equality matters: Python treats True == 1 and 1.0 == 1.
            actual_json = json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("ascii")
            expected_json = json.dumps(expected, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("ascii")
            require_bound(actual_json == expected_json, "decoded_entry_raw_binding",
                          label + ": decoded entry/raw binding differs", decoded_pin,
                          {"canonicalRowSha256": hashlib.sha256(expected_json).hexdigest()},
                          {"canonicalRowSha256": hashlib.sha256(actual_json).hexdigest()},
                          sequence=sequence, hook=hook["name"], rawSourcePath=str(journal["path"]),
                          rawSourceSha256=journal["sha256"])
            entries.append(value)
            calls[index] += 1
        trace.require(not decoded.read(1), "Mission replay: extra decoded entry")
    trace.require(raw_bytes == journal["bytes"] and digest.hexdigest() == journal["sha256"],
                  "Mission replay: raw journal changed during replay")
    count = len(entries)
    if paired:
        trace.require(invocations.finish(True) == report.get('invocations'), 'Mission replay: invocation receipt differs')
    trace.require(count > 0 and count == report["decodedRows"] == summary["written"] == summary["attempted"] == summary["admitted"] and
                  decoded_bytes == report["decodedBytes"] and raw_bytes == summary["bytesWritten"] and
                  min(seen) == 1 and max(seen) == count and states[4] == summary["nullFields"] and
                  all(calls[index] == row["calls"] for index, row in enumerate(summary["hooks"])),
                  "Mission replay: row, sequence, byte or hook accounting differs")
    inventory_pin = fingerprint(session / "collected/inventory.json", limits.json_bytes)
    trace.require(inventory_pin["sha256"] == inventory["inventorySha256"],
                  "Mission replay: retained inventory changed during replay")
    inputs = [report_pin, decoded_pin, inventory_pin,
              fingerprint(Path(__file__), limits.json_bytes), fingerprint(Path(trace.__file__), limits.json_bytes),
              fingerprint(Path(mission_trace_invocations.__file__), limits.json_bytes)]
    replay = Replay(session, report, inventory, artifacts, profile, entries, inputs)
    replay.unchanged(limits)
    return replay
