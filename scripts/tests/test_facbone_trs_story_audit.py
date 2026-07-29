from __future__ import annotations

import importlib.util
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT / "scripts" / "story_recovery" / "build_facbone_trs_story_audit.py"
)
SPEC = importlib.util.spec_from_file_location("facbone_trs_story_audit", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def make_container() -> bytes:
    bucket_count = 4
    source_units = [
        {
            "guid": 1,
            "bones": [
                (0x1111, 2),
                (0x2222, 1),
            ],
        },
        {
            "guid": -2,
            "bones": [
                (0x3333, 1),
            ],
        },
    ]
    buckets: list[list[dict]] = [[] for _ in range(bucket_count)]
    for unit in source_units:
        buckets[abs(unit["guid"]) % bucket_count].append(unit)

    unit_count = len(source_units)
    unit_table_bytes = (
        4
        + bucket_count * AUDIT.UNIT_BUCKET_SIZE
        + unit_count * AUDIT.UNIT_ENTRY_SIZE
    )
    bone_table_start = 4 + unit_table_bytes
    bone_count = sum(len(unit["bones"]) for unit in source_units)
    matrix_table_start = bone_table_start + bone_count * AUDIT.BONE_ENTRY_SIZE

    bucket_blob = bytearray()
    unit_blob = bytearray()
    bone_blob = bytearray()
    matrix_blob = bytearray()
    unit_relative_cursor = 4 + bucket_count * AUDIT.UNIT_BUCKET_SIZE
    bone_cursor = bone_table_start
    matrix_cursor = matrix_table_start
    frame_value = 1.0

    for bucket in buckets:
        if not bucket:
            bucket_blob += struct.pack("<II", 0, 0)
            continue
        bucket_blob += struct.pack(
            "<II", unit_relative_cursor, len(bucket)
        )
        for unit in bucket:
            unit_blob += struct.pack(
                "<qII", unit["guid"], len(unit["bones"]), bone_cursor
            )
            unit_relative_cursor += AUDIT.UNIT_ENTRY_SIZE
            for bone_hash, frame_count in unit["bones"]:
                bone_blob += struct.pack(
                    "<QII", bone_hash, frame_count, matrix_cursor
                )
                bone_cursor += AUDIT.BONE_ENTRY_SIZE
                for _ in range(frame_count):
                    matrix_blob += struct.pack(
                        "<16f", *[frame_value + index for index in range(16)]
                    )
                    frame_value += 16.0
                    matrix_cursor += AUDIT.MATRIX_SIZE

    return (
        struct.pack("<II", unit_table_bytes, bucket_count)
        + bytes(bucket_blob)
        + bytes(unit_blob)
        + bytes(bone_blob)
        + bytes(matrix_blob)
    )


class FacBoneTRSStoryAuditTests(unittest.TestCase):
    def test_valid_container_decodes_complete_partitions(self) -> None:
        result = AUDIT.decode_facbone_trs(make_container())
        self.assertEqual(result["bucketCount"], 4)
        self.assertEqual(result["unitCount"], 2)
        self.assertEqual(result["boneCount"], 3)
        self.assertEqual(result["matrixCount"], 4)
        self.assertEqual(result["matrixTableEnd"], result["fileBytes"])
        self.assertEqual(result["nonFiniteFloatCount"], 0)

    def test_wrong_unit_bucket_fails_closed(self) -> None:
        data = bytearray(make_container())
        # First non-empty bucket is bucket 1. Change its guid from 1 to 2.
        first_unit_offset = 4 + 4 + 4 * AUDIT.UNIT_BUCKET_SIZE
        struct.pack_into("<q", data, first_unit_offset, 2)
        with self.assertRaisesRegex(AUDIT.AuditError, "expected 2"):
            AUDIT.decode_facbone_trs(bytes(data))

    def test_non_finite_matrix_fails_closed(self) -> None:
        data = bytearray(make_container())
        decoded = AUDIT.decode_facbone_trs(bytes(data))
        struct.pack_into("<f", data, decoded["matrixTableStart"], math.nan)
        with self.assertRaisesRegex(AUDIT.AuditError, "non-finite"):
            AUDIT.decode_facbone_trs(bytes(data))

    def test_exact_encoded_targets_find_both_encodings(self) -> None:
        target = "cutscene_example"
        data = target.encode("ascii") + target.encode("utf-16le")
        hits = AUDIT.find_exact_encoded_targets(data, [target])
        self.assertEqual(
            {(row["target"], row["encoding"]) for row in hits},
            {(target, "ascii"), (target, "utf16le")},
        )

    def test_inventory_requires_exact_current_family(self) -> None:
        files = []
        for name, expected in AUDIT.EXPECTED_EXTEND_DATA_FILES.items():
            files.append(
                {
                    "fileName": name,
                    "fileBlockType": expected["blockType"],
                    "length": expected["length"],
                    "fileDataMd5": expected["dataMd5"],
                }
            )
        payload = {
            "blocks": [{"version": 22097503}],
            "files": files,
            "summary": {
                "blockCount": 2,
                "chunkCount": 2,
                "missingBlockCount": 0,
                "missingChunkCount": 0,
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "facbone_inventory.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = AUDIT.validate_extend_data_inventory(path)
            self.assertEqual(result["fileCount"], 4)
            self.assertEqual(result["version"], [22097503])

            payload["files"].pop()
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(AUDIT.AuditError, "inventory drifted"):
                AUDIT.validate_extend_data_inventory(path)


if __name__ == "__main__":
    unittest.main()
