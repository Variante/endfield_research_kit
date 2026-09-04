import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.game_data import terrain_corpus


INPUT_SET = "A" * 64
NATIVE_EVIDENCE = {
    "status": "validated",
    "nativeMappingId": "fixture",
    "evidenceBoundary": {
        "exact": "fixture",
        "direct": "fixture",
        "structuralOnly": "fixture",
        "inferred": "fixture",
        "unresolved": "fixture",
    },
}


def tret(words: tuple[int, int, int, int], payload: bytes) -> bytes:
    length = len(payload)
    header_words = (*words, length & 0xFFFF, length >> 16)
    return (
        b"TRET"
        + (1).to_bytes(4, "little")
        + b"".join(value.to_bytes(2, "little") for value in header_words)
        + payload
    )


class TerrainCorpusTests(unittest.TestCase):
    def make_fixture(
        self,
        root: Path,
        raw: bytes,
        *,
        offset: int = 3,
        declared_length: int | None = None,
        expected_input: str = INPUT_SET,
    ) -> tuple[Path, Path]:
        chunk = root / "source.chk"
        chunk.write_bytes(b"pad" + raw)
        length = len(raw) if declared_length is None else declared_length
        ledger = root / "ledger.jsonl.gz"
        header = {
            "recordType": "audit_header",
            "schemaVersion": 1,
            "inputSetSha256": INPUT_SET,
            "primaryAssets": "P:/Persistent",
            "fallbackAssets": "S:/StreamingAssets",
        }
        row = {
            "recordType": "file",
            "inputSetSha256": INPUT_SET,
            "status": "verified",
            "boundaryStatus": "boundary_verified",
            "overlayState": "identical",
            "blockName": "Terrain",
            "blockTypeValue": 22,
            "chunkFile": chunk.name,
            "virtualPath": "Data/Terrain/PC/test/Terrain_0_0_0_H.bytes",
            "offset": offset,
            "length": length,
            "actualBytesRead": length,
            "physicalChunkPath": str(chunk),
            "physicalChunkSource": "fallback",
            "metadataProvenance": "primary",
            "encrypted": False,
            "recomputedFileDataMd5": hashlib.md5(
                raw[:length], usedforsecurity=False
            ).hexdigest().upper(),
        }
        with gzip.open(ledger, "wt", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(header) + "\n")
            stream.write(json.dumps(row) + "\n")
        summary = root / "summary.json"
        summary.write_text(
            json.dumps(
                {
                    "format": "fixture",
                    "inputSetSha256": INPUT_SET,
                    "primaryAssets": header["primaryAssets"],
                    "fallbackAssets": header["fallbackAssets"],
                    "summary": {"fullAuditPassed": True},
                    "publication": {
                        "ledgerSha256": terrain_corpus._sha256_file(ledger)
                    },
                }
            ),
            encoding="utf-8",
        )
        self.expected_input = expected_input
        return summary, ledger

    def run_fixture(self, summary: Path, ledger: Path) -> dict:
        return terrain_corpus.sweep(
            outer_summary_path=summary,
            outer_ledger_path=ledger,
            expected_input_set_sha256=self.expected_input,
            native_evidence=NATIVE_EVIDENCE,
        )

    def test_exact_fixture_reaches_complete_terminal_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = tret((34, 34, 1, 6), b"\x5a" * 2312)
            report = self.run_fixture(*self.make_fixture(root, raw))
            self.assertEqual("complete", report["status"])
            self.assertFalse(report["failed"])
            self.assertEqual(1, report["summary"]["parsedExact"])
            self.assertEqual(1, report["summary"]["exactRanges"])

    def test_truncated_physical_interval_has_path_offset_expected_actual(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = tret((34, 34, 1, 6), b"\x5a" * 2312)
            summary, ledger = self.make_fixture(root, raw, declared_length=len(raw) + 1)
            report = self.run_fixture(summary, ledger)
            self.assertEqual("failed", report["status"])
            self.assertEqual(1, report["summary"]["failed"])
            self.assertEqual(0, report["summary"]["unsupported"])
            failure = report["failures"][0]
            self.assertIn("Terrain_0_0_0_H.bytes", failure["virtualPath"])
            self.assertEqual(3, failure["offset"])
            self.assertEqual(len(raw) + 1, failure["expected"])
            self.assertEqual(len(raw), failure["actual"])

    def test_malformed_layout_count_is_reported_as_parse_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = tret((34, 34, 2, 6), b"\x00" * 2312)
            report = self.run_fixture(*self.make_fixture(root, raw))
            self.assertEqual("failed", report["status"])
            self.assertEqual(0, report["summary"]["failed"])
            self.assertEqual(1, report["summary"]["unsupported"])
            failure = report["failures"][0]
            self.assertEqual("parse", failure["stage"])
            self.assertIn("decoded offset 8", failure["message"])

    def test_trailing_byte_is_not_hidden_by_outer_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = tret((34, 34, 1, 6), b"\x00" * 2312) + b"x"
            report = self.run_fixture(*self.make_fixture(root, raw))
            self.assertEqual("failed", report["status"])
            self.assertIn("decoded offset 16", report["failures"][0]["message"])

    def test_input_set_mismatch_fails_before_claiming_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = tret((34, 34, 1, 6), b"\x00" * 2312)
            summary, ledger = self.make_fixture(
                root, raw, expected_input="B" * 64
            )
            report = self.run_fixture(summary, ledger)
            self.assertEqual("failed", report["status"])
            self.assertEqual(0, report["summary"]["parsedExact"])
            self.assertTrue(
                any(row.get("field") == "inputSetSha256" for row in report["failures"])
            )

    def test_native_contract_failure_closes_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = tret((34, 34, 1, 6), b"\x00" * 2312)
            summary, ledger = self.make_fixture(root, raw)
            report = terrain_corpus.sweep(
                outer_summary_path=summary,
                outer_ledger_path=ledger,
                expected_input_set_sha256=INPUT_SET,
                native_evidence={
                    "status": "validation_failed",
                    "validationFailures": [{"gate": "body_sha256"}],
                },
            )
            self.assertEqual("failed", report["status"])
            self.assertEqual(0, report["summary"]["parsedExact"])
            self.assertEqual("native-contract", report["failures"][0]["stage"])


if __name__ == "__main__":
    unittest.main()
