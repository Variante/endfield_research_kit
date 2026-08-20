#!/usr/bin/env python3
"""Tests for the fixed-client managed end-step integrator contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_integrator_contract as builder  # noqa: E402


class SecondaryDynamicsIntegratorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_report_is_pinned_and_current(self) -> None:
        self.assertEqual(self.payload["status"], "native_spans_hash_pinned_managed_integrator_boundary")
        self.assertFalse(self.payload["secondaryDynamicsVerified"])
        self.assertEqual(builder.build_contract(), self.payload)

    def test_indexed_end_step_span_and_helper_chain(self) -> None:
        root = self.payload["root"]
        self.assertEqual(root["methodIndex"], builder.METHOD_INDEX)
        self.assertEqual(root["spanBytes"], 3616)
        self.assertEqual(root["endVaExclusive"], "0x18676f784")
        calls = {(row["offset"], row["methodIndex"]) for row in root["selectedHelperCalls"]}
        self.assertEqual(
            calls,
            {
                ("0x3bb", 384698),
                ("0x4c3", 386216),
                ("0x55e", 386213),
                ("0xa1b", 386216),
                ("0xa95", 386214),
                ("0xcd3", 386216),
                ("0xd43", 386216),
            },
        )

    def test_branch_and_array_writeback_evidence(self) -> None:
        root = self.payload["root"]
        self.assertEqual(len(root["branches"]), 28)
        self.assertEqual(
            [(row["offset"], row["condition"], row["targetOffset"]) for row in root["branches"][-4:]],
            [("0x9c5", "jb", "0xc90"), ("0xad4", "jbe", "0xc90"), ("0xd9f", "jmp", "0xdc7"), ("0xdae", "jne", "0xdb6")],
        )
        writes = {(row["field"], row["offset"]) for row in root["memoryAccesses"] if row["access"] == "write"}
        self.assertIn(("velocityArray", "0xcf6"), writes)
        self.assertIn(("realVelocityArray", "0xd84"), writes)
        self.assertIn(("oldPosArray", "0xd93"), writes)
        self.assertIn(("frictionArray", "0x956"), writes)

    def test_job_offsets_and_helper_body_calls(self) -> None:
        root = self.payload["root"]
        pointers = {row["field"]: row["displacement"] for row in root["jobPointerLoads"]}
        self.assertEqual(pointers["stepParticleIndexArray"], "0x8")
        self.assertEqual(pointers["teamDataArray"], "0x18")
        self.assertEqual(pointers["collisionNormalArray"], "0xe8")
        helpers = {row["methodIndex"]: row for row in self.payload["helperBodies"]}
        self.assertEqual([(row["offset"], row["targetVa"]) for row in helpers[386213]["selectedDirectCalls"]], [("0x4e", "0x185f0ae78"), ("0x63", "0x185f00e9c")])
        self.assertEqual(len(helpers[386214]["selectedDirectCalls"]), 3)
        self.assertEqual(len(helpers[386216]["selectedDirectCalls"]), 0)

    def test_native_gate_fails_closed_for_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.dll"
            with self.assertRaises(builder.ContractError):
                builder.build_contract(missing, missing)

    def test_body_hash_and_chain_drift_are_rejected(self) -> None:
        original_hash = builder.EXPECTED_METHOD["bodySha256"]
        builder.EXPECTED_METHOD["bodySha256"] = "0" * 64
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_METHOD["bodySha256"] = original_hash

        original = builder.EXPECTED_CHAIN_CALLS[0]
        builder.EXPECTED_CHAIN_CALLS = ((original[0] + 1, original[1], original[2], original[3]),) + builder.EXPECTED_CHAIN_CALLS[1:]
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_CHAIN_CALLS = (original,) + builder.EXPECTED_CHAIN_CALLS[1:]

    def test_branch_memory_and_helper_drift_are_rejected(self) -> None:
        original_branch = builder.EXPECTED_BRANCHES[0]
        builder.EXPECTED_BRANCHES = ((original_branch[0], "je", original_branch[2]),) + builder.EXPECTED_BRANCHES[1:]
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_BRANCHES = (original_branch,) + builder.EXPECTED_BRANCHES[1:]

        original_site = builder.EXPECTED_MEMORY_SITES[0]
        builder.EXPECTED_MEMORY_SITES = (original_site[:4] + (8, original_site[5], original_site[6], original_site[7]),) + builder.EXPECTED_MEMORY_SITES[1:]
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_MEMORY_SITES = (original_site,) + builder.EXPECTED_MEMORY_SITES[1:]

        original_calls = builder.EXPECTED_HELPER_DIRECT_CALLS[386213]
        builder.EXPECTED_HELPER_DIRECT_CALLS[386213] = original_calls[:-1]
        try:
            with self.assertRaises(builder.ContractError):
                builder.build_contract()
        finally:
            builder.EXPECTED_HELPER_DIRECT_CALLS[386213] = original_calls


if __name__ == "__main__":
    unittest.main()
