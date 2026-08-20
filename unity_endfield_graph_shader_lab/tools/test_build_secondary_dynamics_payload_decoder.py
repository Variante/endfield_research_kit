#!/usr/bin/env python3
"""Focused tests for the read-only secondary-dynamics payload decoder."""

from __future__ import annotations

import copy
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
        observed = decoder.build_report()
        published = json.loads(decoder.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, published)
        self.assertEqual(published["schema"], decoder.REPORT_SCHEMA)
        self.assertFalse(published["implementation_boundary"]["solver_instantiated"])
        self.assertFalse(published["implementation_boundary"]["transforms_modified"])
        self.assertFalse(published["implementation_boundary"]["secondary_dynamics_verified"])
        self.assertFalse(published["implementation_boundary"]["solver_implemented"])
        self.assertFalse(published["source"]["hashes_match"])
        self.assertFalse(published["source"]["hash_checks"]["chen"]["hierarchy_name_map"]["matches"])
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

    def test_proxy_arrays_without_explicit_stride_stay_raw(self) -> None:
        report = decoder.decode_payload(self.payload)
        for actor in report["actors"].values():
            for cloth in actor["cloths"]:
                arrays = cloth["proxy_mesh_arrays"]
                reference = arrays["referenceIndices"]
                self.assertEqual(reference["status"], "raw_preserved")
                self.assertTrue(reference["raw_preserved"])
                self.assertTrue(reference["semantic_unresolved"])
                self.assertEqual(reference["byte_length"], len(reference["array_bytes"]))

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

    def test_check_accepts_canonical_report_without_writing(self) -> None:
        before = decoder.OUTPUT.read_bytes()
        self.assertEqual(decoder.main(["--check"]), 0)
        self.assertEqual(decoder.OUTPUT.read_bytes(), before)

    def test_check_rejects_missing_or_stale_report_without_creating_it(self) -> None:
        report = decoder.build_report()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "missing.json"
            with mock.patch.object(decoder, "OUTPUT", output):
                self.assertEqual(decoder.main(["--check"]), 1)
                self.assertFalse(output.exists())

                output.write_bytes(b"{}\n")
                before = output.read_bytes()
                self.assertEqual(decoder.main(["--check"]), 1)
                self.assertEqual(output.read_bytes(), before)

                # The check compares the same canonical bytes used for a
                # normal write, not merely parseable JSON.
                decoder._write_report(report)
                self.assertEqual(decoder.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
