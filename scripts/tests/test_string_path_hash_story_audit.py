from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT
    / "scripts"
    / "story_recovery"
    / "build_string_path_hash_story_audit.py"
)
SPEC = importlib.util.spec_from_file_location(
    "build_string_path_hash_story_audit",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_hash_table(rows: list[tuple[int, str]]) -> bytes:
    pool = bytearray()
    offsets: list[int] = []
    for _, text in rows:
        offsets.append(len(pool))
        encoded = text.encode("utf-16le")
        pool.extend(struct.pack("<I", len(encoded)))
        pool.extend(encoded)
        pool.extend(b"\0\0")
    count = len(rows)
    pool_offset = 8 + count * 8 + count * 16
    buckets = b"".join(struct.pack("<q", index) for index in range(count))
    entries = b"".join(
        struct.pack("<qQ", hash_value, offset)
        for (hash_value, _), offset in zip(rows, offsets, strict=True)
    )
    return struct.pack("<II", pool_offset, count) + buckets + entries + pool


class StringPathHashStoryAuditTests(unittest.TestCase):
    def test_parser_validates_hash_to_path_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "StringPathHash.bin"
            path.write_bytes(
                make_hash_table(
                    [
                        (0x102030405060708, "Assets/First.asset"),
                        (0x112233445566778, "Assets/Second.asset"),
                    ]
                )
            )
            metadata, rows = MODULE.parse_string_path_hash(path)

        self.assertTrue(metadata["validated"])
        self.assertEqual(metadata["entryCount"], 2)
        self.assertEqual([row.path for row in rows], [
            "Assets/First.asset",
            "Assets/Second.asset",
        ])
        self.assertEqual(rows[1].hash_hex, "0x0112233445566778")

    def test_binary_scan_finds_both_byte_orders(self) -> None:
        selected = [
            {
                "target": "cutscene_test",
                "path": "Assets/cutscene_test.json",
                "hashSigned": 0x102030405060708,
                "hashUnsigned": 0x102030405060708,
                "hashHex": "0x0102030405060708",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            little = Path(temp_dir) / "little.bin"
            big = Path(temp_dir) / "big.bin"
            little.write_bytes(b"x" + bytes.fromhex("0807060504030201") + b"y")
            big.write_bytes(b"x" + bytes.fromhex("0102030405060708") + b"y")
            result = MODULE.scan_binary_paths((little, big), selected)

        self.assertEqual(result["hitCount"], 2)
        self.assertEqual(
            {row["byteOrder"] for row in result["hits"]},
            {"little", "big"},
        )

    def test_truncated_pool_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "StringPathHash.bin"
            path.write_bytes(make_hash_table([(123, "Assets/Test.asset")])[:-1])
            with self.assertRaisesRegex(ValueError, "truncated string"):
                MODULE.parse_string_path_hash(path)


if __name__ == "__main__":
    unittest.main()
