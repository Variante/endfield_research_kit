import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.streaming_corpus import sweep
from scripts.tests.test_streaming import _info_root, _packed, _parallel_data_root


class StreamingCorpusTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path, str]:
        input_set = "A" * 64
        init = _packed(_parallel_data_root())
        info = _info_root()
        chunk = root / "fixture.chk"
        chunk.write_bytes(init + info)
        header = {
            "recordType": "audit_header",
            "schemaVersion": 1,
            "inputSetSha256": input_set,
            "primaryAssets": "P:/Persistent",
            "fallbackAssets": "F:/StreamingAssets",
        }
        rows = []
        for path, offset, data in (
            (
                "Data/Streaming/PC/test/Streaming/InitChunkData_Global_0_0.bytes",
                0,
                init,
            ),
            (
                "Data/Streaming/PC/test/Streaming/StreamingChunkInfo.bytes",
                len(init),
                info,
            ),
        ):
            rows.append(
                {
                    "recordType": "file",
                    "inputSetSha256": input_set,
                    "status": "verified",
                    "boundaryStatus": "boundary_verified",
                    "blockTypeValue": 15,
                    "virtualPath": path,
                    "offset": offset,
                    "length": len(data),
                    "actualBytesRead": len(data),
                    "physicalChunkPath": str(chunk),
                    "physicalChunkSource": "fallback",
                    "metadataProvenance": "primary",
                    "overlayState": "identical",
                    "chunkFile": chunk.name,
                    "encrypted": False,
                    "recomputedFileDataMd5": hashlib.md5(
                        data, usedforsecurity=False
                    ).hexdigest().upper(),
                }
            )
        ledger = root / "ledger.jsonl.gz"
        with gzip.open(ledger, "wt", encoding="utf-8", newline="\n") as stream:
            for row in (header, *rows):
                stream.write(json.dumps(row) + "\n")
        ledger_sha256 = hashlib.sha256(ledger.read_bytes()).hexdigest().upper()
        summary = root / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "format": "animestudio-vfs-boundary-audit",
                    "inputSetSha256": input_set,
                    "primaryAssets": header["primaryAssets"],
                    "fallbackAssets": header["fallbackAssets"],
                    "summary": {"fullAuditPassed": True},
                    "publication": {"ledgerSha256": ledger_sha256},
                }
            ),
            encoding="utf-8",
        )
        return summary, ledger, chunk, input_set

    def test_complete_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, _chunk, input_set = self._fixture(Path(temporary))
            result = sweep(
                outer_summary_path=summary,
                outer_ledger_path=ledger,
                expected_input_set_sha256=input_set,
            )
        self.assertEqual(result["status"], "complete")
        self.assertFalse(result["failed"])
        self.assertEqual(result["summary"]["parsed"], 2)
        self.assertEqual(result["summary"]["exactInfo"], 1)
        self.assertEqual(result["summary"]["partialData"], 1)
        self.assertEqual(
            result["layer3"]["field2DirectSubgraphStatus"],
            "exact_anonymous_direct_subgraph",
        )
        self.assertEqual(result["layer3"]["field2DirectRowCount"], 0)
        self.assertEqual(result["layer3"]["field2InitEmptyVectorAtEofFiles"], 1)
        self.assertEqual(result["layer3"]["parallelRowCount"], 2)
        self.assertEqual(result["layer3"]["field5Field0ReferenceCount"], 2)
        self.assertEqual(result["layer3"]["field5Field0Representation"], "ambiguous")

    def test_stale_input_set_fails_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, _chunk, _input_set = self._fixture(Path(temporary))
            result = sweep(
                outer_summary_path=summary,
                outer_ledger_path=ledger,
                expected_input_set_sha256="B" * 64,
            )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["failed"])
        self.assertTrue(
            any(item.get("field") == "inputSetSha256" for item in result["failures"])
        )

    def test_physical_hash_mismatch_reports_file_and_offset(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, chunk, input_set = self._fixture(Path(temporary))
            data = bytearray(chunk.read_bytes())
            data[0] ^= 0xFF
            chunk.write_bytes(data)
            result = sweep(
                outer_summary_path=summary,
                outer_ledger_path=ledger,
                expected_input_set_sha256=input_set,
            )
        self.assertEqual(result["status"], "failed")
        failure = next(
            item for item in result["failures"] if item.get("stage") == "physical-hash"
        )
        self.assertIn("InitChunkData", failure["virtualPath"])
        self.assertEqual(failure["offset"], 0)
        self.assertNotEqual(failure["expected"], failure["actual"])

    def test_invalid_expected_hash_fails_closed(self):
        result = sweep(
            outer_summary_path=Path("missing"),
            outer_ledger_path=Path("missing"),
            expected_input_set_sha256="not-a-sha",
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["summary"]["gateFailures"], 1)


if __name__ == "__main__":
    unittest.main()
