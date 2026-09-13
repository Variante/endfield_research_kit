from __future__ import annotations

import base64
import hashlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.game_data.memorypack import corpus_gate as vfs
from scripts.game_data.memorypack import npc_montage_corpus as corpus
from scripts.game_data.memorypack.npc_montage import NPC_MONTAGE_RELATIVE_PREFIX
from scripts.game_data.memorypack.npc_montage_corpus import _join_and_frame, _summary, select_rows


INPUT_SET = "A" * 64
VIRTUAL_PATH = NPC_MONTAGE_RELATIVE_PREFIX + "Generic/test.json"


def _minimal_empty_frame() -> bytes:
    """A valid exact frame with both counted collections empty."""
    out = bytearray((3,))
    out.extend(struct.pack("<i", 1))
    out.append(24)
    out.extend(b"\x00\x00")
    out.append(0xFF)  # Null ClipInfo.
    out.extend(struct.pack("<I", 0))  # data.member3 count.
    out.extend(b"\x00\x00")
    out.extend(bytes(36))
    out.append(0)
    out.extend(struct.pack("<ffii", 0.0, 0.0, 0, 0))
    out.extend(bytes(8 + 16))
    out.extend(struct.pack("<f", 0.0))
    out.extend(bytes(36))
    out.extend(struct.pack("<i", 0))
    out.extend(bytes(32))
    out.extend(struct.pack("<I", 0))  # data.member18 count.
    out.extend(struct.pack("<if", 0, 0.0))
    out.extend(bytes(36 + 16 + 8))
    out.extend(struct.pack("<i", 0))  # root.member2.
    return bytes(out)


class NpcMontageCorpusGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = _minimal_empty_frame()
        self.chunk = Path(self.temp.name) / "physical.chk"
        self.chunk.write_bytes(self.data)
        self.ledger = {
            "recordType": "file",
            "inputSetSha256": INPUT_SET,
            "virtualPath": VIRTUAL_PATH,
            "status": "verified",
            "boundaryStatus": "boundary_verified",
            "blockName": "JsonData",
            "blockTypeValue": 19,
            "encrypted": True,
            "length": len(self.data),
            "actualBytesRead": len(self.data),
            "offset": 0,
            "physicalChunkPath": str(self.chunk),
            "physicalChunkSource": "fallback",
            "metadataProvenance": "primary",
            "overlayState": "identical",
            "chunkOverlayState": "fallback_only",
            "hashDirectory": "AABBCCDD",
            "chunkFile": "11223344556677889900AABBCCDDEEFF.chk",
            "recomputedFileDataMd5": hashlib.md5(self.data).hexdigest().upper(),
        }
        self.stream = {
            "fileName": VIRTUAL_PATH,
            "blockType": "JsonData",
            "blockTypeValue": 19,
            "length": len(self.data),
            "dataBase64": base64.b64encode(self.data).decode("ascii"),
        }

    def _census_fixture(self, extra_rows: list[dict] | None = None):
        root = Path(self.temp.name)
        primary = root / "primary"
        fallback = root / "fallback"
        primary.mkdir()
        fallback.mkdir()
        cli = root / "AnimeStudio.CLI.exe"
        cli.write_bytes(b"test cli fingerprint")
        outer_path = root / "outer.json"
        ledger_path = root / "ledger.jsonl.gz"
        outer_path.write_bytes(b"test outer")
        ledger_path.write_bytes(b"test ledger")
        output_dir = root / "reports"
        output_dir.mkdir()
        outer = {"primaryAssets": str(primary), "fallbackAssets": str(fallback)}
        provenance = {
            "outer": {"path": str(outer_path.resolve()), "length": 10, "sha256": "A" * 64},
            "ledger": {"path": str(ledger_path.resolve()), "length": 11, "sha256": "B" * 64},
            "sourceFingerprints": [],
            "buildFingerprints": [{"path": str(cli.resolve()), "sha256": "C" * 64}],
            "blcPaths": [],
        }
        rows = [self.ledger, *(extra_rows or [])]
        return outer, outer_path, ledger_path, cli, output_dir, rows, provenance

    def _patch_census(self, outer, rows, provenance):
        loaded = (outer, {}, rows, provenance)
        return (
            patch.object(vfs, "_read_outer_and_ledger", side_effect=[loaded, loaded]),
            patch.object(vfs, "_chunk_selection_snapshot", return_value=[]),
            patch.object(corpus, "_iter_stream_rows", side_effect=lambda _command: iter([self.stream])),
        )

    def test_current_family_selection_requires_current_verified_rows(self) -> None:
        selected = select_rows([self.ledger], expected_input=INPUT_SET)
        self.assertEqual([VIRTUAL_PATH], [row["virtualPath"] for row in selected])

        with self.assertRaises(vfs.CensusGateError) as caught:
            select_rows([self.ledger], expected_input="B" * 64)
        self.assertEqual("npc-montage-ledger-field-mismatch", caught.exception.diagnostic["code"])

        non_json = dict(self.ledger, virtualPath=NPC_MONTAGE_RELATIVE_PREFIX + "Generic/test.bytes")
        with self.assertRaises(vfs.CensusGateError) as caught:
            select_rows([non_json], expected_input=INPUT_SET)
        self.assertEqual("unsupported-npc-montage-path", caught.exception.diagnostic["code"])

    def test_authenticated_stream_row_frames_exactly_to_eof(self) -> None:
        selected = select_rows([self.ledger], expected_input=INPUT_SET)
        rows = _join_and_frame(selected, [self.stream], expected_input=INPUT_SET)

        self.assertEqual(1, len(rows))
        self.assertEqual("success", rows[0]["status"])
        self.assertEqual("exact-closed", rows[0]["boundaryClass"])
        self.assertEqual(len(self.data), rows[0]["bytesConsumed"])
        self.assertEqual(hashlib.sha256(self.data).hexdigest().upper(), rows[0]["logicalSha256"])
        summary = _summary(rows)
        self.assertEqual(1, summary["filesExactClosed"])
        self.assertEqual(0, summary["filesUnsupported"])
        self.assertEqual(0, summary["filesAmbiguous"])
        self.assertEqual(0, summary["filesFailed"])
        self.assertIsNone(summary["firstIssue"])

    def test_stream_identity_duplicates_missing_rows_and_md5_drift_fail_closed(self) -> None:
        selected = select_rows([self.ledger], expected_input=INPUT_SET)
        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame(selected, [dict(self.stream, fileName="Data/Json/other.json")], expected_input=INPUT_SET)
        self.assertEqual("unexpected-stream-identity", caught.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame(selected, [self.stream, self.stream], expected_input=INPUT_SET)
        self.assertEqual("duplicate-stream-identity", caught.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame(selected, [], expected_input=INPUT_SET)
        self.assertEqual("stream-missing-current-identities", caught.exception.diagnostic["code"])

        changed = dict(self.stream, dataBase64=base64.b64encode(self.data + b"\x00").decode("ascii"), length=len(self.data) + 1)
        # A byte-count drift is rejected before any parser result is produced.
        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame(selected, [changed], expected_input=INPUT_SET)
        self.assertEqual("stream-length-mismatch", caught.exception.diagnostic["code"])

        wrong_md5 = dict(self.ledger, recomputedFileDataMd5="0" * 32)
        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame([wrong_md5], [self.stream], expected_input=INPUT_SET)
        self.assertEqual("stream-ledger-md5-mismatch", caught.exception.diagnostic["code"])

    def test_stream_block_type_and_invalid_base64_fail_closed(self) -> None:
        selected = select_rows([self.ledger], expected_input=INPUT_SET)
        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame(
                selected,
                [dict(self.stream, blockType="Texture2D")],
                expected_input=INPUT_SET,
            )
        self.assertEqual("stream-block-mismatch", caught.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as caught:
            _join_and_frame(
                selected,
                [dict(self.stream, dataBase64="!!!")],
                expected_input=INPUT_SET,
            )
        self.assertEqual("stream-base64-invalid", caught.exception.diagnostic["code"])

    def test_stream_jsonl_reader_rejects_invalid_rows_and_process_failure(self) -> None:
        rows = list(corpus._iter_stream_rows([
            sys.executable,
            "-c",
            "import json; print(json.dumps({'ok': True}))",
        ]))
        self.assertEqual([{"ok": True}], rows)

        with self.assertRaises(vfs.CensusGateError) as caught:
            list(corpus._iter_stream_rows([sys.executable, "-c", "print('{')"]))
        self.assertEqual("stream-json-invalid", caught.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as caught:
            list(corpus._iter_stream_rows([sys.executable, "-c", "print('[]')"]))
        self.assertEqual("stream-row-not-object", caught.exception.diagnostic["code"])

        with self.assertRaises(vfs.CensusGateError) as caught:
            list(corpus._iter_stream_rows([
                sys.executable,
                "-c",
                "import json,sys; print(json.dumps({'ok': True})); sys.exit(7)",
            ]))
        self.assertEqual("stream-process-failed", caught.exception.diagnostic["code"])

    def test_census_protects_unselected_ledger_chunks_from_output_paths(self) -> None:
        outside_chunk = Path(self.temp.name) / "unselected" / "outside.chk"
        outside_chunk.parent.mkdir()
        outside_chunk.write_bytes(b"unselected physical input")
        unselected = dict(
            self.ledger,
            virtualPath="Data/Json/Other/unselected.json",
            physicalChunkPath=str(outside_chunk),
        )
        outer, outer_path, ledger_path, cli, output_dir, rows, provenance = self._census_fixture([unselected])
        output_md = output_dir / "report.md"
        read_patch, selection_patch, stream_patch = self._patch_census(outer, rows, provenance)
        with read_patch, selection_patch, stream_patch:
            with self.assertRaises(vfs.CensusGateError) as caught:
                corpus.build_current_census(
                    outer_path=outer_path,
                    ledger_path=ledger_path,
                    cli_path=cli,
                    expected_input_set_sha256=INPUT_SET,
                    output_json=outside_chunk,
                    output_md=output_md,
                )
        self.assertEqual("output-overlaps-input", caught.exception.diagnostic["code"])

    def test_census_rejects_selected_chunk_fingerprint_drift(self) -> None:
        outer, outer_path, ledger_path, cli, output_dir, rows, provenance = self._census_fixture()
        chunk_fingerprints = [
            [{"path": str(self.chunk.resolve()), "sha256": "1" * 64}],
            [{"path": str(self.chunk.resolve()), "sha256": "2" * 64}],
        ]
        read_patch, selection_patch, stream_patch = self._patch_census(outer, rows, provenance)
        with read_patch, selection_patch, stream_patch, \
             patch.object(vfs, "_chunk_fingerprints", side_effect=chunk_fingerprints):
            with self.assertRaises(vfs.CensusGateError) as caught:
                corpus.build_current_census(
                    outer_path=outer_path,
                    ledger_path=ledger_path,
                    cli_path=cli,
                    expected_input_set_sha256=INPUT_SET,
                    output_json=output_dir / "report.json",
                    output_md=output_dir / "report.md",
                )
        self.assertEqual("current-input-drift", caught.exception.diagnostic["code"])

    def test_unrecognized_current_shape_is_unsupported_and_never_exact(self) -> None:
        selected = select_rows([self.ledger], expected_input=INPUT_SET)
        unsupported_bytes = b"\x02" + self.data[1:]
        self.chunk.write_bytes(unsupported_bytes)
        unsupported_ledger = dict(
            self.ledger,
            length=len(unsupported_bytes),
            actualBytesRead=len(unsupported_bytes),
            recomputedFileDataMd5=hashlib.md5(unsupported_bytes).hexdigest().upper(),
        )
        unsupported_stream = dict(
            self.stream,
            length=len(unsupported_bytes),
            dataBase64=base64.b64encode(unsupported_bytes).decode("ascii"),
        )
        rows = _join_and_frame([unsupported_ledger], [unsupported_stream], expected_input=INPUT_SET)

        self.assertEqual("unsupported", rows[0]["status"])
        self.assertEqual("unsupported", rows[0]["boundaryClass"])
        self.assertIsNone(rows[0]["bytesConsumed"])
        self.assertEqual(VIRTUAL_PATH, rows[0]["diagnostic"]["source"])
        self.assertEqual(INPUT_SET, rows[0]["diagnostic"]["inputSetSha256"])
        self.assertEqual(rows[0]["logicalSha256"], rows[0]["diagnostic"]["logicalSha256"])
        summary = _summary(rows)
        self.assertEqual(0, summary["filesExactClosed"])
        self.assertEqual(1, summary["filesUnsupported"])
        self.assertEqual(0, summary["filesFailed"])
        self.assertEqual("npc-montage-frame-not-closed", summary["firstIssue"]["code"])


if __name__ == "__main__":
    unittest.main()
