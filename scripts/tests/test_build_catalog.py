import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "build_catalog", ROOT / "tools/endfield-il2cpp/build_catalog.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakePe:
    buf = b"\0" * 64

    def file_offset_for_va(self, address):
        if 0 <= address < len(self.buf):
            return address, ".data", address
        return None, "", 0

    def u64_at_va(self, address):
        return struct.unpack_from("<Q", self.buf, address)[0]


class BuildCatalogTests(unittest.TestCase):
    def test_range_status_is_explicit_for_truncated_relationship(self):
        self.assertEqual(MODULE.status_for_range(1, 2, 3), "resolved")
        self.assertEqual(MODULE.status_for_range(2, 2, 3), "malformed")
        self.assertEqual(MODULE.status_for_range(-1, 0, 3), "resolved")
        self.assertEqual(MODULE.status_for_range(-1, 1, 3), "malformed")

    def test_pointer_table_rejects_invalid_entry_address(self):
        pe = FakePe()
        self.assertEqual(MODULE.ptr(pe, 60, 1), 0)
        self.assertEqual(MODULE.ptr(pe, 0, 0), 0)

    def test_signed_field_offset_reader(self):
        pe = FakePe()
        pe.buf = struct.pack("<i", -16) + b"\0" * 60
        self.assertEqual(MODULE.i32_at_va(pe, 0), -16)

    def test_read_bytes_rejects_section_crossing(self):
        pe = FakePe()
        pe.sections = [{"rawPointer": 0, "rawSize": 4}]
        self.assertIsNone(MODULE.read_bytes(pe, 2, 4))

    def test_method_mapping_fails_closed_on_count_mismatch(self):
        self.assertEqual(MODULE.method_mapping_status({"methodPointerCount": 2}, 3),
                         ("unresolved", "method-span-count-mismatch"))

    def test_aggregate_status_includes_top_level_counts(self):
        value = MODULE.aggregate_status(
            [{"status": "malformed", "nativeLayout": {"status": "unresolved"}}],
            [{"status": "resolved"}], [{"status": "resolved", "parameterRangeStatus": "malformed"}],
            [{"status": "resolved"}], [{"status": "malformed"}])
        self.assertEqual(value["metadataParameters"], 1)
        self.assertEqual(value["malformedImages"], 1)
        self.assertEqual(value["malformedParameterRanges"], 1)
        self.assertEqual(MODULE.catalog_status(value, []), "complete_with_unresolved")

    def test_catalog_status_is_complete_only_without_gaps(self):
        coverage = {
            "malformedTypes": 0, "malformedFields": 0, "malformedMethods": 0,
            "malformedParameters": 0, "malformedImages": 0,
            "malformedParameterRanges": 0, "unresolvedNativeLayouts": 0,
        }
        self.assertEqual(MODULE.catalog_status(coverage, []), "complete")
        self.assertEqual(
            MODULE.catalog_status(coverage, [{"reason": "method-span-count-mismatch"}]),
            "complete_with_unresolved",
        )

    def test_write_report_publishes_compact_json_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.json"
            MODULE.write_report(output, {"schema": "test", "rows": [1, 2]})
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["rows"], [1, 2])
            self.assertNotIn("\n  ", output.read_text(encoding="utf-8"))
            self.assertFalse((Path(directory) / ".catalog.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
