"""End-to-end packed-byte/pair composition without mocking either parser."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.game_data import streaming_marker2_corpus as gate
from scripts.tests.test_streaming import _packed
from scripts.tests.test_streaming_marker2 import fixture as marker2_fixture
from scripts.tests.test_streaming_marker13_corpus import Fixture, INPUT_SET, ROOT, write_json


class ActualPairCompositionTests(unittest.TestCase):
    def test_actual_two_file_pair_and_forged_first_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            for root in (fixture.primary, fixture.fallback):
                (Path(root) / "VFS").mkdir(parents=True)
            fixture.fingerprint = Path(fixture.primary) / "VFS/source.blc"
            fixture.fingerprint.write_bytes(b"source")
            clear, _parsed, _context = marker2_fixture(gap=6, word=0xFFFFFFFF)
            fixture.clear = _packed(clear)
            streaming = fixture.make_file("pair", 0)
            init = {**streaming, "virtualPath": streaming["virtualPath"].replace(
                "/StreamingChunkData_", "/InitChunkData_")}
            fixture.files = [init, streaming]
            fixture.write_all()
            document = json.loads(fixture.report.read_text())
            records = []
            for row in fixture.files:
                parsed = gate.fmt.parse_streaming_file(
                    gate.root_corpus._family(row["virtualPath"]), fixture.clear,
                    native_layout_validated=True, include_certified_ranges=True,
                )
                records.append({**row, "packedSha256": gate.shared.sha256_bytes(fixture.clear),
                                "witness": parsed["anonymousParallelSubgraph"]["orderedRootWitness"]})
            document["layer3"]["pairedRootIdentities"] = gate.root_corpus._join_root_witnesses(records)
            document["layer3"]["nestedElementFraming"]["nestedElementMarkerCounts"] = {"2": 2}
            native = {"status": "validated", "validationFailures": [],
                      "profile": gate.NATIVE_PROFILE,
                      "contractSha256": gate.shared.sha256_file(
                          ROOT / "scripts/game_data/streaming_marker2_native.json")}
            for mutation in (None, "field4VectorSha256", "packedSha256"):
                with self.subTest(mutation=mutation):
                    changed = json.loads(json.dumps(document))
                    first = changed["layer3"]["pairedRootIdentities"]["pairs"][0]["init"]
                    if mutation == "field4VectorSha256":
                        first["witness"][mutation] = "F" * 64
                    elif mutation is not None:
                        first[mutation] = "F" * 64
                    write_json(fixture.report, changed)
                    with mock.patch.object(gate, "validate_marker2_native_contract", return_value=native):
                        result = gate.sweep(
                            repo_root=ROOT, root_report_path=fixture.report,
                            outer_summary_path=fixture.outer, ledger_path=fixture.ledger,
                            expected_input_set_sha256=INPUT_SET, game_root=fixture.game_root,
                        )
                    self.assertEqual(result["failed"], mutation is not None, result["failures"])
                    if mutation is None:
                        self.assertTrue(result["publicationEligible"])
                        summary = result["summary"]
                        self.assertEqual(summary["filesSucceeded"], 2)
                        self.assertEqual(summary["marker2References"], 2)
                        self.assertEqual(summary["framedReferences"], 1)
                        self.assertEqual(summary["unsupportedReferences"], 1)
                        self.assertEqual(summary["nativeReadWindowReferenceBytes"], 4)
                        self.assertEqual(summary["residualOpaqueReferenceBytes"], 2)
                        self.assertEqual(summary["filesWithFramedReferences"], 1)
                        self.assertEqual(summary["selectedPhysicalGapLengthCounts"], {"4": 0, "6": 1})
                    else:
                        self.assertFalse(result["publicationEligible"])
                        self.assertEqual(result["_inventoryRows"], [])


if __name__ == "__main__":
    unittest.main()
