from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT / "scripts" / "story_recovery" / "build_bundle_manifest_story_audit.py"
)
SPEC = importlib.util.spec_from_file_location(
    "bundle_manifest_story_audit", MODULE_PATH
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def hash_table(record_size: int, fill: int) -> bytes:
    # One bucket and one value. Bucket offsets are relative to the blob start.
    return struct.pack("<III", 1, 12, 1) + bytes([fill]) * record_size


def make_manifest(target: str = "") -> bytes:
    asset = hash_table(AUDIT.ASSET_RECORD_SIZE, 0x11)
    bundle_dictionary = hash_table(AUDIT.BUNDLE_RECORD_SIZE, 0x22)
    bundles = struct.pack("<I", 1) + bytes([0x33]) * AUDIT.BUNDLE_RECORD_SIZE
    data_pool = target.encode("utf-16le") or b"payload"

    def text(value: str) -> bytes:
        encoded = value.encode("utf-16le")
        return struct.pack("<I", len(value)) + encoded

    logical = (
        struct.pack("<I", AUDIT.HEAD1)
        + text("manifest-hash")
        + struct.pack("<I", AUDIT.HEAD2)
        + text("hash-version")
        + text("")
    )
    for blob in (asset, bundle_dictionary, bundles):
        logical += struct.pack("<I", len(blob)) + blob
    logical += (
        struct.pack("<I", len(data_pool))
        + data_pool
        + struct.pack("<I", len(data_pool))
    )
    return brotli.compress(logical)


@unittest.skipIf(brotli is None, "brotli module is not installed")
class BundleManifestStoryAuditTests(unittest.TestCase):
    def test_valid_manifest_decodes_all_partitions(self) -> None:
        result = AUDIT.decode_manifest(make_manifest())
        self.assertEqual(result["assetDictionary"]["entryCount"], 1)
        self.assertEqual(result["bundleDictionary"]["entryCount"], 1)
        self.assertEqual(result["bundleArray"]["entryCount"], 1)
        self.assertEqual(result["dataPool"]["bytes"], 7)

    def test_bad_data_pool_trailer_fails_closed(self) -> None:
        compressed = make_manifest()
        logical = bytearray(brotli.decompress(compressed))
        struct.pack_into("<I", logical, len(logical) - 4, 999)
        with self.assertRaisesRegex(AUDIT.AuditError, "trailing length"):
            AUDIT.decode_manifest(brotli.compress(bytes(logical)))

    def test_bucket_gap_fails_closed(self) -> None:
        blob = struct.pack("<III", 1, 16, 1) + bytes(28)
        with self.assertRaisesRegex(AUDIT.AuditError, "expected 12"):
            AUDIT.validate_hash_table(blob, 24, "test")

    def test_decompressed_target_is_reported(self) -> None:
        target = "cutscene_example"
        compressed = make_manifest(target)
        logical = brotli.decompress(compressed)
        hits = AUDIT.find_exact_encoded_targets(
            {"compressed": compressed, "decompressed": logical}, [target]
        )
        self.assertEqual(
            [(row["source"], row["encoding"]) for row in hits],
            [("decompressed", "utf16le")],
        )


if __name__ == "__main__":
    unittest.main()
