from __future__ import annotations

import base64
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.memorypack import corpus_gate as vfs
from scripts.game_data.memorypack.lipsync import LIPSYNC_FIELD_NAMES
from scripts.game_data.memorypack.lipsync_corpus import (
    _join_and_decode,
    _summary,
    select_rows,
)


INPUT_SET = "A" * 64
PATH = "Data/Json/LipSync/Chinese/fixture.json"


def _payload() -> bytes:
    output = bytearray([len(LIPSYNC_FIELD_NAMES)])
    for index, _name in enumerate(LIPSYNC_FIELD_NAMES):
        if index == 0:
            output.extend(struct.pack("<I", 1))
            output.extend(struct.pack("<I6f", 6, 0.5, 1.0, 0.0, 0.0, 0.0, 0.0))
        else:
            output.extend(struct.pack("<I", 0xFFFFFFFF))
    return bytes(output)


def _ledger_row(data: bytes, *, path: str = PATH, input_set: str = INPUT_SET) -> dict:
    return {
        "recordType": "file",
        "inputSetSha256": input_set,
        "status": "verified",
        "boundaryStatus": "boundary_verified",
        "blockName": "JsonData",
        "blockTypeValue": 19,
        "encrypted": True,
        "virtualPath": path,
        "length": len(data),
        "actualBytesRead": len(data),
        "offset": 0,
        "physicalChunkPath": "fixture.chk",
        "physicalChunkSource": "primary",
        "physicalChunkRoot": "fixture-root",
        "metadataProvenance": "primary",
        "overlayState": "identical",
        "chunkOverlayState": "primary_only",
        "hashDirectory": "01234567",
        "chunkFile": "0123456789ABCDEF0123456789ABCDEF.chk",
        "recomputedFileDataMd5": hashlib.md5(data).hexdigest().upper(),
    }


def _stream_row(data: bytes, *, path: str = PATH) -> dict:
    return {
        "fileName": path,
        "blockType": "JsonData",
        "blockTypeValue": 19,
        "length": len(data),
        "dataBase64": base64.b64encode(data).decode("ascii"),
    }


class LipSyncCorpusGateTests(unittest.TestCase):
    def test_current_stream_row_joins_and_consumes_the_exact_file(self) -> None:
        data = _payload()
        rows = _join_and_decode([_ledger_row(data)], [_stream_row(data)])

        self.assertEqual(1, len(rows))
        self.assertEqual("exact-closed", rows[0]["status"])
        self.assertEqual(len(data), rows[0]["bytesConsumed"])
        self.assertEqual(hashlib.sha256(data).hexdigest().upper(), rows[0]["logicalSha256"])
        self.assertEqual(15, rows[0]["channelCount"])
        self.assertEqual(1, rows[0]["rowCountsByChannel"]["A"])
        self.assertIsNone(rows[0]["rowCountsByChannel"]["E"])
        self.assertEqual(1, _summary(rows)["filesExactClosed"])

    def test_stale_current_ledger_input_set_is_rejected(self) -> None:
        data = _payload()
        row = _ledger_row(data, input_set="B" * 64)
        with tempfile.TemporaryDirectory() as directory:
            chunk = Path(directory) / row["chunkFile"]
            chunk.write_bytes(data)
            row["physicalChunkPath"] = str(chunk)
            with self.assertRaises(vfs.CensusGateError) as caught:
                select_rows([row], expected_input=INPUT_SET)
        self.assertEqual("lipsync-ledger-field-mismatch", caught.exception.diagnostic["code"])
        self.assertIn(PATH, caught.exception.diagnostic["source"])

    def test_logical_md5_mismatch_fails_closed(self) -> None:
        data = _payload()
        ledger = _ledger_row(data)
        ledger["recomputedFileDataMd5"] = "0" * 32

        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_decode([ledger], [_stream_row(data)])
        self.assertEqual("stream-ledger-md5-mismatch", caught.exception.diagnostic["code"])
        self.assertEqual("0" * 32, caught.exception.diagnostic["expected"])

    def test_duplicate_unexpected_and_missing_stream_identities_fail(self) -> None:
        data = _payload()
        ledger = [_ledger_row(data)]
        stream = _stream_row(data)

        with self.assertRaises(vfs.CensusGateError) as duplicate:
            _join_and_decode(ledger, [stream, stream])
        self.assertEqual("duplicate-stream-identity", duplicate.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as unexpected:
            _join_and_decode(ledger, [_stream_row(data, path="Data/Json/LipSync/English/extra.json")])
        self.assertEqual("unexpected-stream-identity", unexpected.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as missing:
            _join_and_decode(ledger, [])
        self.assertEqual("stream-missing-current-identities", missing.exception.diagnostic["code"])

    def test_truncated_current_row_is_not_an_exact_frame(self) -> None:
        data = _payload()[:-1]
        rows = _join_and_decode([_ledger_row(data)], [_stream_row(data)])
        summary = _summary(rows)

        self.assertEqual("failed", rows[0]["status"])
        self.assertEqual("lipsync-framing-failed", rows[0]["diagnostic"]["code"])
        self.assertEqual(1, summary["filesFailed"])
        self.assertEqual(0, summary["filesExactClosed"])
        self.assertIsNotNone(summary["firstFailure"])


if __name__ == "__main__":
    unittest.main()
