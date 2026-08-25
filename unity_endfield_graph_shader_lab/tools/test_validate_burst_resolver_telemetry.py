#!/usr/bin/env python3
"""Tests for Burst resolver trace validation."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
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
            captureTool="frida-burst-resolver-telemetry/test",
            exportFingerprint=manifest["files"]["metadata"]["sha256"],
            verifiedFiles=files,
            kernel32ModuleName=manifest["kernel32ModuleName"],
            resolverModuleName=manifest["resolverModuleName"],
            nativeEvidenceBoundary=manifest["evidenceBoundary"],
        )
        identity = {
            "status": "already_loaded",
            "name": manifest["resolverModuleName"],
            "path": "D:/Program Files/Endfield Game/Endfield_Data/Plugins/x86_64/lib_burst_generated.dll",
            "base": "0x5000",
            "moduleBase": "0x5000",
            "size": manifest["files"]["resolver"]["bytes"],
            "exportEnumerationStatus": "available",
            "hashedExportCount": 628,
        }
        add(
            "native_module_verified",
            expectedModulePath="D:/Program Files/Endfield Game/GameAssembly.dll",
            expectedModuleSize=manifest["files"]["gameAssembly"]["bytes"],
            attachedModulePath="D:/Program Files/Endfield Game/GameAssembly.dll",
            attachedModuleSize=manifest["files"]["gameAssembly"]["bytes"],
            modulePathMatch=True,
            moduleSizeMatch=True,
            verifiedFiles=files,
            hookStates={name: "attached" for name in manifest["hooks"]},
            kernel32ModuleName=manifest["kernel32ModuleName"],
            resolverModuleName=manifest["resolverModuleName"],
            resolverModuleIdentity=identity,
            resolverExpectedPath="D:/Program Files/Endfield Game/Endfield_Data/Plugins/x86_64/lib_burst_generated.dll",
            resolverExpectedSize=manifest["files"]["resolver"]["bytes"],
            gameAssemblyModuleName=manifest["moduleName"],
            gameAssemblyModuleBase="0x180000000",
            gameAssemblyModuleSize=manifest["files"]["gameAssembly"]["bytes"],
            resolverExportMapSha256=manifest["resolverExportEnumeration"]["canonicalNameRvaSha256"],
            resolverExportMapCount=manifest["resolverExportEnumeration"]["hashedCount"],
            targets=[
                {
                    "id": target["id"],
                    "methodIndex": target["methodIndex"],
                    "methodName": target["methodName"],
                    "windowCount": len(target["windows"]),
                }
                for target in manifest["targets"]
            ],
        )
        add("capture_started", trigger="test")
        frame = {
            "address": "0x1867774a4",
            "module": "GameAssembly.dll",
            "modulePath": "D:/Program Files/Endfield Game/GameAssembly.dll",
            "moduleBase": "0x180000000",
            "moduleSize": manifest["files"]["gameAssembly"]["bytes"],
            "offset": "0x67774a4",
        }
        target = next(target for target in manifest["targets"] if target["id"] == "start_simulation_step_range_kernel")
        window = next(window for window in target["windows"] if window["role"] == "get_function_pointer_discard")
        match = {
            "targetId": target["id"],
            "targetMethodIndex": target["methodIndex"],
            "targetMethodName": target["methodName"],
            "targetFullName": target["fullName"],
            "role": window["role"],
            "methodIndex": window["methodIndex"],
            "windowStartOffset": window["startOffset"],
            "windowEndOffsetExclusive": window["endOffsetExclusive"],
            "frameAddress": frame["address"],
            "frameOffset": frame["offset"],
        }
        add(
            "get_proc_address",
            requestOrdinal=0,
            hModule="0x5000",
            lpProcName="0123456789abcdef0123456789abcdef",
            lpProcNameType="name",
            requestedExportIsHashed=True,
            returnPointer="0x7000",
            resolverModule=identity,
            resolvedAddress="0x7000",
            resolvedModuleName=manifest["resolverModuleName"],
            resolvedModulePath=identity["path"],
            resolvedModuleBase="0x5000",
            resolvedModuleSize=manifest["files"]["resolver"]["bytes"],
            resolvedModuleOffset="0x2000",
            resolvedExportName="0123456789abcdef0123456789abcdef",
            resolvedExportStatus="enumerated",
            caller=frame,
            callerBacktrace=[frame],
            callerBacktraceStatus="frames",
            gameAssemblyCallerBacktrace=[frame],
            backtraceStatus="gameassembly_frames",
            targetWindowMatches=[match],
            targetAttributionStatus="target_window_match",
            targetAttributionTargets=[target["id"]],
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

    def test_all_target_windows_are_counted_without_execution_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            first = next(row for row in rows if row["kind"] == "get_proc_address")
            extra_events = []
            for ordinal, target in enumerate(manifest["targets"][1:], start=1):
                window = target["windows"][0]
                frame_offset = window["startOffset"]
                frame = deepcopy(first["caller"])
                frame["offset"] = frame_offset
                frame["address"] = hex(int(frame["moduleBase"], 16) + int(frame_offset, 16))
                match = {
                    "targetId": target["id"],
                    "targetMethodIndex": target["methodIndex"],
                    "targetMethodName": target["methodName"],
                    "targetFullName": target["fullName"],
                    "role": window["role"],
                    "methodIndex": window["methodIndex"],
                    "windowStartOffset": window["startOffset"],
                    "windowEndOffsetExclusive": window["endOffsetExclusive"],
                    "frameAddress": frame["address"],
                    "frameOffset": frame["offset"],
                }
                event = deepcopy(first)
                event["requestOrdinal"] = ordinal
                event["caller"] = frame
                event["callerBacktrace"] = [frame]
                event["gameAssemblyCallerBacktrace"] = [frame]
                event["targetWindowMatches"] = [match]
                event["targetAttributionTargets"] = [target["id"]]
                extra_events.append(event)
            get_index = next(index for index, row in enumerate(rows) if row["kind"] == "get_proc_address")
            rows[get_index:get_index + 1] = [first, *extra_events]
            stop_ack = next(row for row in rows if row["kind"] == "capture_stop_ack")
            stop_ack["eventCount"] = len(manifest["targets"])
            for seq, row in enumerate(rows):
                row["seq"] = seq
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = validator.validate_trace(path)
        self.assertEqual(result["hashedExportRequestCount"], 5)
        self.assertEqual(result["hashedExportRequestsWithTargetAttribution"], 5)
        self.assertEqual(
            result["targetWindowObservations"],
            {
                "start_simulation_step_range_kernel": 1,
                "update_step_basic_poture_range_kernel": 1,
                "end_simulation_step_range_kernel": 1,
                "collider_start_simulation_step_range_kernel": 1,
                "collider_end_simulation_step_range_kernel": 1,
            },
        )
        self.assertTrue(result["claims"]["allThreeTargetWindowsObserved"])
        self.assertFalse(result["claims"]["resolverExportMappingProven"])

    def test_null_proc_result_and_failed_load_are_valid_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows.insert(
                3,
                {
                    key: rows[3][key]
                    for key in ("schema", "sessionId", "seq", "monotonicMs", "utc")
                }
                | {
                    "kind": "resolver_module_loaded",
                    "requestedPath": "D:/Program Files/Endfield Game/Endfield_Data/Plugins/lib_burst_generated.dll",
                    "hModule": "0x0",
                    "loadSucceeded": False,
                    "module": {
                        "status": "loadlibraryw",
                        "name": None,
                        "path": None,
                        "base": None,
                        "moduleBase": None,
                        "size": None,
                        "exportEnumerationStatus": "not_loaded",
                        "hashedExportCount": 0,
                    },
                    "resolverModuleIdentity": rows[1]["resolverModuleIdentity"],
                    "resolverExportMap": [],
                    "resolverExportMapCount": 0,
                },
            )
            for seq, row in enumerate(rows):
                row["seq"] = seq
            next(row for row in rows if row["kind"] == "capture_stop_ack")["eventCount"] = 2
            get_proc = next(row for row in rows if row["kind"] == "get_proc_address")
            get_proc["lpProcName"] = None
            get_proc["lpProcNameType"] = "null"
            get_proc["requestedExportIsHashed"] = False
            get_proc["returnPointer"] = "0x0"
            get_proc["resolvedAddress"] = None
            get_proc["resolvedModuleName"] = None
            get_proc["resolvedModulePath"] = None
            get_proc["resolvedModuleBase"] = None
            get_proc["resolvedModuleSize"] = None
            get_proc["resolvedModuleOffset"] = None
            get_proc["resolvedExportName"] = None
            get_proc["resolvedExportStatus"] = "null_return"
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

    def test_canonical_phase_order_rejects_pre_start_proc_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[2], rows[3] = rows[3], rows[2]
            for seq, row in enumerate(rows):
                row["seq"] = seq
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "event order"):
                validator.validate_trace(path)

    def test_frame_address_offset_and_handshake_base_are_checked(self) -> None:
        for mutation, message in (
            (lambda rows: rows[3]["caller"].update(address="0x1867774a5") or rows[3]["callerBacktrace"][0].update(address="0x1867774a5") or rows[3]["gameAssemblyCallerBacktrace"][0].update(address="0x1867774a5"), "address is not moduleBase plus offset"),
            (lambda rows: rows[1].update(gameAssemblyModuleBase="0x190000000"), "module base differs from the native handshake"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "trace.jsonl"
                self._write_trace(path)
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutation(rows)
                path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                with self.assertRaisesRegex(validator.TraceValidationError, message):
                    validator.validate_trace(path)

    def test_resolved_pointer_arithmetic_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[3]["returnPointer"] = "0x7001"
            rows[3]["resolvedAddress"] = "0x7001"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "resolvedAddress is not resolvedModuleBase"):
                validator.validate_trace(path)

    def test_successful_resolver_load_requires_module_base_equal_hmodule(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            identity = deepcopy(rows[1]["resolverModuleIdentity"])
            module = deepcopy(identity)
            module["status"] = "loadlibraryw"
            event = {
                key: rows[3][key]
                for key in ("schema", "sessionId", "seq", "monotonicMs", "utc")
            } | {
                "kind": "resolver_module_loaded",
                "requestedPath": identity["path"],
                "hModule": "0x5000",
                "loadSucceeded": True,
                "module": module,
                "resolverModuleIdentity": identity,
                "resolverExportMap": [],
                "resolverExportMapCount": 0,
            }
            rows.insert(3, event)
            rows[3]["module"]["base"] = "0x5001"
            rows[3]["module"]["moduleBase"] = "0x5001"
            for seq, row in enumerate(rows):
                row["seq"] = seq
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "module.base does not equal hModule"):
                validator.validate_trace(path)

    def test_successful_post_attach_load_cannot_spoof_empty_export_map(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            identity = deepcopy(rows[1]["resolverModuleIdentity"])
            module = deepcopy(identity)
            module["status"] = "loadlibraryw"
            event = {
                key: rows[3][key]
                for key in ("schema", "sessionId", "seq", "monotonicMs", "utc")
            } | {
                "kind": "resolver_module_loaded",
                "requestedPath": identity["path"],
                "hModule": "0x5000",
                "loadSucceeded": True,
                "module": module,
                "resolverModuleIdentity": identity,
                "resolverExportMap": [],
                "resolverExportMapCount": 0,
            }
            rows.insert(3, event)
            for seq, row in enumerate(rows):
                row["seq"] = seq
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "incomplete resolver export map"):
                validator.validate_trace(path)

    def test_export_status_name_and_hashed_flag_are_consistent(self) -> None:
        for mutation, message in (
            (lambda row: row.update(resolvedExportStatus="not_enumerated"), "not_enumerated result must not include resolvedExportName"),
            (lambda row: row.update(requestedExportIsHashed=False), "requestedExportIsHashed disagrees with lpProcName"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "trace.jsonl"
                self._write_trace(path)
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutation(rows[3])
                path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                with self.assertRaisesRegex(validator.TraceValidationError, message):
                    validator.validate_trace(path)

    def test_resolver_identity_status_is_enum_and_not_loaded_fields_are_null(self) -> None:
        for mutation, message in (
            (lambda identity: identity.update(status="bogus"), "status is invalid or unrecognized"),
            (lambda identity: identity.update(status="not_loaded_at_attach", path=None, base=None, moduleBase=None, size=None, exportEnumerationStatus="available"), "inconsistent export enumeration fields"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "trace.jsonl"
                self._write_trace(path)
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutation(rows[1]["resolverModuleIdentity"])
                path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                with self.assertRaisesRegex(validator.TraceValidationError, message):
                    validator.validate_trace(path)

    def test_stop_ack_count_and_clean_state_are_exact(self) -> None:
        for mutation, message in (
            (lambda row: row.update(eventCount=0), "eventCount differs"),
            (lambda row: row.update(terminalState="capped"), "non-clean terminal state"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "trace.jsonl"
                self._write_trace(path)
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                mutation(next(row for row in rows if row["kind"] == "capture_stop_ack"))
                path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                with self.assertRaisesRegex(validator.TraceValidationError, message):
                    validator.validate_trace(path)

    def test_manifest_pinned_export_map_digest_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[1]["resolverExportMapSha256"] = "0" * 64
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "pinned name/RVA map"):
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

    def test_target_window_schema_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[3]["targetWindowMatches"][0]["windowEndOffsetExclusive"] = "0x67775a7"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "windowEndOffsetExclusive drifted"):
                validator.validate_trace(path)

    def test_missing_all_module_caller_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            self._write_trace(path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[3].pop("callerBacktrace")
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(validator.TraceValidationError, "caller backtrace"):
                validator.validate_trace(path)


if __name__ == "__main__":
    unittest.main()
