#!/usr/bin/env python3
"""Focused tests for the HGRP/Lit HGBuffer payload drift gate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "verify_deferred_gbuffer_payload_contract.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_deferred_gbuffer_payload_contract", MODULE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load verifier module: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def current_inputs() -> dict[str, str]:
    return {
        "source_text": MODULE.SOURCE_PATH.read_text(encoding="utf-8"),
        "sidecar_text": MODULE.SIDECAR_PATH.read_text(encoding="utf-8"),
        "runtime_text": MODULE.RUNTIME_PATH.read_text(encoding="utf-8"),
        "material_text": MODULE.MATERIAL_PATH.read_text(encoding="utf-8"),
    }


class DeferredGBufferPayloadContractTests(unittest.TestCase):
    def test_current_source_sidecar_and_material_pass(self) -> None:
        report = MODULE.validate_payload_contract(**current_inputs())
        self.assertEqual(report["status"], "pass", report["failures"])
        self.assertEqual(report["failedCount"], 0)
        self.assertEqual(len(report["knownGaps"]), 3)
        motion_gap = next(
            item for item in report["knownGaps"]
            if item["check"] == "sidecar.scene_motion"
        )
        self.assertEqual(motion_gap["status"], "partial")
        self.assertIn("previous camera/object clip history", motion_gap["evidence"])
        self.assertIn("MeshRenderer motion-vector mode", motion_gap["evidence"])

    def test_missing_porosity_term_reports_bounded_failure(self) -> None:
        inputs = current_inputs()
        inputs["sidecar_text"] = inputs["sidecar_text"].replace(
            "_PorosityFactorY * roughness +", "_MissingPorosityY * roughness +"
        )
        report = MODULE.validate_payload_contract(**inputs)
        self.assertEqual(report["status"], "validation_failed")
        self.assertEqual(report["failures"][0]["check"], "sidecar.mro_and_porosity_lanes")
        self.assertIn("_PorosityFactorY * roughness +", report["failures"][0]["actual"])
        self.assertIn("EndfieldCharInfoHGRPLitUnavailable.shader", report["failures"][0]["source"])

    def test_missing_resolver_alias_reports_exact_expected_token(self) -> None:
        inputs = current_inputs()
        inputs["runtime_text"] = inputs["runtime_text"].replace(
            "command.SetGlobalTexture(ResolverGBufferT24Id, gBufferB)",
            "command.SetGlobalTexture(ResolverGBufferT24Id, gBufferA)",
            1,
        )
        report = MODULE.validate_payload_contract(**inputs)
        self.assertEqual(report["status"], "validation_failed")
        failure = next(
            item for item in report["failures"]
            if item["check"] == "runtime.resolver_alias_boundary"
        )
        self.assertIn("ResolverGBufferT24Id, gBufferB", failure["actual"])
        self.assertIn("EndfieldRecoveredDeferredGBufferFrame.cs", failure["source"])


if __name__ == "__main__":
    unittest.main()
