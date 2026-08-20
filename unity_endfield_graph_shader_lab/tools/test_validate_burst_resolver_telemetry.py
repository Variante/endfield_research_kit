#!/usr/bin/env python3
"""Tests for Burst resolver trace validation."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import burst_resolver_telemetry as telemetry  # noqa: E402
import validate_burst_resolver_telemetry as validator  # noqa: E402


class ValidateBurstResolverTelemetryTests(unittest.TestCase):
    def _write_trace(self, path: Path, *, stop_ack: bool = True) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        files = {
            name: {
                "path": str(Path("D:/Program Files/Endfield Game") / spec["relativePath"]),
                "bytes": spec["bytes"],
                "sha256": spec["sha256"],
            }
            for name, spec in manifest["files"].items()
        }
        rows: list[dict[str, object]] = []

        def add(kind: str, **values: object) -> None:
            rows.append(
                {
                    "schema": telemetry.EVENT_SCHEMA,
                    "sessionId": "burst-test-session",
                    "seq": len(rows),
                    "monotonicMs": float(len(rows)),
                    "utc": "2026-08-20T00:00:00.000Z",
                    "kind": kind,
                    **values,
                }
            )

        add(
            "session_start",
            gameBuild=manifest["gameBuild"],
            exportFingerprint=manifest["files"]["metadata"]["sha256"],
            verifiedFiles=files,
            kernel32ModuleName=manifest["kernel32ModuleName"],
            resolverModuleName=manifest["resolverModuleName"],
        )
        identity = {
            "status": "already_loaded",
            "name": manifest["resolverModuleName"],
            "path": "D:/Program Files/Endfield Game/Endfield_Data/Plugins/lib_burst_generated.dll",
            "base": "0x5000",
            "size": 123456,
        }
        add(
            "native_module_verified",
            attachedModulePath="D:/Program Files/Endfield Game/GameAssembly.dll",
            attachedModuleSize=manifest["files"]["gameAssembly"]["bytes"],
            modulePathMatch=True,
            moduleSizeMatch=True,
            verifiedFiles=files,
            hookStates={name: "attached" for name in manifest["hooks"]},
            kernel32ModuleName=manifest["kernel32ModuleName"],
            resolverModuleName=manifest["resolverModuleName"],
            resolverModuleIdentity=identity,
        )
        add("capture_started", trigger="test")
        add(
            "get_proc_address",
            hModule="0x5000",
            lpProcName="BurstDirectCall_0",
            lpProcNameType="name",
            returnPointer="0x7000",
            gameAssemblyCallerBacktrace=[
                {
                    "address": "0x180123456",
                    "module": "GameAssembly.dll",
                    "modulePath": "D:/Program Files/Endfield Game/GameAssembly.dll",
                    "moduleBase": "0x180000000",
                    "moduleSize": manifest["files"]["gameAssembly"]["bytes"],
                    "offset": "0x123456",
                }
            ],
            backtraceStatus="gameassembly_frames",
            threadId=42,
        )
        if stop_ack:
            add(
                "capture_stop_ack",
                eventCount=1,
                captureStarted=True,
                terminalState=None,
                resolverModuleIdentity=identity,
            )
        add("session_end", captureStarted=True, stopAck=stop_ack, terminalFailure=False)
        path.write_text(
            "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_valid_trace_records_only_matching_resolver_handle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            result = validator.validate_trace(path)
        self.assertEqual(result["status"], "observed_runtime_candidate")
        self.assertEqual(result["getProcAddressEventCount"], 1)
        self.assertTrue(result["claims"]["gameAssemblyCallerBacktraceObserved"])
        self.assertFalse(result["claims"]["resolverExportMappingProven"])
        self.assertFalse(result["claims"]["gameStateWritten"])

    def test_null_proc_result_and_failed_load_are_valid_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows.insert(
                3,
                {
                    **rows[3],
                    "seq": 3,
                    "kind": "resolver_module_loaded",
                    "requestedPath": "D:/Program Files/Endfield Game/Endfield_Data/Plugins/lib_burst_generated.dll",
                    "hModule": "0x0",
                    "loadSucceeded": False,
                    "module": {"status": "loadlibraryw", "name": None, "path": None, "base": None, "size": None},
                },
            )
            for seq, row in enumerate(rows):
                row["seq"] = seq
            get_proc = next(row for row in rows if row["kind"] == "get_proc_address")
            get_proc["lpProcName"] = None
            get_proc["lpProcNameType"] = "null"
            get_proc["returnPointer"] = "0x0"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = validator.validate_trace(path)
        self.assertEqual(result["getProcAddressEventCount"], 1)

    def test_foreign_hmodule_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[3]["hModule"] = "0x9000"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "does not match"):
                validator.validate_trace(path)

    def test_missing_stop_ack_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path, stop_ack=False)
            with self.assertRaisesRegex(validator.TraceValidationError, "capture_stop_ack"):
                validator.validate_trace(path)

    def test_non_gameassembly_backtrace_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[3]["gameAssemblyCallerBacktrace"][0]["module"] = "kernel32.dll"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "non-GameAssembly"):
                validator.validate_trace(path)


if __name__ == "__main__":
    unittest.main()
