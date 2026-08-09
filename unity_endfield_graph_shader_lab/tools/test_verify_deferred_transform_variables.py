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
    def current_report() -> dict[str, object]:
        path = (
            verifier.LAB_ROOT
            / "scratch/character_recovery/deferred_transform_variables/"
            "gpu_validation_d3d12.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_current_report_passes(self) -> None:
        verifier.validate_gpu_report(
            self.current_report(),
            "d3d12",
            Path("fixture.json"),
        )

    def test_changed_selected_word_is_actionable(self) -> None:
        report = copy.deepcopy(self.current_report())
        report["actualWords"][96] = "0xDEADBEEF"
        with self.assertRaisesRegex(
            AssertionError,
            "Deferred TransformVariables validator failed: "
            "check=gpu_report.d3d12.words; source=fixture.json;",
        ):
            verifier.validate_gpu_report(
                report,
                "d3d12",
                Path("fixture.json"),
            )

    def test_missing_fail_closed_gate_is_actionable(self) -> None:
        report = copy.deepcopy(self.current_report())
        report["failClosedGates"][2]["diagnosticMatched"] = False
        with self.assertRaisesRegex(
            AssertionError,
            "check=gpu_report.d3d12.fail_closed_gates",
        ):
            verifier.validate_gpu_report(
                report,
                "d3d12",
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
