#!/usr/bin/env python3
"""Tests for the static TransformAccess writeback boundary contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
import build_secondary_dynamics_transform_writeback_contract as builder


class SecondaryDynamicsTransformWritebackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_report_is_pinned_and_rebuilds(self) -> None:
        self.assertEqual(self.payload["status"], "transform_writeback_access_closed")
        self.assertEqual(
            self.payload["native_gate"]["gameAssembly"]["sha256"],
            builder.EXPECTED_GAME_ASSEMBLY_SHA256,
        )
        self.assertEqual(builder.build_contract(), self.payload)

    def test_array_lifecycle_has_create_add_set_length_and_destroy_edges(self) -> None:
        roles = {row["role"] for row in self.payload["native"]["transformAccessArrayLifecycle"]}
        self.assertTrue({"array_create", "array_destroy", "array_add", "array_set_transform", "array_length"} <= roles)
        self.assertEqual(
            sum(row["role"] == "array_create" for row in self.payload["native"]["transformAccessArrayLifecycle"]),
            2,
        )
        self.assertEqual(
            sum(row["role"] == "array_destroy" for row in self.payload["native"]["transformAccessArrayLifecycle"]),
            2,
        )

    def test_transform_access_reads_and_writes_are_separate(self) -> None:
        calls = self.payload["native"]["transformAccessProperties"]
        reads = {row["method"] for row in calls if row["role"] == "transform_read"}
        writes = {row["method"] for row in calls if row["role"] == "transform_write"}
        self.assertTrue({"get_position", "get_rotation", "get_localPosition", "get_localRotation"} <= reads)
        self.assertTrue({"set_position", "set_rotation", "set_localPosition", "set_localRotation"} <= writes)
        self.assertTrue(any(row["ownerType"].endswith("+WriteTransformJob") for row in calls if row["role"] == "transform_write"))

    def test_managed_shape_keeps_result_arrays_and_index_signature(self) -> None:
        types = {row["fullName"]: row for row in self.payload["managed"]["types"]}
        write_fields = {row["name"] for row in types[builder.WRITE_JOB]["fields"]}
        self.assertTrue({"lastpositionArray", "lastrotationArray", "lastlocalPositionArray", "lastlocalRotationArray"} <= write_fields)
        signatures = {
            (row["type"], row["methodIndex"]): row
            for row in self.payload["managed"]["methodSignatures"]
        }
        read = signatures[(builder.READ_JOB, 384537)]
        self.assertEqual([row["metadataTypeName"] for row in read["parameters"]], ["System.Int32", "UnityEngine.Jobs.TransformAccess"])

    def test_pointer_provenance_and_solver_remain_open(self) -> None:
        boundary = self.payload["execution_boundary"]
        self.assertFalse(boundary["result_array_pointer_provenance_closed"])
        self.assertFalse(boundary["solver_numerics_recovered"])
        self.assertFalse(boundary["unity_runtime_executed"])

    def test_missing_native_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.dll"
            result = builder.build_contract(missing, missing)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["execution_boundary"]["transform_access_property_writes_closed"])


if __name__ == "__main__":
    unittest.main()
