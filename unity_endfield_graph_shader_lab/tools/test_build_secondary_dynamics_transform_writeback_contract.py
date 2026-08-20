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
        self.assertEqual(self.payload["status"], "transform_writeback_call_edges_closed")
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
        self.assertFalse(boundary["array_ownership_closed"])
        self.assertFalse(boundary["schedule_closed"])
        self.assertFalse(boundary["solver_numerics_recovered"])
        self.assertFalse(boundary["unity_runtime_executed"])

    def test_missing_native_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.dll"
            result = builder.build_contract(missing, missing)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["execution_boundary"]["transform_access_property_writes_closed"])

    def _build_with_mutation(self, *, native_mutator=None, catalog_mutator=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native_path = root / "native.json"
            catalog_path = root / "catalog.json"
            native = json.loads(builder.DEFAULT_NATIVE.read_text(encoding="utf-8"))
            catalog = json.loads(builder.DEFAULT_METADATA_CATALOG.read_text(encoding="utf-8"))
            if native_mutator:
                native_mutator(native)
            if catalog_mutator:
                catalog_mutator(catalog)
            native_path.write_text(json.dumps(native), encoding="utf-8")
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            return builder.build_contract(native_evidence=native_path, metadata_catalog=catalog_path)

    def test_forged_call_json_fails_closed(self) -> None:
        def mutate(native):
            row = next(row for row in native["bodyTargets"] if row.get("methodIndex") == 384536)
            next(call for call in row["directCalls"] if call["offset"] == 441)["targetVa"] = "0x1"
        result = self._build_with_mutation(native_mutator=mutate)
        self.assertEqual(result["status"], "unavailable")

    def test_forged_metadata_type_index_fails_closed(self) -> None:
        def mutate(catalog):
            row = next(row for row in catalog["matchedTypes"] if row.get("fullName") == builder.WRITE_JOB)
            field = next(field for field in row["fields"] if field.get("name") == "lastpositionArray")
            field["typeIndex"] += 1
        result = self._build_with_mutation(catalog_mutator=mutate)
        self.assertEqual(result["status"], "unavailable")

    def test_zero_scan_bytes_fails_closed(self) -> None:
        def mutate(native):
            row = next(row for row in native["bodyTargets"] if row.get("methodIndex") == 384536)
            row["scanBytes"] = 0
        result = self._build_with_mutation(native_mutator=mutate)
        self.assertEqual(result["status"], "unavailable")

    def test_forged_method_name_and_pointer_fail_closed(self) -> None:
        def mutate_name(native):
            row = next(row for row in native["bodyTargets"] if row.get("methodIndex") == 384536)
            row["method"] = "Apply"
        def mutate_pointer(native):
            row = next(row for row in native["bodyTargets"] if row.get("methodIndex") == 384536)
            row["methodPointerVa"] = "0x180000000"
        for mutate in (mutate_name, mutate_pointer):
            result = self._build_with_mutation(native_mutator=mutate)
            self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
