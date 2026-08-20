#!/usr/bin/env python3
"""Tests for character telemetry output validation."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import character_dynamics_telemetry as telemetry  # noqa: E402
import validate_character_dynamics_telemetry as validator  # noqa: E402


class ValidateCharacterDynamicsTelemetryTests(unittest.TestCase):
    def _write_trace(self, path: Path, *, include_handshake: bool = True) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        target = manifest["targets"]["chen-overview"]
        rows = []

        def add(kind: str, **values: object) -> None:
            rows.append({
                "schema": telemetry.EVENT_SCHEMA,
                "sessionId": "test-session",
                "seq": len(rows),
                "monotonicMs": float(len(rows)),
                "utc": "2026-08-20T00:00:00.000Z",
                "kind": kind,
                **values,
            })

        add(
            "session_start",
            gameBuild=manifest["gameBuild"],
            targetId="chen-overview",
            target=target,
            exportFingerprint=manifest["files"]["metadata"]["sha256"],
            verifiedFiles={
                name: {"path": str(Path("D:/Program Files/Endfield Game") / spec["relativePath"]), "bytes": spec["bytes"], "sha256": spec["sha256"]}
                for name, spec in manifest["files"].items()
            },
        )
        if include_handshake:
            add(
                "native_module_verified",
                modulePathMatch=True,
                moduleSizeMatch=True,
                verifiedFiles=rows[0]["verifiedFiles"],
                hookStates={name: "attached" for name in manifest["hooks"]},
            )
        add("capture_started", targetId="chen-overview", trigger="test")
        add(
            "hook_enter",
            hook="transformWriteback",
            registers={
                "rcx": {"pointer": "0x1000", "snapshot": {"status": "read", "length": 16, "bytes": "00" * 16}},
                "rdx": {"pointer": "0x2000"},
                "r8": {"pointer": "0x3000", "snapshot": {"status": "read", "length": 16, "bytes": "11" * 16}},
                "r9": {"pointer": "0x0"},
            },
        )
        add("hook_leave", hook="transformWriteback", threadId=1, returnValue="0x0")
        add("capture_stop_ack", eventCount=2, captureStarted=True, terminalState=None)
        add("session_end", captureStarted=True, stopAck=True, terminalFailure=False)
        path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    def test_valid_trace_stays_observed_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            result = validator.validate_trace(path)
        self.assertEqual(result["status"], "observed_runtime_candidate")
        self.assertTrue(result["claims"]["transformWritebackCallObserved"])
        self.assertFalse(result["claims"]["solverImplemented"])
        self.assertFalse(result["claims"]["retailEquivalent"])
        self.assertFalse(result["claims"]["actorIdentityProven"])
        self.assertEqual(result["identityStatus"], "exact")

    def test_missing_native_handshake_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path, include_handshake=False)
            with self.assertRaisesRegex(validator.TraceValidationError, "native_module_verified"):
                validator.validate_trace(path)

    def test_sequence_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[2]["seq"] = 99
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "sequence"):
                validator.validate_trace(path)

    def test_unresolved_endminf_label_never_becomes_actor_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
            rows[0]["targetId"] = "endminf-overview"
            rows[0]["target"] = manifest["targets"]["endminf-overview"]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = validator.validate_trace(path)
        self.assertEqual(result["identityStatus"], "unresolved_endminf_alias")
        self.assertFalse(result["claims"]["actorIdentityProven"])

    def test_exact_target_still_never_proves_actor_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            result = validator.validate_trace(path)
        self.assertEqual(result["identityStatus"], "exact")
        self.assertFalse(result["claims"]["actorIdentityProven"])

    def test_missing_stop_ack_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows = [row for row in rows if row["kind"] != "capture_stop_ack"]
            for index, row in enumerate(rows):
                row["seq"] = index
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "capture_stop_ack"):
                validator.validate_trace(path)

    def test_capped_trace_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows.insert(-1, {"schema": telemetry.EVENT_SCHEMA, "sessionId": "test-session", "seq": 0, "kind": "capture_capped"})
            for index, row in enumerate(rows):
                row["seq"] = index
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "terminal failure"):
                validator.validate_trace(path)


if __name__ == "__main__":
    unittest.main()
