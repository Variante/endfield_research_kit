"""Independent desired-contract tests for scripts.game_data.streaming_pairs."""
from __future__ import annotations

import copy
import hashlib
import struct
import unittest

from scripts.game_data import streaming_pairs as pairs


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def make_root() -> bytes:
    data = bytearray(224)
    struct.pack_into("<I", data, 0, 32)
    # Six-field root table at 32, vtable at 8.
    struct.pack_into("<HH6H", data, 8, 16, 16, 0, 0, 0, 4, 8, 12)
    struct.pack_into("<i", data, 32, 24)
    struct.pack_into("<I", data, 36, 80 - 36)
    struct.pack_into("<I", data, 40, 96 - 40)
    struct.pack_into("<I", data, 44, 112 - 44)
    # Complete ordered field3/4 vectors and row-uoffset field5 vector.
    struct.pack_into("<III", data, 80, 2, 0x11111111, 0x22222222)
    struct.pack_into("<I2B", data, 96, 2, 2, 3)
    struct.pack_into("<III", data, 112, 2, 160 - 116, 192 - 120)
    # Two bounded row tables. field2 is absent in both, though this module only
    # binds their exact uoffsets; the marker13 parser owns absence projection.
    struct.pack_into("<HH3H", data, 144, 10, 8, 4, 0, 0)
    struct.pack_into("<iI", data, 160, 16, 0xAAAAAAAA)
    struct.pack_into("<HH3H", data, 176, 10, 8, 4, 0, 0)
    struct.pack_into("<iI", data, 192, 16, 0xBBBBBBBB)
    return bytes(data)


