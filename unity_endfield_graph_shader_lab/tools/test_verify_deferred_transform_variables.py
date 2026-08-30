#!/usr/bin/env python3
"""Focused diagnostics tests for deferred TransformVariables validation."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "verify_deferred_transform_variables.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_deferred_transform_variables",
    MODULE_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load verifier: {MODULE_PATH}")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class DeferredTransformVariablesValidationTests(unittest.TestCase):
    @staticmethod
    def complete_report() -> tuple[dict[str, object], str]:
        root = (
            verifier.LAB_ROOT
            / "scratch/character_recovery/deferred_transform_variables"
        )
        candidates = [
            root / "gpu_validation_d3d12.json",
            root / "gpu_validation_d3d11.json",
        ]
        path = next((value for value in candidates if value.is_file()), None)
        if path is None:
            raise AssertionError(
                "missing focused deferred TransformVariables GPU report"
            )
        report = json.loads(path.read_text(encoding="utf-8"))
        # The focused GPU report supplies the exact word fixture. Normalize
        # only run-level evidence status so these unit tests remain isolated
        # from an in-progress cross-API wrapper run.
        report["valid"] = True
        report["failures"] = []
        for field in verifier.EXPECTED_TEMPORAL_OWNER_FLAGS:
            report[field] = True
        return report, str(report["graphicsApi"])

    def test_complete_report_fixture_passes(self) -> None:
        report, api = self.complete_report()
        verifier.validate_gpu_report(
            report,
            api,
            Path("fixture.json"),
        )

    def test_changed_selected_word_is_actionable(self) -> None:
        current, api = self.complete_report()
        report = copy.deepcopy(current)
        report["actualWords"][96] = "0xDEADBEEF"
        with self.assertRaisesRegex(
            AssertionError,
            "Deferred TransformVariables validator failed: "
            rf"check=gpu_report.{api}.words; source=fixture.json;",
        ):
            verifier.validate_gpu_report(
                report,
                api,
                Path("fixture.json"),
            )

    def test_missing_fail_closed_gate_is_actionable(self) -> None:
        current, api = self.complete_report()
        report = copy.deepcopy(current)
        report["failClosedGates"][2]["diagnosticMatched"] = False
        with self.assertRaisesRegex(
            AssertionError,
            rf"check=gpu_report.{api}.fail_closed_gates",
        ):
            verifier.validate_gpu_report(
                report,
                api,
                Path("fixture.json"),
            )

    def test_missing_owner_history_gate_is_actionable(self) -> None:
        current, api = self.complete_report()
        report = copy.deepcopy(current)
        report.pop("temporalHistoryStatePolicyPassed")
        with self.assertRaisesRegex(
            AssertionError,
            rf"check=gpu_report.{api}.temporalHistoryStatePolicyPassed; "
            r"source=fixture.json; expected=True; actual=None",
        ):
            verifier.validate_gpu_report(
                report,
                api,
                Path("fixture.json"),
            )

    def test_frame_activation_gate_is_actionable(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            "check=frame.d3d12.activation",
        ):
            verifier.validate_frame_log(
                "Forcing GfxDevice: Direct3D 12\n" +
                verifier.PREREQUISITE_TOKEN +
                "\nExiting batchmode successfully now!\n",
                "d3d12",
                Path("frame.log"),
                False,
            )


if __name__ == "__main__":
    unittest.main()
