import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.game_data.streaming_corpus import sweep
from scripts.tests.test_streaming import (
    _field2_streaming_full_layout_root,
    _info_root,
    _packed,
    _parallel_target_data_root,
    _selector5_data_root,
)


class StreamingCorpusTests(unittest.TestCase):
    @staticmethod
    def _sweep(**kwargs):
        native = {
            "status": "validated",
            "rowLayout": [
                {"fieldIndex": 0, "representation": "little-endian-scalar32"},
                {"fieldIndex": 1, "representation": "little-endian-scalar32"},
                {"fieldIndex": 2, "representation": "little-endian-scalar32"},
                {"fieldIndex": 3, "representation": "little-endian-int32[2]"},
                {"fieldIndex": 4, "representation": "little-endian-float32[6]"},
                {
                    "fieldIndex": 5,
                    "representation": "count-prefixed-little-endian-scalar32[]",
                },
            ],
            "carrierObservations": {
                "baseLengthStatus": "exact-selected-build-family-level-native-carrier",
                "staticFirstReadLeaf": "StreamingChunkInfo",
                "logicalFileJoinStatus": "bounded-authenticated-candidates-no-concrete-runtime-root",
                "finalCursorStatus": "exact-selected-closure-pointer-only-no-final-cursor",
                "rowConsumerCarrierJoinStatus": "exact-static-object-chain-concrete-create-instance-unresolved",
                "rowConsumerRuntimeHandleRepresentation": "anonymous-little-endian-dword[4]",
            },
            "validationFailures": [],
            "nestedContextObservations": {
                "status": "direct-static-root-field5-row-field3-to-context",
                "marker15SelectionStatus": "unresolved",
                "recordExtentStatus": "unresolved",
            },
            "nestedReaderPhaseObservations": {
                "status": "direct-conditional-default-selector5-later-reader",
                "sourceRoot": "second-secondary-root",
                "marker15WidthStatus": "unresolved",
                "targetOwnedBytes": 0,
            },
        }
        with patch(
            "scripts.game_data.streaming_corpus.validate_streaming_field2_native_contract",
            return_value=native,
        ):
            return sweep(**kwargs)

    def _fixture(self, root: Path, *, selector5: bool = False) -> tuple[Path, Path, Path, str]:
        input_set = "A" * 64
        init_clear = bytearray(_parallel_target_data_root())
        init_clear[236] = 15
        if selector5:
            init_clear = bytearray(_selector5_data_root())
        init = _packed(bytes(init_clear))
        streaming_clear = bytearray(_field2_streaming_full_layout_root())
        streaming_clear[128:132] = (7).to_bytes(4, "little")
        streaming_clear[132:136] = (9).to_bytes(4, "little")
        streaming_clear[136:140] = (-160).to_bytes(4, "little", signed=True)
        streaming_clear[140:144] = (416).to_bytes(4, "little", signed=True)
        streaming = _packed(bytes(streaming_clear))
        info = _info_root()
        chunk = root / "fixture.chk"
        chunk.write_bytes(init + streaming + info)
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
                "Data/Streaming/PC/test/Streaming/StreamingChunkData_-2_3_7_9.bytes",
                len(init),
                streaming,
            ),
            (
                "Data/Streaming/PC/test/Streaming/StreamingChunkInfo.bytes",
                len(init) + len(streaming),
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

    def test_selector5_ranges_keep_source_identity_without_runtime_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, _chunk, input_set = self._fixture(Path(temporary), selector5=True)
            result = self._sweep(outer_summary_path=summary, outer_ledger_path=ledger,
                                 expected_input_set_sha256=input_set)
        self.assertEqual(result['status'], 'complete')
        joined = result['layer3']['selector5KeyRangeJoin']
        self.assertEqual(joined['rowCount'], 1)
        self.assertEqual(joined['elementRangeCount'], 1)
        self.assertEqual(joined['candidateReadBytes'], 20)
        self.assertEqual(joined['targetOwnedBytes'], 0)
        self.assertEqual(joined['files'][0]['physicalChunkSource'], 'fallback')
        self.assertEqual(len(joined['files'][0]['packedSha256']), 64)
        self.assertEqual(joined['files'][0]['rows'][0]['countValue'], 1)

    def test_complete_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, _chunk, input_set = self._fixture(Path(temporary))
            result = self._sweep(
                outer_summary_path=summary,
                outer_ledger_path=ledger,
                expected_input_set_sha256=input_set,
            )
        self.assertEqual(result["status"], "complete")
        self.assertFalse(result["failed"])
        self.assertEqual(result["summary"]["parsed"], 3)
        self.assertEqual(result["summary"]["exactInfo"], 1)
        self.assertEqual(result["summary"]["partialData"], 2)
        self.assertEqual(
            result["layer3"]["field2TerminalSubgraphStatus"],
            "exact_anonymous_eof_subgraph",
        )
        self.assertEqual(result["layer3"]["field2DirectRowCount"], 1)
        self.assertEqual(result["layer3"]["field2Field5VectorCount"], 1)
        self.assertEqual(result["layer3"]["field2Field5ValueCount"], 2)
        self.assertEqual(
            result["layer3"]["field2RowObjectPartitionStatus"],
            "exact-anonymous-slot-spans",
        )
        self.assertEqual(
            [
                item["slotToNextBoundaryBytes"]
                for item in result["layer3"]["field2RowSlotSpans"]
            ],
            [4, 4, 4, 8, 24, 4],
        )
        self.assertEqual(
            result["layer3"]["field2RowSlotSpansMayContainPadding"],
            [],
        )
        self.assertEqual(
            result["layer3"]["field2Rows0To4RepresentationStatus"],
            "exact-selected-build-native-loads",
        )
        self.assertEqual(
            result["layer3"]["field2Rows0To5RepresentationStatus"],
            "exact-selected-build-native-loads",
        )
        self.assertEqual(
            result["layer3"]["field2Field5ValuesStatus"],
            "exact-anonymous-selected-build-native-scalar32-keys",
        )
        self.assertEqual(
            result["layer3"]["field2Field5Scalar32Stats"],
            {
                "minimum": 50462976,
                "maximum": 117835012,
                "zeroCount": 0,
                "highBitSetCount": 0,
                "strictlyIncreasingRowCount": 1,
                "notStrictlyIncreasingRowCount": 0,
                "duplicateWithinRowCount": 0,
                "orderedValuesSha256": hashlib.sha256(
                    (2).to_bytes(4, "little") + bytes(range(8))
                )
                .hexdigest()
                .upper(),
                "status": "current-corpus-structural-statistics",
            },
        )
        self.assertEqual(result["layer3"]["field2InitEmptyVectorAtEofFiles"], 1)
        numeric = result["layer3"]["field2PathRelations"]["numericPattern"]
        self.assertEqual(numeric["fileCount"], 1)
        self.assertEqual(numeric["rowCount"], 1)
        self.assertEqual(numeric["field1PresentAndToken2Match"], 1)
        self.assertEqual(numeric["field2PresentAndToken3Match"], 1)
        self.assertEqual(numeric["field3FloorDiv128BothLanesMatch"], 1)
        self.assertEqual(numeric["field3ResidualValues"], [32, 96])
        self.assertEqual(result["layer3"]["parallelRowCount"], 1)
        self.assertEqual(result["layer3"]["field5Field0ReferenceCount"], 1)
        self.assertEqual(result["layer3"]["field5Field0Representation"], "ambiguous")
        self.assertEqual(result["layer3"]["parallelField5Field5VectorCount"], 1)
        self.assertEqual(result["layer3"]["parallelField5Field5ValueCount"], 0)
        self.assertEqual(
            result["layer3"]["parallelField5Field3NestedTableCount"], 1
        )
        self.assertEqual(
            result["layer3"]["parallelField5Field3NestedParallelCount"], 2
        )
        framing = result["layer3"]["nestedElementFraming"]
        self.assertEqual(framing["nestedElementFramedCounts"], {"17": 1})
        self.assertEqual(framing["nestedElementByteCounts"], {"17": 4})
        self.assertEqual(framing["opaqueElementCount"], 1)
        refs15 = result["layer3"]["nestedMarker15ReferenceBounds"]
        self.assertEqual(refs15["referenceCount"], 1)
        self.assertEqual(refs15["filesWithReferences"], 1)
        self.assertEqual(refs15["widthStatus"], "unresolved")
        self.assertEqual(refs15["targetOwnedBytes"], 0)
        context = result["layer4"]["nestedContextStaticChain"]
        self.assertEqual(context["status"], "direct-static-root-field5-row-field3-to-context")
        self.assertEqual(context["marker15SelectionStatus"], "unresolved")
        self.assertEqual(context["recordExtentStatus"], "unresolved")
        phase = result["layer4"]["nestedReaderPhaseStaticChain"]
        self.assertEqual(phase["sourceRoot"], "second-secondary-root")
        self.assertEqual(phase["marker15WidthStatus"], "unresolved")
        self.assertEqual(phase["targetOwnedBytes"], 0)
        join = result["layer3"]["rootMarkerRowShapeJoin"]
        self.assertEqual(join["status"], "exact-same-vector-index")
        self.assertEqual(join["counts"], {"[2,6,40,[0,1,2,3,4,5]]": 1})
        self.assertEqual(refs15["files"][0]["referenceCount"], 1)
        self.assertEqual(refs15["files"][0]["offset"], 0)
        self.assertEqual(len(refs15["files"][0]["packedSha256"]), 64)
        self.assertEqual(len(refs15["files"][0]["orderedSlotTargetSha256"]), 64)
        self.assertEqual(
            result["layer4"]["nativeCarrierStatus"],
            "exact-selected-build-family-level-native-carrier",
        )
        self.assertEqual(
            result["layer4"]["nativeFinalCursorStatus"],
            "exact-selected-closure-pointer-only-no-final-cursor",
        )
        self.assertEqual(
            result["layer4"]["nativeStaticFirstReadLeaf"], "StreamingChunkInfo"
        )

    def test_stale_input_set_fails_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, _chunk, _input_set = self._fixture(Path(temporary))
            result = self._sweep(
                outer_summary_path=summary,
                outer_ledger_path=ledger,
                expected_input_set_sha256="B" * 64,
            )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["failed"])
        self.assertTrue(
            any(item.get("field") == "inputSetSha256" for item in result["failures"])
        )
        self.assertEqual(
            result["layer3"]["field2RowObjectPartitionStatus"], "unvalidated"
        )
        self.assertEqual(result["layer3"]["field2Rows0To4Status"], "unvalidated")
        self.assertEqual(result["layer3"]["field2Rows0To5Status"], "unvalidated")
        self.assertEqual(result["layer3"]["nestedMarker15ReferenceBounds"]["status"], "unvalidated")
        self.assertIsNone(result["layer4"]["nestedContextStaticChain"])
        self.assertIsNone(result["layer4"]["nestedReaderPhaseStaticChain"])
        self.assertIsNone(result["layer4"]["nestedKeyIndexStaticChain"])
        self.assertEqual(result['layer3']['selector5KeyRangeJoin']['status'], 'unvalidated')
        self.assertEqual(result['layer3']['selector5KeyRangeJoin']['files'], [])
        self.assertEqual(result["layer3"]["rootMarkerRowShapeJoin"]["status"], "unvalidated")
        self.assertEqual(result["layer3"]["rootMarkerRowShapeJoin"]["counts"], {})
        self.assertEqual(
            {item["status"] for item in result["layer3"]["field2RowSlotSpans"]},
            {"unvalidated"},
        )

    def test_physical_hash_mismatch_reports_file_and_offset(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, chunk, input_set = self._fixture(Path(temporary))
            data = bytearray(chunk.read_bytes())
            data[0] ^= 0xFF
            chunk.write_bytes(data)
            result = self._sweep(
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
        result = self._sweep(
            outer_summary_path=Path("missing"),
            outer_ledger_path=Path("missing"),
            expected_input_set_sha256="not-a-sha",
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["summary"]["gateFailures"], 1)

    def test_native_contract_failure_blocks_representation_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary, ledger, _chunk, input_set = self._fixture(Path(temporary))
            with patch(
                "scripts.game_data.streaming_corpus.validate_streaming_field2_native_contract",
                return_value={
                    "status": "validation_failed",
                    "validationFailures": [
                        {
                            "gate": "field3AccessorThunk.body_sha256",
                            "expected": "expected-body",
                            "actual": "changed-body",
                        }
                    ],
                },
            ):
                result = sweep(
                    outer_summary_path=summary,
                    outer_ledger_path=ledger,
                    expected_input_set_sha256=input_set,
                )
        self.assertEqual("failed", result["status"])
        self.assertEqual("unvalidated", result["layer3"]["field2Rows0To4RepresentationStatus"])
        self.assertEqual("unvalidated", result["layer3"]["field2Rows0To5RepresentationStatus"])
        self.assertEqual("unvalidated", result["layer3"]["field2Field5ValuesStatus"])
        self.assertEqual([], result["layer3"]["field2RowFieldRepresentations"])
        self.assertTrue(
            any(
                failure.get("stage") == "native-provenance"
                for failure in result["failures"]
            )
        )


if __name__ == "__main__":
    unittest.main()
