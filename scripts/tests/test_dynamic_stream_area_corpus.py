from __future__ import annotations

import base64
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.dynamic_stream_area_corpus import (
    load_current_inputs,
    validate_stream_output,
)


INPUT_SET = "A" * 64
FILE_PATH = "Data/DynamicStreaming/PC/Scene/fixture/FBStreamArea.bytes"


def _fixture() -> bytes:
    return bytes.fromhex(
        "1800000000001200340004000c000800"
        "1c001800100014001200000030000000"
        "34000000340000003c00000034000000"
        "380000000050c3470050c3470050c3c7"
        "0050c3c70050c3470050c3c701000000"
        "00000000000000000100000000000000"
        "000000000000000000000000"
    )


def _ledger_identity(data: bytes = _fixture()) -> dict:
    return {
        "block": "DynamicStreaming",
        "path": FILE_PATH,
        "declaredBytes": len(data),
        "fileDataMd5": hashlib.md5(data).hexdigest().upper(),
        "chunk": "fixture.chk",
        "source": "fixture.blc",
    }


def _stream_line(
    data: bytes = _fixture(), *, path: str = FILE_PATH, block_type_value: int = 16
) -> bytes:
    return (
        json.dumps(
            {
                "blockType": "DynamicStreaming",
                "blockTypeValue": block_type_value,
                "fileName": path,
                "length": len(data),
                "dataBase64": base64.b64encode(data).decode("ascii"),
            }
        ).encode("utf-8")
        + b"\r\n"
    )


class DynamicStreamAreaCorpusTests(unittest.TestCase):
    def test_exact_stream_rows_match_ledger_hash_and_frame_to_eof(self) -> None:
        files, summary = validate_stream_output([_ledger_identity()], _stream_line(), 16)

        self.assertEqual(1, summary["fileCount"])
        self.assertEqual(1, summary["finalVectorReachesPayloadEofCount"])
        self.assertEqual(len(_fixture()), summary["sourceBytes"])
        self.assertTrue(files[0]["finalVectorReachesPayloadEof"])
        self.assertEqual(len(_fixture()), files[0]["finalVectorEndOffset"])

    def test_stream_filedata_md5_mismatch_fails_with_path(self) -> None:
        ledger = _ledger_identity()
        ledger["fileDataMd5"] = "0" * 32

        with self.assertRaisesRegex(ValueError, "FileDataMd5 mismatch.*FBStreamArea"):
            validate_stream_output([ledger], _stream_line(), 16)

    def test_stream_block_value_and_file_set_must_match_outer_ledger(self) -> None:
        with self.assertRaisesRegex(ValueError, "wrong DynamicStreaming block value"):
            validate_stream_output([_ledger_identity()], _stream_line(block_type_value=15), 16)

        other = _ledger_identity()
        other["path"] = "Data/DynamicStreaming/PC/Scene/other/FBStreamArea.bytes"
        with self.assertRaisesRegex(ValueError, "omitted current ledger files"):
            validate_stream_output([_ledger_identity(), other], _stream_line(), 16)

    def test_stream_parser_rejects_a_ledger_matched_trailing_byte(self) -> None:
        data = _fixture() + b"\x00"

        with self.assertRaisesRegex(ValueError, "parser rejected.*expected payload EOF"):
            validate_stream_output([_ledger_identity(data)], _stream_line(data), 16)

    def test_outer_gate_authenticates_ledger_and_source_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            fallback = root / "fallback"
            primary.mkdir()
            fallback.mkdir()
            source = root / "chunk.blc"
            source.write_bytes(b"authenticated fixture source")
            cli = root / "AnimeStudio.CLI.exe"
            cli.write_bytes(b"authenticated fixture CLI")
            game_binary = root / "Endfield.exe"
            game_binary.write_bytes(b"pinned game binary")
            data = _fixture()
            row = {
                "recordType": "file",
                "inputSetSha256": INPUT_SET,
                "blockName": "DynamicStreaming",
                "virtualPath": FILE_PATH,
                "length": len(data),
                "actualBytesRead": len(data),
                "boundaryStatus": "boundary_verified",
                "declaredFileDataMd5LittleEndianHex": hashlib.md5(data).hexdigest().upper(),
                "recomputedFileDataMd5": hashlib.md5(data).hexdigest().upper(),
                "chunkFile": "fixture.chk",
                "physicalChunkPath": str(source),
            }
            ledger_path = root / "ledger.jsonl.gz"
            with gzip.open(ledger_path, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
            outer = {
                "format": "animestudio-vfs-boundary-audit",
                "schemaVersion": 1,
                "inputSetSha256": INPUT_SET,
                "primaryAssets": str(primary),
                "fallbackAssets": str(fallback),
                "summary": {
                    "fullAuditPassed": True,
                    "allAvailableBoundaryVerified": True,
                    "failureCount": 0,
                    "terminalCountsReconciled": True,
                    "availableCountsReconciled": True,
                    "ledgerFileCount": 1,
                },
                "sourceFingerprints": [
                    {
                        "path": str(source),
                        "length": source.stat().st_size,
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest().upper(),
                    }
                ],
                "buildFingerprints": [
                    {
                        "path": str(cli),
                        "length": cli.stat().st_size,
                        "sha256": hashlib.sha256(cli.read_bytes()).hexdigest().upper(),
                    },
                    {
                        "path": str(game_binary),
                        "length": game_binary.stat().st_size,
                        "sha256": hashlib.sha256(game_binary.read_bytes()).hexdigest().upper(),
                    },
                ],
                "publication": {
                    "ledgerSha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()
                },
            }
            outer_path = root / "outer.json"
            outer_path.write_text(json.dumps(outer), encoding="utf-8")

            _, files, provenance = load_current_inputs(outer_path, ledger_path, cli, INPUT_SET)

            self.assertEqual(1, len(files))
            self.assertEqual(1, len(provenance["sourceFingerprints"]))
            self.assertEqual(1, len(provenance["gameBuildFingerprints"]))
            self.assertTrue(provenance["streamCliFingerprint"]["matchesOuterAudit"])
            with self.assertRaisesRegex(ValueError, "input-set mismatch"):
                load_current_inputs(outer_path, ledger_path, cli, "B" * 64)

            cli.write_bytes(b"x" * cli.stat().st_size)
            _, _, provenance = load_current_inputs(outer_path, ledger_path, cli, INPUT_SET)
            self.assertFalse(provenance["streamCliFingerprint"]["matchesOuterAudit"])

            source.write_bytes(b"x" * source.stat().st_size)
            with self.assertRaisesRegex(ValueError, "source SHA-256 mismatch"):
                load_current_inputs(outer_path, ledger_path, cli, INPUT_SET)


if __name__ == "__main__":
    unittest.main()
