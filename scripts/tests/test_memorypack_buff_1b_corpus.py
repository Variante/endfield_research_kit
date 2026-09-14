import base64
import hashlib
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.game_data.memorypack import buff_1b_corpus
from scripts.game_data.memorypack import corpus_gate


INPUT_SET = "A" * 64
LOGICAL_SHA = "B" * 64
PATH = "Data/Json/BuffData/buff_chr_0030_zhuangfy_power_attack_blow.json"


def corpus_row(*, coverage="unique", tag=0x1B, continuation="supported-prefix"):
    start, end, hard_limit = 10, 20, 100
    context = {
        "inputSetSha256": INPUT_SET,
        "logicalFileIdentity": PATH,
        "logicalSha256": LOGICAL_SHA,
        "startOffset": 5,
        "hardLimit": hard_limit,
    }
    record = {
        "start": start,
        "end": end,
        "kind": "union",
        "tag": tag,
        "boundaryClass": "exact-closed",
        "hardLimit": hard_limit,
        "boundaryContext": {**context, "recordRange": [start, end]},
    }
    profile = {
        "status": continuation,
        "startOffset": 5,
        "parserCursor": 40,
        "readLimit": hard_limit,
        "hardLimit": hard_limit,
        "boundaryClass": "unsupported" if continuation == "unsupported" else "structural-prefix",
        "boundaryContext": context,
        "ranges": [{"start": start, "end": start + 1, "kind": "union-tag"}],
        "completedRecords": [record],
    }
    candidate = {
        "startOffset": 5,
        "anchorOffset": hard_limit,
        "hardLimit": hard_limit,
        "readerAcceptedThroughEof": True,
        "boundaryContext": context,
        "currentRootContinuation": profile,
        "currentEventPrefix": {
            "status": "supported-prefix",
            "consumedEnd": 5,
            "parserCursor": 5,
            "readLimit": hard_limit,
            "hardLimit": hard_limit,
            "boundaryContext": context,
            "completedRecords": [
                {"start": 1, "end": 2, "kind": "union", "tag": 0x1B}
            ]
        },
    }
    return {
        "identity": {
            "inputSetSha256": INPUT_SET,
            "virtualPath": PATH,
            "length": hard_limit,
            "recomputedFileDataMd5": "C" * 32,
        },
        "logicalSha256": LOGICAL_SHA,
        "coverageStatus": coverage,
        "rootContinuationStatus": "unsupported" if continuation == "unsupported" else "success",
        "candidates": [candidate],
    }


def buff_census(row):
    return {
        "format": "animestudio-buffdata-current-vfs-corpus",
        "schemaVersion": 1,
        "status": "complete",
        "publicationEligible": True,
        "inputSetSha256": INPUT_SET,
        "files": [row],
    }


