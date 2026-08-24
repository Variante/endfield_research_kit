#!/usr/bin/env python3
"""Focused tests for the read-only secondary-dynamics payload decoder."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_payload_decoder as decoder  # noqa: E402


class SecondaryDynamicsPayloadDecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = decoder.load_json(decoder.INPUT)

    def test_published_report_is_read_only_and_reconstructs(self) -> None:
        observed = decoder.build_report(allow_source_hash_mismatch=True)
        published = json.loads(decoder.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, published)
        self.assertEqual(published["schema"], decoder.REPORT_SCHEMA)
        self.assertFalse(published["implementation_boundary"]["solver_instantiated"])
        self.assertFalse(published["implementation_boundary"]["transforms_modified"])
        self.assertFalse(published["implementation_boundary"]["secondary_dynamics_verified"])
        self.assertFalse(published["implementation_boundary"]["solver_implemented"])
        self.assertFalse(published["source"]["hashes_match"])
        self.assertTrue(published["source"]["hash_checks"]["chen"]["hierarchy_name_map"]["matches"])
        self.assertFalse(published["source"]["hash_checks"]["chen"]["target_filter"]["exists"])
        self.assertEqual(
            {name: len(actor["cloths"]) for name, actor in published["actors"].items()},
            {"endminf": 4, "pelica": 7, "chen": 6},
        )

    def test_every_transform_pptr_is_mapped_or_explicit_null(self) -> None:
        report = decoder.decode_payload(self.payload)
        entries = [
            entry
            for actor in report["actors"].values()
            for cloth in actor["cloths"]
            for entry in cloth["transform_array"]["entries"]
        ]
        self.assertGreater(len(entries), 0)
        self.assertTrue(all(entry["pptr_valid"] for entry in entries))
        self.assertTrue(all(entry["status"] in {"resolved", "null"} for entry in entries))
        self.assertTrue(any(entry["status"] == "null" for entry in entries))
        self.assertTrue(all(entry["hierarchy_path"] for entry in entries if entry["status"] == "resolved"))

    def test_selection_data_has_matching_finite_positions_and_attributes(self) -> None:
        report = decoder.decode_payload(self.payload)
        for actor in report["actors"].values():
            for cloth in actor["cloths"]:
                selection = cloth["selection_data"]
                self.assertEqual(selection["count"], len(selection["positions"]))
                self.assertEqual(selection["count"], len(selection["attributes"]))
                self.assertTrue(selection["checks"]["positions_finite"])
                self.assertTrue(selection["checks"]["attributes_valid"])

    def test_proxy_arrays_use_pinned_native_layouts(self) -> None:
        report = decoder.decode_payload(self.payload)
        for actor in report["actors"].values():
            for cloth in actor["cloths"]:
                arrays = cloth["proxy_mesh_arrays"]
                reference = arrays["referenceIndices"]
                self.assertEqual(reference["status"], "typed_decoded_native_layout")
                self.assertFalse(reference["raw_preserved"])
                self.assertFalse(reference["semantic_unresolved"])
                self.assertEqual(reference["semantic"], "System.Int32")
                self.assertEqual(reference["stride_bytes"], 4)
                self.assertEqual(reference["byte_length"], reference["length"] * 4)
                transform = arrays["transformData"]
                self.assertEqual(transform["flagArray"]["stride_bytes"], 1)
                self.assertEqual(transform["initLocalPositionArray"]["stride_bytes"], 12)
                self.assertEqual(transform["initLocalRotationArray"]["stride_bytes"], 16)
                self.assertTrue(all(
                    row["status"] == "typed_decoded_native_layout"
                    for row in transform.values()
                ))

    def test_endminf_coat_closes_all_populated_proxy_arrays(self) -> None:
        report = decoder.decode_payload(self.payload)
        coat = next(row for row in report["actors"]["endminf"]["cloths"]
                    if row["game_object_path"] == "MC_Coat")
        arrays = coat["proxy_mesh_arrays"]
        rows = []
        for name, value in arrays.items():
            if name == "transformData":
                rows.extend(value.values())
            else:
                rows.append(value)
        populated = [row for row in rows if row.get("byte_length", 0) > 0]
        self.assertEqual(len(rows), 38)
        self.assertEqual(len(populated), 34)
        typed = [row for row in rows if row["status"] == "typed_decoded_native_layout"]
        raw = [row for row in rows if row["status"] == "raw_preserved"]
        self.assertEqual(len(typed), 38)
        self.assertEqual(len(raw), 0)
        self.assertTrue(all(not row["semantic_unresolved"] for row in typed))
        self.assertEqual(arrays["vertexToTriangles"]["stride_bytes"], 32)
        self.assertEqual(arrays["edges"]["semantic"], "Unity.Mathematics.int2")
        self.assertEqual(arrays["centerFixedList"]["values"], [2, 4, 12, 26, 28, 33, 45, 47, 55])
        self.assertTrue(any(value < 0 for value in arrays["vertexParentIndices"]["values"]))
        self.assertTrue(all(len(value) == 64 for value in arrays["boneWeights"]["values"]))

    def test_native_contract_decodes_vectors_and_rejects_malformed_bytes(self) -> None:
        layouts, _ = decoder._load_proxy_layouts()
        triangle_bytes = list(struct.pack("<6i", 1, 2, 3, 4, 5, 6))
        triangle_record = {"count": 2, "length": 2, "arrayBytes": triangle_bytes}
        triangles = decoder._contract_array(
            triangle_record, "fixture.triangles", layouts["triangles"])
        self.assertEqual(triangles["semantic"], "Unity.Mathematics.int3")
        self.assertEqual(triangles["stride_bytes"], 12)
        self.assertEqual(triangles["values"], [[1, 2, 3], [4, 5, 6]])
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "not divisible"):
            decoder._contract_array(
                {"count": 2, "length": 2, "arrayBytes": triangle_bytes[:-1]},
                "fixture.triangles", layouts["triangles"])

        edge_keys = decoder._contract_array(
            [{"x": 7, "y": 9}], "fixture.edgeKeys",
            layouts["edgeToTrianglesKeys"])
        edge_values = decoder._contract_array(
            [12], "fixture.edgeValues", layouts["edgeToTrianglesValues"])
        self.assertEqual(edge_keys["values"], [[7, 9]])
        self.assertEqual(edge_values["values"], [12])

    def test_layout_contract_hash_and_census_fail_closed(self) -> None:
        original = decoder.EXPECTED_LAYOUT_SHA256
        with mock.patch.object(decoder, "EXPECTED_LAYOUT_SHA256", "0" * 64):
            with self.assertRaisesRegex(decoder.PayloadDecodeError, "hash drift"):
                decoder._load_proxy_layouts()
        self.assertEqual(decoder.EXPECTED_LAYOUT_SHA256, original)

        layouts, contract = decoder._load_proxy_layouts()
        missing = dict(layouts)
        missing.pop("centerFixedList")
        payload = copy.deepcopy(self.payload)
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "missing native layout"):
            decoder.decode_payload(payload, proxy_layouts=missing, layout_contract=contract)

    def test_explicit_typed_array_checks_count_stride_bytes_and_finite_values(self) -> None:
        value = {
            "count": 2,
            "length": 2,
            "stride": 12,
            "arrayBytes": list(struct.pack("<6f", 1.0, 2.0, 3.0, -1.0, 0.5, 4.0)),
        }
        decoded = decoder._typed_array(value, "fixture.positions", decoder.TYPED_LAYOUTS["localPositions"])
        self.assertEqual(decoded["status"], "typed_decoded")
        self.assertEqual(decoded["values"], [[1.0, 2.0, 3.0], [-1.0, 0.5, 4.0]])

        bad_stride = dict(value, stride=4)
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "count/stride"):
            decoder._typed_array(bad_stride, "fixture.positions", decoder.TYPED_LAYOUTS["localPositions"])
        bad_bytes = dict(value, arrayBytes=value["arrayBytes"][:-1])
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "byte length"):
            decoder._typed_array(bad_bytes, "fixture.positions", decoder.TYPED_LAYOUTS["localPositions"])
        nonfinite = dict(value, arrayBytes=list(struct.pack("<6f", 1.0, 2.0, 3.0, float("nan"), 0.5, 4.0)))
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "non-finite"):
            decoder._typed_array(nonfinite, "fixture.positions", decoder.TYPED_LAYOUTS["localPositions"])

        self.assertEqual(decoder.TYPED_LAYOUTS["triangles"], ("int3", 12, "<3i"))
        self.assertEqual(decoder.TYPED_LAYOUTS["lines"], ("int2", 8, "<2i"))
        signed = {"count": 1, "length": 1, "stride": 4,
                  "arrayBytes": list(struct.pack("<i", -1))}
        self.assertEqual(
            decoder._typed_array(signed, "fixture.parent", ("int32", 4, "<i"))["values"],
            [-1],
        )

    def test_schema_source_hash_and_pptr_gates_are_fail_closed(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["schema"] = "spoofed"
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "unexpected schema"):
            decoder.validate_input(payload)

        payload = copy.deepcopy(self.payload)
        payload["source_build"]["game_assembly"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "source_build"):
            decoder.validate_input(payload)

        with self.assertRaisesRegex(decoder.PayloadDecodeError, "external Transform PPtr"):
            decoder._pptr({"m_FileID": 1, "m_PathID": 2}, "fixture", {2: "Root/Bone"}, 0)
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "unresolved Transform PPtr"):
            decoder._pptr({"m_FileID": 0, "m_PathID": 2}, "fixture", {}, 0)

    def test_decode_does_not_mutate_input(self) -> None:
        payload = copy.deepcopy(self.payload)
        original = copy.deepcopy(payload)
        decoder.decode_payload(payload)
        self.assertEqual(payload, original)

    def test_check_accepts_explicit_degraded_mode_without_writing(self) -> None:
        before = decoder.OUTPUT.read_bytes()
        self.assertEqual(decoder.main(["--check", "--allow-source-hash-mismatch"]), 0)
        self.assertEqual(decoder.OUTPUT.read_bytes(), before)

    def test_default_build_is_strict_and_diagnostic_mode_remains_explicit(self) -> None:
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "source hash mismatch"):
            decoder.build_report()
        mismatched = decoder._source_hash_checks(self.payload)
        mismatched["chen"]["hierarchy_name_map"]["matches"] = False
        with self.assertRaisesRegex(decoder.PayloadDecodeError, "source hash mismatch"):
            decoder._require_source_hashes(
                mismatched,
                allow_source_hash_mismatch=False,
            )

        before = decoder.OUTPUT.read_bytes()
        self.assertEqual(decoder.main([]), 1)
        self.assertEqual(decoder.OUTPUT.read_bytes(), before)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "diagnostic.json"
            with mock.patch.object(decoder, "OUTPUT", output):
                self.assertEqual(decoder.main(["--allow-source-hash-mismatch"]), 0)
                generated = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(generated["status"], "decoded_typed_proxy_payload_source_hash_mismatch")
                self.assertFalse(generated["source"]["hashes_match"])

    def test_check_never_accepts_override_or_writes(self) -> None:
        before = decoder.OUTPUT.read_bytes()
        self.assertEqual(decoder.main(["--check", "--refresh-input-hash"]), 2)
        self.assertEqual(decoder.OUTPUT.read_bytes(), before)

    def test_refresh_input_hash_pin_is_explicit_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "solver_inputs.json"
            source_path = root / "decoder.py"
            input_bytes = b'{"schema":"fixture"}\n'
            input_path.write_bytes(input_bytes)
            source_path.write_text(
                'EXPECTED_INPUT_SHA256 = "' + ("0" * 64) + '"\n',
                encoding="utf-8",
            )
            with mock.patch.object(decoder, "INPUT", input_path), mock.patch.object(
                decoder, "__file__", str(source_path)
            ):
                actual = decoder._refresh_input_hash_pin()
            expected = hashlib.sha256(input_bytes).hexdigest()
            self.assertEqual(actual, expected)
            self.assertIn(f'EXPECTED_INPUT_SHA256 = "{expected}"', source_path.read_text(encoding="utf-8"))

    def test_check_rejects_missing_or_stale_report_without_creating_it(self) -> None:
        report = decoder.build_report(allow_source_hash_mismatch=True)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "missing.json"
            with mock.patch.object(decoder, "OUTPUT", output):
                # _check_report itself remains a pure byte-level canonicality
                # check; main's strict source gate is covered above.
                with self.assertRaisesRegex(decoder.PayloadDecodeError, "missing generated report"):
                    decoder._check_report(report)
                self.assertFalse(output.exists())

                output.write_bytes(b"{}\n")
                before = output.read_bytes()
                with self.assertRaisesRegex(decoder.PayloadDecodeError, "stale or non-canonical"):
                    decoder._check_report(report)
                self.assertEqual(output.read_bytes(), before)

                # The check compares the same canonical bytes used for a
                # normal write, not merely parseable JSON.
                decoder._write_report(report)
                decoder._check_report(report)


if __name__ == "__main__":
    unittest.main()
