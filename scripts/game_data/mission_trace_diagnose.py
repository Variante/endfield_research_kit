"""Diagnose preserved failed Mission traces without admitting their evidence.

The original package stays untouched. Locally computed hashes identify what
was examined; they are not a successful collection receipt. Retained profile,
activation and summary bindings are checked with the normal inspector, but a
failed session never becomes a healthy capture, even if its prefix is readable.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.game_data import mission_trace_inspect as inspector
from scripts.repo_paths import REPO_ROOT


def diagnose_session(session: Path, output_dir: Path, *, limits: inspector.Limits = inspector.Limits()) -> dict[str, Any]:
    session, output_dir = session.resolve(strict=True), output_dir.resolve()
    inspector.require(any(output_dir.is_relative_to((REPO_ROOT / root).resolve()) for root in ("reports", "scratch", "tmp")),
                      "diagnostic output must be under ignored reports/, scratch/, or tmp/")
    inspector.require(not output_dir.is_relative_to(session) and not session.is_relative_to(output_dir),
                      "diagnostic output must be outside the original session")
    inspector.require(not output_dir.exists() or not any(output_dir.iterdir()), "diagnostic output must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"schema": "endfield.mission-trace-diagnostic.v1", "status": "failed",
        "session": str(session), "captureAdmitted": False, "collectionAuthenticated": False,
        "boundary": "Locally identified failed-session diagnostics only; no capture admission, successful ABI read, return value or temporal causal join inferred.",
        "inputs": {}, "failedFields": [], "decodedRows": 0}
    try:
        artifacts = {}
        names = ["session.json", "private/mission-trace-build-manifest.json", "private/mission-trace.activation",
                 "private/runtime.conf", "mission-trace/summary.json"]
        if (session / "private/EndfieldCapture.dll").exists():
            names.append("private/EndfieldCapture.dll")
        for name in names:
            path = inspector.safe_path(session, name)
            data = inspector.read_bytes(path, limits.json_bytes)
            receipt = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            artifacts[name] = {"path": path, **receipt}
            report["inputs"][name] = receipt
        profile, summary, hooks = inspector.bindings(artifacts, limits)
        inspector.require(summary.get("complete") is False or summary.get("healthy") is False,
                          "use the normal authenticated inspector for a successful capture")
        report["failureReason"] = summary.get("failureReason")
        report["firstFailure"] = summary.get("firstFailure")
        report["retainedBindingsConsistent"] = True
        journal = inspector.safe_path(session, "mission-trace/events.jsonl")
        digest, input_bytes, calls, states = hashlib.sha256(), 0, Counter(), Counter()
        seen, failures, output_bytes = set(), 0, 0
        with journal.open("rb") as source, (output_dir / "diagnostic-events.jsonl").open("xb") as destination:
            while line := source.readline(limits.input_line_bytes + 1):
                input_bytes += len(line)
                inspector.require(input_bytes <= limits.journal_bytes and len(line) <= limits.input_line_bytes and line.endswith(b"\n"),
                                  "diagnostic journal exceeds bounds or has an unterminated row")
                inspector.require(report["decodedRows"] < limits.rows, "diagnostic row budget exceeded")
                digest.update(line)
                row = inspector.parse_json(line, "mission-trace/events.jsonl")
                inspector.require(isinstance(row, dict) and row.get("schema") == "endfieldCapture.missionTraceEntry.v1", "invalid diagnostic row schema")
                index = inspector.integer(row.get("hookIndex"), "hookIndex", len(hooks) - 1)
                hook = hooks[index]
                inspector.require(row.get("hook") == hook["name"], "diagnostic hook binding mismatch")
                sequence = inspector.integer(row.get("sequence"), "sequence")
                inspector.require(sequence > 0 and sequence not in seen, "duplicate or zero diagnostic sequence")
                seen.add(sequence)
                fields = row.get("fields")
                inspector.require(isinstance(fields, list) and len(fields) == len(hook["fields"]), "diagnostic field count mismatch")
                decoded = [inspector.decode_field(field, observed, profile.get("enumDefinitions", {}))
                           for field, observed in zip(hook["fields"], fields)]
                for number, field in enumerate(decoded):
                    states[field["stateName"]] += 1
                    if field["state"] in (2, 3):
                        failures += 1
                        if len(report["failedFields"]) < 64:
                            report["failedFields"].append({"sequence": sequence, "hook": hook["name"],
                                "fieldIndex": number, "qpc": row.get("qpc"), **field})
                calls[index] += 1
                payload = {"sequence": sequence, "qpc": row.get("qpc"), "hook": hook["name"],
                           "args": row.get("args"), "captureAdmitted": False, "fields": decoded}
                encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
                output_bytes += len(encoded)
                inspector.require(len(encoded) <= limits.output_line_bytes and output_bytes <= limits.output_bytes,
                                  "diagnostic output byte budget exceeded")
                destination.write(encoded)
                report["decodedRows"] += 1
        report["inputs"]["mission-trace/events.jsonl"] = {"bytes": input_bytes, "sha256": digest.hexdigest()}
        inspector.require(all(calls[index] == receipt["calls"] for index, receipt in enumerate(summary["hooks"])),
                          "diagnostic journal/summary hook counts differ")
        inspector.require(report["decodedRows"] == summary.get("written"), "diagnostic journal/summary written count differs")
        inspector.require(states["unreadable"] == summary.get("unreadableFields") and states["truncated"] == summary.get("truncatedFields"),
                          "diagnostic journal/summary failed field counts differ")
        report.update(status="diagnosed", fieldStates=dict(states), failedFieldCount=failures,
                      hookCalls={hooks[index]["name"]: count for index, count in sorted(calls.items())})
    except (inspector.InspectionError, OSError, KeyError, TypeError, ValueError) as exc:
        report["detail"] = str(exc)[:2048]
    (output_dir / "diagnostic.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = diagnose_session(args.session, args.output_dir)
    except (inspector.InspectionError, OSError, ValueError) as exc:
        print(f"[mission_trace_diagnose] failed; captureAdmitted=false; {exc}")
        return 1
    print(f"[mission_trace_diagnose] {report['status']}; captureAdmitted=false; rows={report['decodedRows']}")
    for field in report["failedFields"]:
        print(f"  sequence={field['sequence']} hook={field['hook']} field={field['label']} state={field['stateName']} read={field['read']}")
    if report.get("detail"):
        print(report["detail"])
    return 0 if report["status"] == "diagnosed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