def native_fixture():
    formatter = "Beyond.MemoryPack.BlowOffActionFormatter"
    data_type = "Beyond.MemoryPack.BlowOffAction_Data"
    sequence_type = buff_1b_corpus.SEQUENCE_TYPE
    base = 0x180000000
    contract_methods = [
        [118713, formatter, "Deserialize", 0x1000],
        [118712, data_type, "Deserialize", 0x2000],
    ]
    code_windows = [
        {"startRva": 0x2000, "endRva": 0x2010, "sha256": "D" * 64}
    ]
    nested_contexts = []
    read_order = {"member17": ["byte", "target-profile"]}
    contract = {
        "schemaVersion": 1,
        "nativeInputs": {
            "gameassemblySha256": "4" * 64,
            "metadataSha256": "5" * 64,
        },
        "unionRoute": {
            "tag": 0x1B,
            "switchTargetRva": 0x390EB56,
            "typeDefinition": 15937,
            "wrapperName": data_type,
            "dataReaderMethodIndex": 118712,
            "operands": [{
                "instructionRva": 0x390EB56,
                "usageTag": 1,
                "registeredTypeIndex": 106327,
            }],
        },
        "methods": contract_methods,
        "codeWindows": code_windows,
        "nestedContexts": nested_contexts,
        "anonymousReadOrder": read_order,
    }
    selected_methods = [
        {
            "methodIndex": index,
            "declaringType": declaring,
            "name": name,
            "pointerVa": base + rva,
            "image": "MemoryPack.Beyond.dll",
        }
        for index, declaring, name, rva in contract_methods
    ]
    root_contract = {
        "schemaVersion": 1,
        "methods": [
            [104480, "Beyond.MemoryPack.BuffActionMapFormatter", "Deserialize", 0x3000],
            [104479, "Beyond.MemoryPack.BuffActionMap", "Deserialize", 0x4000],
        ],
        "anonymousReadOrder": {"rootMember6": ["nullable-signed-count"]},
        "codeWindows": [
            {"startRva": 0x3000, "endRva": 0x3010, "sha256": "E" * 64}
        ],
        "nestedContexts": [],
    }
    root_reader = {
        "contractPath": "D:/repo/scripts/game_data/buff_root_sixth_native.json",
        "contractSha256": "F" * 64,
        "methods": [
            {
                "methodIndex": 104480,
                "declaringType": "Beyond.MemoryPack.BuffActionMapFormatter",
                "name": "Deserialize",
                "pointerVa": base + 0x3000,
                "image": "MemoryPack.Beyond.dll",
            },
            {
                "methodIndex": 104479,
                "declaringType": "Beyond.MemoryPack.BuffActionMap",
                "name": "Deserialize",
                "pointerVa": base + 0x4000,
                "image": "MemoryPack.Beyond.dll",
            },
        ],
        "anonymousReadOrder": root_contract["anonymousReadOrder"],
        "codeWindows": root_contract["codeWindows"],
        "nestedContexts": root_contract["nestedContexts"],
        "boundary": "conditional root member six",
    }
    route = {
        "tag": 0x1B,
        "switchTargetRva": 0x390EB56,
        "typeDefinition": 15937,
        "wrapperName": data_type,
        "operands": [{
            "instructionRva": 0x390EB56,
            "usageTag": 1,
            "registeredTypeIndex": 106327,
        }],
    }
    reader = {
        "contractPath": "D:/repo/scripts/game_data/buff_1b_native.json",
        "contractSha256": "C" * 64,
        "methods": selected_methods,
        "codeWindows": code_windows,
        "nestedContexts": nested_contexts,
        "anonymousReadOrder": read_order,
    }
    sequence_reader = {
        "methods": [
            {
                "methodIndex": 104346,
                "declaringType": sequence_type,
                "name": "Deserialize",
                "image": "MemoryPack.Beyond.dll",
            }
        ],
        "rootCodeWindow": {"startRva": 0x4000, "endRva": 0x4010, "sha256": "1" * 64},
        "boundary": "provider identity unresolved",
    }
    native = {
        "schemaVersion": 1,
        "status": "structural-only",
        "inputSetSha256": INPUT_SET,
        "nativeInputs": {
            "gameassemblySha256": "4" * 64,
            "metadataSha256": "5" * 64,
        },
        "selectedBuffUnionRoutes": {"rows": [route]},
        "selectedBuff1BReadOrder": reader,
        "selectedBuffRootSixthReadOrder": root_reader,
        "selectedBuffSequenceReadOrder": sequence_reader,
    }
    return native, contract, root_contract


