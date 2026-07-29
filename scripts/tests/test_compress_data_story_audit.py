from __future__ import annotations

import importlib.util
import json
import struct
import unittest
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT / "scripts" / "story_recovery" / "build_compress_data_story_audit.py"
)
SPEC = importlib.util.spec_from_file_location("compress_data_story_audit", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def logical_json(extra: dict | None = None) -> bytes:
    payload = {
        "m_allParameters": [],
        "type": "NodeCanvas.BehaviourTrees.BehaviourTree",
        "nodes": [],
        "connections": [],
        "canvasGroups": [],
        "localBlackboard": {"_variables": {}},
        "derivedData": {
            "repeat": True,
            "$type": (
                "NodeCanvas.BehaviourTrees.BehaviourTree"
                "+DerivedSerializationData"
            ),
        },
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload).encode("utf-16le")


def make_container(decoded_records: list[bytes]) -> bytes:
    records = []
    for decoded in decoded_records:
        compressed = brotli.compress(decoded)
        records.append(struct.pack("<II", len(compressed), len(decoded)) + compressed)
    header_size = 4 + 4 * len(records)
    offsets = []
    cursor = header_size
    for record in records:
        offsets.append(cursor)
        cursor += len(record)
    return (
        struct.pack("<I", len(records))
        + struct.pack(f"<{len(offsets)}I", *offsets)
        + b"".join(records)
    )


@unittest.skipIf(brotli is None, "brotli module is not installed")
class CompressDataStoryAuditTests(unittest.TestCase):
    def test_valid_container_decodes_all_records(self) -> None:
        data = make_container([logical_json(), logical_json()])
        result = AUDIT.decode_compress_data(data)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["headerSize"], 12)
        self.assertEqual(result["storyHits"], [])
        self.assertEqual(
            result["namespaceCounts"]["NodeCanvas.BehaviourTrees"], 4
        )

    def test_story_token_in_logical_json_is_reported(self) -> None:
        data = make_container(
            [logical_json({"debug": "cutscene_example_1", "owner": "mission"})]
        )
        result = AUDIT.decode_compress_data(data)
        self.assertEqual(len(result["storyHits"]), 1)
        matches = result["storyHits"][0]["matches"]
        self.assertEqual(matches[0]["storyTokens"], ["cutscene_example_1"])
        self.assertEqual(matches[1]["ownerTerms"], ["mission"])

    def test_bad_compressed_length_fails_closed(self) -> None:
        data = bytearray(make_container([logical_json()]))
        record_offset = struct.unpack_from("<I", data, 4)[0]
        struct.pack_into("<I", data, record_offset, 1)
        with self.assertRaises(AUDIT.AuditError):
            AUDIT.decode_compress_data(bytes(data))


if __name__ == "__main__":
    unittest.main()
