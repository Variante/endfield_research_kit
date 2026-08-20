#!/usr/bin/env python3
"""Focused tests for the secondary-dynamics owner verifier."""

from __future__ import annotations

import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import verify_secondary_dynamics_owner_recovery as verifier  # noqa: E402


class SecondaryDynamicsOwnerVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(verifier.OUTPUT.read_text(encoding="utf-8"))

    def test_current_totals_are_sourced_from_actor_inventory(self) -> None:
        self.assertEqual(
            verifier._component_totals(self.contract),
            {
                "BeyondDynamicBone.BeyondBoneCapsuleCollider": 130,
                "BeyondDynamicBone.BeyondBoneCloth": 67,
                "BeyondDynamicBone.BeyondBonePlaneCollider": 6,
                "BeyondDynamicBone.BeyondBoneSphereCollider": 11,
            },
        )
        self.assertEqual(verifier.owner_contract_total_diagnostics(self.contract), [])

    def test_success_path_uses_published_totals_and_common_cohort(self) -> None:
        output = io.StringIO()
        with mock.patch.object(verifier, "build_contract", return_value=self.contract):
            with redirect_stdout(output):
                self.assertEqual(verifier.main(), 0)
        self.assertIn("67 cloths, 147 colliders", output.getvalue())

    def test_actor_type_drift_reports_expected_actual_and_source_fingerprint(self) -> None:
        observed = copy.deepcopy(self.contract)
        component = "BeyondDynamicBone.BeyondBoneCloth"
        observed["actors"]["lizhiyan"]["dynamic_component_counts"][component] += 1
        observed["totals"][component] += 1

        diagnostics = verifier.contract_drift_diagnostics(self.contract, observed)
        drift = next(
            item
            for item in diagnostics
            if item["actor"] == "lizhiyan" and item["type"] == component
        )
        self.assertEqual(drift["validator"], verifier.VALIDATOR)
        self.assertEqual(drift["check"], "owner_contract_matches_actor_source_inventory")
        self.assertEqual(drift["expected"], 19)
        self.assertEqual(drift["actual"], 20)
        self.assertTrue(drift["source"]["path"].endswith("lizhiyan_postmodel_monobehaviour_filter.json"))
        self.assertEqual(
            drift["source"]["expected_sha256"],
            drift["source"]["actual_sha256"],
        )

    def test_source_hash_drift_reports_actor_type_and_hashes(self) -> None:
        observed = copy.deepcopy(self.contract)
        observed["actors"]["wulfa"]["target_filter"]["sha256"] = "0" * 64
        diagnostics = verifier.contract_drift_diagnostics(self.contract, observed)
        drift = next(
            item
            for item in diagnostics
            if item["actor"] == "wulfa" and item["type"] == "target_filter"
        )
        self.assertEqual(drift["check"], "owner_contract_source_hashes_match")
        self.assertEqual(drift["expected"], self.contract["actors"]["wulfa"]["target_filter"]["sha256"])
        self.assertEqual(drift["actual"], "0" * 64)
        self.assertEqual(drift["source"]["expected_sha256"], drift["expected"])
        self.assertEqual(drift["source"]["actual_sha256"], drift["actual"])
        self.assertTrue(drift["source"]["path"].endswith("wulfa_postmodel_monobehaviour_filter.json"))

    def test_published_total_drift_is_rejected_against_actor_inventory(self) -> None:
        drifted = copy.deepcopy(self.contract)
        component = "BeyondDynamicBone.BeyondBoneCapsuleCollider"
        drifted["totals"][component] -= 1
        diagnostics = verifier.owner_contract_total_diagnostics(drifted)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["check"], "owner_contract_totals_match_actor_source_inventory")
        self.assertEqual(diagnostics[0]["actor"], "<aggregate>")
        self.assertEqual(diagnostics[0]["type"], component)
        self.assertEqual(diagnostics[0]["expected"], 129)
        self.assertEqual(diagnostics[0]["actual"], 130)

    def test_main_failure_prints_structured_drift_diagnostic(self) -> None:
        observed = copy.deepcopy(self.contract)
        component = "BeyondDynamicBone.BeyondBonePlaneCollider"
        observed["actors"]["zhuangfy"]["dynamic_component_counts"][component] -= 1
        observed["totals"][component] -= 1
        with mock.patch.object(verifier, "build_contract", return_value=observed):
            with self.assertRaises(SystemExit) as raised:
                verifier.main()
        message = str(raised.exception)
        self.assertTrue(message.startswith("FAIL: "))
        payload = json.loads(message.split("\n", 1)[1])
        self.assertEqual(payload["validator"], verifier.VALIDATOR)
        drift = next(
            item
            for item in payload["failures"]
            if item["actor"] == "zhuangfy" and item["type"] == component
        )
        self.assertEqual(drift["expected"], 3)
        self.assertEqual(drift["actual"], 2)
        self.assertIn("source", drift)


if __name__ == "__main__":
    unittest.main()