class Buff1BCorpusTests(unittest.TestCase):
    def test_unique_root_record_is_bound_to_current_identity_and_exact_tag_byte(self):
        records = buff_1b_corpus.select_root_tag_records(
            buff_census(corpus_row()),
            expected_input_set_sha256=INPUT_SET,
        )
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["uniqueCandidate"])
        self.assertEqual(records[0]["recordRange"], [10, 20])
        records[0]["_profileRanges"] = [
            {"start": 10, "end": 11, "kind": "union-tag"}
        ]
        buff_1b_corpus.bind_tag_bytes(records, {PATH: b"\0" * 10 + b"\x1b" + b"\0" * 89})
        self.assertEqual(records[0]["tagByteRange"], [10, 11])
        self.assertEqual(records[0]["tagByteHex"], "1B")
        self.assertNotIn("_profileRanges", records[0])

    def test_tag_in_first_collection_does_not_count_as_root_continuation(self):
        row = corpus_row(tag=0x20)
        row["candidates"][0]["currentRootContinuation"]["completedRecords"] = []
        records = buff_1b_corpus.select_root_tag_records(
            buff_census(row),
            expected_input_set_sha256=INPUT_SET,
        )
        self.assertEqual(records, [])

    def test_record_context_mismatch_fails_closed(self):
        row = corpus_row()
        row["candidates"][0]["currentRootContinuation"]["completedRecords"][0][
            "boundaryContext"
        ]["logicalSha256"] = "F" * 64
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.select_root_tag_records(
                buff_census(row),
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(caught.exception.diagnostic["code"], "buff-tag27-boundary-context-mismatch")
        self.assertEqual(caught.exception.diagnostic["source"], PATH)

    def test_non_unique_anchor_stays_ambiguous(self):
        row = corpus_row(coverage="ambiguous")
        records = buff_1b_corpus.select_root_tag_records(
            buff_census(row),
            expected_input_set_sha256=INPUT_SET,
        )
        self.assertEqual(len(records), 1)
        self.assertFalse(records[0]["uniqueCandidate"])
        self.assertEqual(records[0]["fileCoverageStatus"], "ambiguous")

    def test_earlier_exact_record_remains_local_when_later_continuation_is_unsupported(self):
        row = corpus_row(continuation="unsupported")
        records = buff_1b_corpus.select_root_tag_records(
            buff_census(row),
            expected_input_set_sha256=INPUT_SET,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["continuationStatus"], "unsupported")
        self.assertEqual(records[0]["recordRange"], [10, 20])

    def test_continuation_wider_read_limit_is_rejected(self):
        row = corpus_row()
        row["candidates"][0]["currentRootContinuation"]["readLimit"] += 1
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.select_root_tag_records(
                buff_census(row),
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "buff-tag27-continuation-boundary-mismatch",
        )

    def test_continuation_start_offset_mismatch_is_rejected(self):
        row = corpus_row()
        row["candidates"][0]["currentRootContinuation"]["startOffset"] += 1
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.select_root_tag_records(
                buff_census(row),
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "buff-tag27-continuation-boundary-mismatch",
        )

    def test_literal_tag_byte_mismatch_fails_closed(self):
        records = buff_1b_corpus.select_root_tag_records(
            buff_census(corpus_row()),
            expected_input_set_sha256=INPUT_SET,
        )
        records[0]["_profileRanges"] = [
            {"start": 10, "end": 11, "kind": "union-tag"}
        ]
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.bind_tag_bytes(records, {PATH: b"\0" * 10 + b"\x20" + b"\0" * 89})
        self.assertEqual(caught.exception.diagnostic["code"], "buff-tag27-byte-mismatch")
        self.assertEqual(caught.exception.diagnostic["offset"], 10)

    def test_exact_stream_row_matches_ledger_and_logical_hashes(self):
        data = b"buff-action"
        selected = {
            "ledgerIdentity": {
                "length": len(data),
                "recomputedFileDataMd5": hashlib.md5(data).hexdigest().upper(),
            },
            "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
        }
        row = {
            "fileName": PATH,
            "blockType": "JsonData",
            "blockTypeValue": 19,
            "length": len(data),
            "dataBase64": base64.b64encode(data).decode("ascii"),
        }
        process = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(row) + "\n",
            stderr="Streamed 1 files\n",
        )
        with patch("scripts.game_data.memorypack.buff_1b_corpus.subprocess.run", return_value=process) as run:
            result = buff_1b_corpus._stream_exact_files(
                Path("animestudio.exe"),
                {"primaryAssets": "primary", "fallbackAssets": "fallback"},
                {PATH: selected},
            )
        self.assertEqual(result, {PATH: data})
        self.assertIn("--verify-md5", run.call_args.args[0])

    def test_exact_stream_ledger_md5_mismatch_fails_closed(self):
        data = b"buff-action"
        selected = {
            "ledgerIdentity": {"length": len(data), "recomputedFileDataMd5": "0" * 32},
            "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
        }
        row = {
            "fileName": PATH,
            "blockType": "JsonData",
            "blockTypeValue": 19,
            "length": len(data),
            "dataBase64": base64.b64encode(data).decode("ascii"),
        }
        process = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(row) + "\n",
            stderr="Streamed 1 files\n",
        )
        with patch("scripts.game_data.memorypack.buff_1b_corpus.subprocess.run", return_value=process):
            with self.assertRaises(corpus_gate.CensusGateError) as caught:
                buff_1b_corpus._stream_exact_files(
                    Path("animestudio.exe"),
                    {"primaryAssets": "primary", "fallbackAssets": "fallback"},
                    {PATH: selected},
                )
        self.assertEqual(caught.exception.diagnostic["code"], "buff-tag27-stream-md5-mismatch")

    def test_exact_stream_logical_sha_mismatch_fails_closed(self):
        data = b"buff-action"
        selected = {
            "ledgerIdentity": {
                "length": len(data),
                "recomputedFileDataMd5": hashlib.md5(data).hexdigest().upper(),
            },
            "logicalSha256": "0" * 64,
        }
        row = {
            "fileName": PATH,
            "blockType": "JsonData",
            "blockTypeValue": 19,
            "length": len(data),
            "dataBase64": base64.b64encode(data).decode("ascii"),
        }
        process = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(row) + "\n",
            stderr="Streamed 1 files\n",
        )
        with patch("scripts.game_data.memorypack.buff_1b_corpus.subprocess.run", return_value=process):
            with self.assertRaises(corpus_gate.CensusGateError) as caught:
                buff_1b_corpus._stream_exact_files(
                    Path("animestudio.exe"),
                    {"primaryAssets": "primary", "fallbackAssets": "fallback"},
                    {PATH: selected},
                )
        self.assertEqual(caught.exception.diagnostic["code"], "buff-tag27-stream-logical-sha-mismatch")

    def test_native_registration_and_selected_reader_are_joined(self):
        native, contract, root_contract = native_fixture()
        evidence = buff_1b_corpus.validate_native_selection(
            native,
            contract,
            root_contract,
            expected_input_set_sha256=INPUT_SET,
        )
        self.assertEqual(evidence["unionRoute"]["tag"], 0x1B)
        self.assertEqual(evidence["unionRoute"]["wrapperName"], "Beyond.MemoryPack.BlowOffAction_Data")
        self.assertEqual(evidence["readerMethods"][1]["methodIndex"], 118712)
        self.assertEqual(evidence["rootMemberSix"]["methods"][1]["methodIndex"], 104479)
        self.assertEqual(evidence["rootMemberSix"]["gameAssemblyImageBase"], 0x180000000)
        self.assertEqual(evidence["rootMemberSix"]["anonymousReadOrder"], root_contract["anonymousReadOrder"])
        self.assertIn("provider", evidence["sequenceReader"]["boundary"])

    def test_native_reader_cannot_be_paired_with_a_different_union_type(self):
        native, contract, root_contract = native_fixture()
        native["selectedBuffUnionRoutes"]["rows"][0]["wrapperName"] = "Beyond.OtherAction_Data"
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(caught.exception.diagnostic["code"], "native-buff-1b-route-contract-mismatch")

    def test_formatter_route_cannot_substitute_for_the_data_reader(self):
        native, contract, root_contract = native_fixture()
        native["selectedBuffUnionRoutes"]["rows"][0]["wrapperName"] = "Beyond.MemoryPack.BlowOffActionFormatter"
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(caught.exception.diagnostic["code"], "native-buff-1b-route-contract-mismatch")

    def test_route_target_type_and_registration_operand_are_pinned(self):
        mutations = (
            ("switchTargetRva", 0x390EB57),
            ("typeDefinition", 15938),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                native, contract, root_contract = native_fixture()
                native["selectedBuffUnionRoutes"]["rows"][0][field] = value
                with self.assertRaises(corpus_gate.CensusGateError) as caught:
                    buff_1b_corpus.validate_native_selection(
                        native,
                        contract,
                        root_contract,
                        expected_input_set_sha256=INPUT_SET,
                    )
                self.assertEqual(
                    caught.exception.diagnostic["code"],
                    "native-buff-1b-route-contract-mismatch",
                )
        native, contract, root_contract = native_fixture()
        native["selectedBuffUnionRoutes"]["rows"][0]["operands"][0]["registeredTypeIndex"] += 1
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "native-buff-1b-route-contract-mismatch",
        )

    def test_native_duplicate_route_is_ambiguous_and_rejected(self):
        native, contract, root_contract = native_fixture()
        native["selectedBuffUnionRoutes"]["rows"].append(
            dict(native["selectedBuffUnionRoutes"]["rows"][0])
        )
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(caught.exception.diagnostic["code"], "native-union-route-not-unique")

    def test_native_input_set_mismatch_is_rejected(self):
        native, contract, root_contract = native_fixture()
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256="9" * 64,
            )
        self.assertEqual(caught.exception.diagnostic["code"], "native-audit-input-set-mismatch")

    def test_native_input_hashes_must_match_the_versioned_contract(self):
        native, contract, root_contract = native_fixture()
        native["nativeInputs"]["gameassemblySha256"] = "6" * 64
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(caught.exception.diagnostic["code"], "native-input-contract-mismatch")

    def test_root_member_sixth_methods_must_match_the_contract(self):
        native, contract, root_contract = native_fixture()
        native["selectedBuffRootSixthReadOrder"]["methods"][1]["methodIndex"] = 999999
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "native-root-sixth-method-not-unique",
        )

    def test_output_cannot_overwrite_a_native_source(self):
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus._guard_output_paths(
                (buff_1b_corpus.NATIVE_SOURCE_PATHS[0],),
                [],
            )
        self.assertIn("output", caught.exception.diagnostic["code"])

    def test_root_reader_image_base_must_match_1b_reader(self):
        native, contract, root_contract = native_fixture()
        for method in native["selectedBuffRootSixthReadOrder"]["methods"]:
            method["pointerVa"] += 0x10000
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
            )
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "native-root-sixth-image-base-differs-from-data-reader",
        )

    def test_all_reported_method_pointers_must_use_pe_image_base(self):
        native, contract, root_contract = native_fixture()
        for reader_key in ("selectedBuff1BReadOrder", "selectedBuffRootSixthReadOrder"):
            for method in native[reader_key]["methods"]:
                method["pointerVa"] += 0x10000
        with self.assertRaises(corpus_gate.CensusGateError) as caught:
            buff_1b_corpus.validate_native_selection(
                native,
                contract,
                root_contract,
                expected_input_set_sha256=INPUT_SET,
                expected_gameassembly_image_base=0x180000000,
            )
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "native-buff-1b-method-pe-image-base-mismatch",
        )

    def test_reads_image_base_from_bounded_amd64_pe32_plus_header(self):
        data = bytearray(0x200)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 0x80)
        data[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HHIIIHH", data, 0x84, 0x8664, 1, 0, 0, 0, 0xF0, 0x2022)
        optional = 0x80 + 24
        struct.pack_into("<H", data, optional, 0x20B)
        struct.pack_into("<Q", data, optional + 24, 0x180000000)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "GameAssembly.dll"
            path.write_bytes(data)
            self.assertEqual(buff_1b_corpus._read_pe_image_base(path), 0x180000000)

    def test_rejects_non_pe32_plus_image_base_header(self):
        data = bytearray(0x200)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 0x80)
        data[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HHIIIHH", data, 0x84, 0x8664, 1, 0, 0, 0, 0xF0, 0x2022)
        optional = 0x80 + 24
        struct.pack_into("<H", data, optional, 0x10B)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "GameAssembly.dll"
            path.write_bytes(data)
            with self.assertRaises(corpus_gate.CensusGateError) as caught:
                buff_1b_corpus._read_pe_image_base(path)
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "native-gameassembly-optional-magic-invalid",
        )

    def test_rejects_pe_header_overlapping_the_dos_header(self):
        data = bytearray(0x200)
        data[:2] = b"MZ"
        data[2:6] = b"PE\0\0"
        struct.pack_into("<HHIIIHH", data, 6, 0x8664, 1, 0, 0, 0, 0xF0, 0x2022)
        optional = 2 + 24
        struct.pack_into("<H", data, optional, 0x20B)
        struct.pack_into("<Q", data, optional + 24, 0x180000000)
        struct.pack_into("<I", data, 0x3C, 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "GameAssembly.dll"
            path.write_bytes(data)
            with self.assertRaises(corpus_gate.CensusGateError) as caught:
                buff_1b_corpus._read_pe_image_base(path)
        self.assertEqual(
            caught.exception.diagnostic["code"],
            "native-gameassembly-pe-offset-before-header",
        )


if __name__ == "__main__":
    unittest.main()
