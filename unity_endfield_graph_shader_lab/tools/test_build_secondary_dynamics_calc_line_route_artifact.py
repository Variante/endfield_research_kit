#!/usr/bin/env python3
"""Focused tests for immutable CalcLine runtime-route promotion."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import burst_resolver_telemetry as telemetry  # noqa: E402
import build_secondary_dynamics_calc_line_route_artifact as builder  # noqa: E402
import test_validate_burst_resolver_telemetry as validator_tests  # noqa: E402
import validate_burst_resolver_telemetry as validator  # noqa: E402


class CalcLineRouteArtifactTests(unittest.TestCase):
    def test_capture_wrapper_publishes_only_checked_closed_artifact(self) -> None:
        wrapper = TOOLS.parent / "capture_endminf_burst_resolver.bat"
        raw = wrapper.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), "batch wrapper must remain CRLF")
        text = raw.decode("utf-8")
        self.assertIn("six pinned BurstDirectCall wrappers", text)
        self.assertNotIn("five pinned BurstDirectCall wrappers", text)
        self.assertIn("Get-Date -Format yyyyMMddTHHmmssfff", text)
        self.assertIn('--output "%TRACE_OUTPUT%"', text)
        self.assertIn('"%VALIDATE_SCRIPT%" "%TRACE_OUTPUT%" --output "%VALIDATION_OUTPUT%"', text)
        self.assertIn('"%ROUTE_SCRIPT%" "%VALIDATION_OUTPUT%" --output "%ROUTE_OUTPUT%"', text)
        self.assertIn('"%ROUTE_SCRIPT%" "%VALIDATION_OUTPUT%" --output "%ROUTE_OUTPUT%" --check', text)

    def _trace(self, root: Path, *, pointers: bool) -> Path:
        path = root / "trace.jsonl"
        fixture = validator_tests.ValidateBurstResolverTelemetryTests()
        fixture._write_trace(path)
        if pointers:
            fixture._add_all_pointer_events(path)
        return path

    @staticmethod
    def _add_route_events(
        path: Path,
        *,
        burst_results: list[bool],
        ifix: tuple[str, bool] | None = None,
    ) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        insert_at = next(index for index, row in enumerate(rows) if row["kind"] == "capture_stop_ack")
        burst = manifest["routeProbes"]["calcLineBurstEnabled"]
        ifix_probe = manifest["routeProbes"]["fromToRotationIfix"]
        common = {
            "schema": telemetry.EVENT_SCHEMA,
            "sessionId": "burst-test-session",
            "seq": 0,
            "monotonicMs": 0.0,
            "utc": "2026-08-20T00:00:00.000Z",
            "threadId": 42,
        }
        added: list[dict[str, object]] = []
        for result in burst_results:
            added.append({
                **common,
                "kind": "calc_line_burst_gate",
                "probe": "calcLineBurstEnabled",
                "methodIndex": burst["methodIndex"],
                "methodName": burst["methodName"],
                "result": result,
                "returnRegister": burst["returnRegister"],
                "callerReturnOffset": burst["invokeReturnOffset"],
                "methodInfo": burst["expectedMethodInfo"],
            })
        if ifix is not None:
            route, patched = ifix
            caller = next(
                row for row in ifix_probe["calcLineCallerReturns"]
                if row["route"] == route
            )
            added.append({
                **common,
                "kind": "calc_line_ifix_gate",
                "probe": "fromToRotationIfix",
                "methodIndex": ifix_probe["methodIndex"],
                "methodName": ifix_probe["methodName"],
                "result": patched,
                "patchId": ifix_probe["patchId"],
                "returnRegister": ifix_probe["returnRegister"],
                "fromToReturnOffset": ifix_probe["callReturnOffset"],
                "calcLineRoute": route,
                "calcLineCallerReturnOffset": caller["returnOffset"],
                "methodInfo": ifix_probe["expectedMethodInfo"],
            })
        rows[insert_at:insert_at] = added
        next(row for row in rows if row["kind"] == "capture_stop_ack")["eventCount"] += len(added)
        for seq, row in enumerate(rows):
            row["seq"] = seq
            row["monotonicMs"] = float(seq)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    @staticmethod
    def _validation(trace: Path) -> Path:
        payload = validator.validate_trace(trace)
        path = trace.with_suffix(".validation.json")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def test_exact_burst_cpu_route_builds_and_revalidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace = self._trace(root, pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            artifact = builder.build_artifact(validation)
            output = root / "route.json"
            output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            checked = builder.validate_artifact(output, validation)

        self.assertEqual(checked["status"], builder.STATUS)
        self.assertEqual(checked["route"]["executionRoute"], "BurstX64Sse2")
        self.assertEqual(checked["selectorObservation"], {
            "traceValidated": True,
            "burstGateObservationCount": 1,
            "burstEnabled": True,
            "directCallTargetObserved": True,
            "cpuSelectionObservationCount": 1,
            "cpuVariant": "x64_sse2",
            "ifixGateObservationCount": 0,
            "ifixPatched": False,
            "ifixCalcLineRoute": None,
        })
        self.assertEqual(len(checked["source"]["trace"]["sha256"]), 64)
        self.assertEqual(
            checked["nativeIdentity"]["gameAssemblyDisk"]["sha256"],
            telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)["files"]["gameAssembly"]["sha256"],
        )

    def test_exact_unpatched_direct_call_fallback_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace = self._trace(root, pointers=False)
            self._add_route_events(
                trace, burst_results=[False], ifix=("direct_call_fallback", False),
            )
            artifact = builder.build_artifact(self._validation(trace))
        self.assertEqual(artifact["route"]["executionRoute"], "ManagedUnpatched")
        self.assertEqual(artifact["route"]["kind"], "managed_unpatched_direct_call_fallback")
        self.assertFalse(artifact["selectorObservation"]["burstEnabled"])
        self.assertEqual(artifact["selectorObservation"]["ifixGateObservationCount"], 1)

    def test_candidate_without_route_closure_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=False)
            validation = self._validation(trace)
            with self.assertRaisesRegex(builder.RouteArtifactError, "exactly one CalcLine Burst gate"):
                builder.build_artifact(validation)

    def test_conflicting_burst_gate_observations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(trace, burst_results=[True, False])
            validation = self._validation(trace)
            with self.assertRaisesRegex(builder.RouteArtifactError, "exactly one CalcLine Burst gate"):
                builder.build_artifact(validation)

    def test_burst_and_ifix_cross_route_conflict_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(
                trace, burst_results=[True], ifix=("direct_call_fallback", False),
            )
            validation = self._validation(trace)
            with self.assertRaisesRegex(builder.RouteArtifactError, "cross-route conflict"):
                builder.build_artifact(validation)

    def test_disabled_burst_with_cpu_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(
                trace, burst_results=[False], ifix=("direct_call_fallback", False),
            )
            validation = self._validation(trace)
            with self.assertRaisesRegex(builder.RouteArtifactError, "CPU-route evidence"):
                builder.build_artifact(validation)

    def test_managed_worker_or_patched_fallback_is_rejected(self) -> None:
        for route, patched, message in (
            ("managed_worker", False, "explicitly unpatched"),
            ("direct_call_fallback", True, "explicitly unpatched"),
        ):
            with self.subTest(route=route, patched=patched), tempfile.TemporaryDirectory() as temp:
                trace = self._trace(Path(temp), pointers=False)
                self._add_route_events(trace, burst_results=[False], ifix=(route, patched))
                validation = self._validation(trace)
                with self.assertRaisesRegex(builder.RouteArtifactError, message):
                    builder.build_artifact(validation)

    def test_validation_report_tamper_is_rejected_against_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            payload = json.loads(validation.read_text(encoding="utf-8"))
            payload["sessionId"] = "forged-session"
            validation.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(builder.RouteArtifactError, "independent trace validation"):
                builder.build_artifact(validation)

    def test_validation_boolean_substitution_is_not_equal_to_integer_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            payload = json.loads(validation.read_text(encoding="utf-8"))
            payload["calcLineCpuSelection"]["observationCount"] = True
            validation.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(builder.RouteArtifactError, "independent trace validation"):
                builder.build_artifact(validation)

    def test_duplicate_trace_key_is_rejected_at_promotion_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(trace, burst_results=[True])
            lines = trace.read_text(encoding="utf-8").splitlines()
            lines[0] = lines[0][:-1] + ',"seq":0}'
            trace.write_text("\n".join(lines) + "\n", encoding="utf-8")
            # The source validator currently interprets the last duplicate,
            # so the promotion boundary must add the stricter JSON guarantee.
            validation = self._validation(trace)
            with self.assertRaisesRegex(builder.RouteArtifactError, "duplicate JSON key"):
                builder.build_artifact(validation)

    def test_boolean_trace_sequence_is_not_equal_to_integer_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(trace, burst_results=[True])
            rows = [
                json.loads(line)
                for line in trace.read_text(encoding="utf-8").splitlines()
            ]
            rows[0]["seq"] = False
            trace.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            # The source validator's numeric equality admits False == 0;
            # promotion must preserve JSON type identity independently.
            validation = self._validation(trace)
            with self.assertRaisesRegex(builder.RouteArtifactError, "seq is not"):
                builder.build_artifact(validation)

    def test_trace_change_during_build_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            trace = self._trace(Path(temp), pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            original = validator.validate_trace

            def validate_then_change(path: Path, manifest_path: Path) -> dict[str, object]:
                result = original(path, manifest_path)
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n",
                    encoding="utf-8",
                )
                return result

            with mock.patch.object(
                builder.trace_validator,
                "validate_trace",
                side_effect=validate_then_change,
            ):
                with self.assertRaisesRegex(builder.RouteArtifactError, "trace source changed"):
                    builder.build_artifact(validation)

    def test_trace_tamper_is_rejected_after_artifact_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace = self._trace(root, pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            artifact = builder.build_artifact(validation)
            output = root / "route.json"
            output.write_text(json.dumps(artifact), encoding="utf-8")
            trace.write_text(trace.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(builder.RouteArtifactError, "independent trace validation|differs"):
                builder.validate_artifact(output, validation)

    def test_artifact_digest_and_rebuild_are_both_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace = self._trace(root, pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            artifact = builder.build_artifact(validation)
            output = root / "route.json"
            artifact["route"]["executionRoute"] = "BurstAvx2"
            output.write_text(json.dumps(artifact), encoding="utf-8")
            with self.assertRaisesRegex(builder.RouteArtifactError, "canonical SHA-256"):
                builder.validate_artifact(output, validation)

            unsigned = {key: value for key, value in artifact.items() if key != "artifactSha256"}
            artifact["artifactSha256"] = builder._canonical_digest(unsigned)
            output.write_text(json.dumps(artifact), encoding="utf-8")
            with self.assertRaisesRegex(builder.RouteArtifactError, "independently rebuilt"):
                builder.validate_artifact(output, validation)

    def test_artifact_boolean_substitution_is_not_equal_to_integer_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace = self._trace(root, pointers=True)
            self._add_route_events(trace, burst_results=[True])
            validation = self._validation(trace)
            artifact = builder.build_artifact(validation)
            output = root / "route.json"
            artifact["selectorObservation"]["burstGateObservationCount"] = True
            unsigned = {
                key: value for key, value in artifact.items()
                if key != "artifactSha256"
            }
            artifact["artifactSha256"] = builder._canonical_digest(unsigned)
            output.write_text(json.dumps(artifact), encoding="utf-8")
            with self.assertRaisesRegex(builder.RouteArtifactError, "independently rebuilt"):
                builder.validate_artifact(output, validation)


if __name__ == "__main__":
    unittest.main()
