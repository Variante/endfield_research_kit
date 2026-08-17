#!/usr/bin/env python3
"""Tests for the bounded external-only M23 correlation contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_m23_external_correlation.py")
SPEC = importlib.util.spec_from_file_location("validate_m23_external_correlation", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


FIXTURE = SCRIPT.parent / "original_m23_dxbc_exact" / "fixtures" / "dxcap_m23_bounded.xml"
PARSER = SCRIPT.parent / "original_m23_dxbc_exact" / "dxcap_xml_evidence.py"
PARSER_SPEC = importlib.util.spec_from_file_location("dxcap_xml_evidence", PARSER)
assert PARSER_SPEC and PARSER_SPEC.loader
PARSER_MODULE = importlib.util.module_from_spec(PARSER_SPEC)
PARSER_SPEC.loader.exec_module(PARSER_MODULE)


def _manifest() -> dict:
    return {
        "schemaVersion": 1,
        "policy": {
            "configurationBoundary": "external_telemetry_only",
            "intrusiveCaptureAttempted": False,
        },
        "harnessActionAttestation": {
            "clientAttachedByHarness": False,
            "debuggerAttached": False,
            "codeInjected": False,
            "clientOrDriverPatched": False,
            "processMemoryRead": False,
            "processModulesEnumerated": False,
            "commandLineCollected": False,
        },
        "capabilities": {
            "acceptedClientProcessCount": 1,
            "configuredBinaryPinsMatch": True,
        },
    }


class ExternalCorrelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dxcap = PARSER_MODULE.parse_dxcap(FIXTURE)

    def test_external_attestation_produces_candidate_only(self) -> None:
        report = M.validate_documents(self.dxcap, _manifest())
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["correlation"]["drawCandidate"])
        self.assertEqual(report["correlation"]["actorObjectIdentity"], "unavailable_external_only")
        self.assertFalse(report["admission"]["exactShaderByteParity"])
        self.assertFalse(report["admission"]["drawTimeCb3Available"])
        self.assertFalse(report["admission"]["visualAdmission"])

    def test_missing_telemetry_manifest_fails_closed(self) -> None:
        report = M.validate_documents(self.dxcap, None)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["firstFailure"], "telemetry.manifest_present")

    def test_invasive_attestation_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["harnessActionAttestation"]["processMemoryRead"] = True
        report = M.validate_documents(self.dxcap, manifest)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["firstFailure"], "telemetry.attestation.processMemoryRead")

    def test_wrong_telemetry_boundary_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["policy"]["configurationBoundary"] = "injected"
        report = M.validate_documents(self.dxcap, manifest)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["firstFailure"],
                         "telemetry.external_only_boundary")

    def test_wrong_stride_is_not_an_m23_candidate(self) -> None:
        dxcap = copy.deepcopy(self.dxcap)
        draw = dxcap["draw_calls"][0]
        draw["m23_candidate"]["exact_m23_candidate"] = False
        report = M.validate_documents(dxcap, _manifest())
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["firstFailure"], "dxcap.candidate_draw_present")


if __name__ == "__main__":
    unittest.main()