class StreamingPairsCandidateTests(unittest.TestCase):
    def setUp(self):
        self.data = make_root()
        self.streaming_path = "Data/Streaming/PC/test/Streaming/StreamingChunkData_1_2_0_0.bytes"
        self.init_path = "Data/Streaming/PC/test/Streaming/InitChunkData_1_2_0_0.bytes"
        self.identity = {
            "virtualPath": self.streaming_path,
            "physicalChunkPath": "D:/game/VFS/A/B.chk",
            "physicalChunkSource": "fallback",
            "metadataProvenance": "primary",
            "overlayState": "identical",
            "offset": 20,
            "length": 40,
            "packedSha256": "A" * 64,
        }
        self.witness = {
            "rowCount": 2,
            "field3VectorSha256": digest(self.data[80:92]),
            "field4VectorSha256": digest(self.data[96:102]),
            "rowField0ValuesSha256": "B" * 64,
            "field3DuplicateCount": 0,
        }
        init = {
            **self.identity,
            "virtualPath": self.init_path,
            "packedSha256": "C" * 64,
            "witness": {**self.witness, "rowField0ValuesSha256": "D" * 64},
        }
        streaming = {**self.identity, "witness": dict(self.witness)}
        self.report = {
            "layer3": {"pairedRootIdentities": {
                "status": "exact-ordered-witness-matches",
                "candidatePairCount": 1,
                "matchedPairCount": 1,
                "mismatchedPairCount": 0,
                "unpairedFileCount": 0,
                "unpairedFiles": [],
                "pairs": [{"init": init, "streaming": streaming,
                           "status": "exact-ordered-witness-match",
                           "differences": [], "rowField0ValuesEqual": False}],
            }}
        }
        self.parsed = {"anonymousParallelSubgraph": {"orderedRootWitness": {
            **self.witness,
            "encoding": "vectors include u32 count; row-field0 digest concatenates u32 length and exact bytes in row order",
        }}}

    def context(self, *, report=None, identity=None, data=None, parsed=None):
        selected_report = self.report if report is None else report
        index = pairs.index_ordered_pairs(selected_report)
        return pairs.bind_current_pair(
            pair_index=index,
            identity=self.identity if identity is None else identity,
            decoded=self.data if data is None else data,
            parsed=self.parsed if parsed is None else parsed,
            root_report_sha256="E" * 64,
        )

    def test_normal_synthetic_root_binds_all_three_vectors(self):
        context = self.context()
        self.assertEqual(context["markerVectorStart"], 96)
        self.assertEqual(context["rowVectorStart"], 112)
        self.assertEqual(context["decodedSha256"], digest(self.data))
        self.assertIn("staged", context["publicationCondition"])

    def test_normal_exact_row_uoffset_and_marker_ordinal(self):
        context = self.context()
        row = {"outerRowIndex": 0, "rootMarker": 2,
               "rootMarkerOffset": 100, "outerRowOffset": 160}
        result = pairs.bind_pair_row(self.data, row, context)
        self.assertEqual(result["outerRowOffset"], 160)
        self.assertEqual(result["classification"],
                         "conditional-new-key-native-read-window-compatibility")
        self.assertEqual(result["runtimeReceipt"], "unresolved")

    def test_equal_counts_cannot_replace_complete_field4_digest(self):
        report = copy.deepcopy(self.report)
        report["layer3"]["pairedRootIdentities"]["pairs"][0]["init"]["witness"]["field4VectorSha256"] = "F" * 64
        with self.assertRaises(ValueError):
            pairs.index_ordered_pairs(report)

    def test_forged_leaf_or_duplicate_pair_rejected(self):
        with self.subTest("leaf"):
            report = copy.deepcopy(self.report)
            report["layer3"]["pairedRootIdentities"]["pairs"][0]["init"]["virtualPath"] = "Data/wrong.bytes"
            with self.assertRaises(ValueError):
                pairs.index_ordered_pairs(report)
        with self.subTest("duplicate"):
            report = copy.deepcopy(self.report)
            report["layer3"]["pairedRootIdentities"]["pairs"].append(
                copy.deepcopy(report["layer3"]["pairedRootIdentities"]["pairs"][0]))
            report["layer3"]["pairedRootIdentities"]["candidatePairCount"] = 2
            report["layer3"]["pairedRootIdentities"]["matchedPairCount"] = 2
            with self.assertRaises(ValueError):
                pairs.index_ordered_pairs(report)

    def test_wrong_identity_sha_or_current_witness_rejected(self):
        with self.subTest("packed sha"):
            with self.assertRaises(ValueError):
                self.context(identity={**self.identity, "packedSha256": "F" * 64})
        with self.subTest("parsed witness"):
            parsed = copy.deepcopy(self.parsed)
            parsed["anonymousParallelSubgraph"]["orderedRootWitness"]["field3VectorSha256"] = "F" * 64
            with self.assertRaises(ValueError):
                self.context(parsed=parsed)

    def test_current_vector_bytes_recomputed_not_trusted(self):
        data = bytearray(self.data)
        data[88] ^= 1
        with self.assertRaises(ValueError):
            self.context(data=bytes(data))

    def test_bad_ordinal_marker_offset_or_row_target_rejected(self):
        context = self.context()
        base = {"outerRowIndex": 0, "rootMarker": 2,
                "rootMarkerOffset": 100, "outerRowOffset": 160}
        for change in (
            {"outerRowIndex": 2},
            {"rootMarkerOffset": 101},
            {"outerRowOffset": 192},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                pairs.bind_pair_row(self.data, {**base, **change}, context)

    def test_directory_root_marker_must_match_actual_marker2(self):
        context = self.context()
        row = {"outerRowIndex": 0, "rootMarker": 3,
               "rootMarkerOffset": 100, "outerRowOffset": 160}
        with self.assertRaises(ValueError):
            pairs.bind_pair_row(self.data, row, context)

    def test_context_cannot_be_reused_with_different_decoded_bytes(self):
        context = self.context()
        changed = bytearray(self.data)
        changed[220] = 1  # outside all checked vectors, but changes file identity
        row = {"outerRowIndex": 0, "rootMarker": 2,
               "rootMarkerOffset": 100, "outerRowOffset": 160}
        with self.assertRaises(ValueError):
            pairs.bind_pair_row(bytes(changed), row, context)

    def test_unpaired_inventory_must_agree_with_zero_count(self):
        report = copy.deepcopy(self.report)
        report["layer3"]["pairedRootIdentities"]["unpairedFiles"] = ["forged"]
        with self.assertRaises(ValueError):
            pairs.index_ordered_pairs(report)

    def test_boolean_pair_counts_are_not_integers(self):
        report = copy.deepcopy(self.report)
        summary = report["layer3"]["pairedRootIdentities"]
        summary["candidatePairCount"] = True
        summary["matchedPairCount"] = True
        summary["mismatchedPairCount"] = False
        summary["unpairedFileCount"] = False
        with self.assertRaises(ValueError):
            pairs.index_ordered_pairs(report)

    def test_missing_complete_current_witness_field_rejected(self):
        report = copy.deepcopy(self.report)
        del report["layer3"]["pairedRootIdentities"]["pairs"][0]["streaming"]["witness"]["rowField0ValuesSha256"]
        with self.assertRaises((ValueError, KeyError)):
            index = pairs.index_ordered_pairs(report)
            pairs.bind_current_pair(
                pair_index=index, identity=self.identity, decoded=self.data,
                parsed=self.parsed, root_report_sha256="E" * 64)

    def test_root_report_sha_must_be_exact_uppercase_digest(self):
        index = pairs.index_ordered_pairs(self.report)
        with self.assertRaises(ValueError):
            pairs.bind_current_pair(pair_index=index, identity=self.identity,
                                    decoded=self.data, parsed=self.parsed,
                                    root_report_sha256="e" * 64)


if __name__ == "__main__":
    unittest.main()
