from __future__ import annotations

import copy
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.game_data import streaming_marker13_native as candidate


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def one_section_pe() -> bytearray:
    image = bytearray(0x6000)
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", image, 0x86, 1)
    struct.pack_into("<H", image, 0x94, 0xE0)
    section = 0x80 + 24 + 0xE0
    image[section:section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", image, section + 8, 0x5000, 0x1000, 0x5000, 0x200)
    return image


class Fixture:
    """Small synthetic PE plus fully synthetic v2 dependency catalogs."""

    def __init__(self, root: Path):
        self.root = root
        self.game_root = root / "selected/Endfield_Data"
        self.game_root.mkdir(parents=True)
        self.image_path = self.game_root.parent / "UnityPlayer.dll"
        self.dependency_path = root / "marker17.json"
        self.base_path = root / "streaming-native.json"
        self.contract_path = root / "marker13.json"

        self.whole = {
            "selector9Slot4Reader": (0x1010, b"R4-whole"),
            "selector9Slot5Reader": (0x1040, b"R5-whole"),
            "slot4LocalFourDwordConsumer": (0x1070, b"C4-whole-body"),
            "slot5LocalFourDwordConsumer": (0x10A0, b"C5-whole-body"),
        }
        self.registrations = {
            4: (0x10D0, b"register-slot4"),
            5: (0x1100, b"register-slot5"),
        }
        self.literal = (0x1130, struct.pack("<3I", 255, 0, 0))
        self.additions = {
            "slot5DispatchWholeHotBodyThroughFinalBackedge": (0x1180, b"hot-dispatch-whole"),
            "slot5DispatchColdIndirectBranchAndReturnEdge": (0x11C0, b"cold-edge"),
            "slot5SelectedMarker2EntryWholeBody": (0x1200, b"marker2-entry-whole"),
            "slot5ScopeWholeBody": (0x1240, b"slot5-scope-whole-body"),
            "slot5Marker2DispatchPointer": (0x1290, b"dispatch"),
            "selector0DescriptorConstructorArgumentsAndCall": (0x12C0, b"selector0-ctor"),
            "selector0Slot5Registration": (0x1300, b"selector0-register-slot5"),
            "selector0PublicationArgumentsAndCall": (0x1350, b"selector0-publish"),
        }
        self.base_ranges = {
            "parallelScopeCallbackBridgeA": (0x1400, b"base-bridge"),
            "descriptorConstructor": (0x1430, b"base-ctor"),
            "callbackAssignment": (0x1460, b"base-assign"),
            "inlineCallbackMove": (0x1490, b"base-inline"),
            "callbackReset": (0x14C0, b"base-reset"),
            "publishTenCallbacks": (0x14F0, b"base-publish"),
        }
        self.marker17_ranges = {
            "indexedCallbackAssignment": (0x1530, b"marker17-indexed-assignment"),
        }

        image = one_section_pe()
        all_spans = (
            list(self.whole.values())
            + list(self.registrations.values())
            + [self.literal]
            + list(self.additions.values())
            + list(self.base_ranges.values())
            + list(self.marker17_ranges.values())
        )
        for rva, body in all_spans:
            offset = self.file_offset(rva)
            image[offset:offset + len(body)] = body
        self.image_path.write_bytes(image)
        self.write_documents()

    @staticmethod
    def file_offset(rva: int) -> int:
        return 0x200 + rva - 0x1000

    @staticmethod
    def range_rows(spans: dict[str, tuple[int, bytes]]) -> list[dict]:
        return [
            {
                "role": role,
                "rva": rva,
                "fileOffset": Fixture.file_offset(rva),
                "size": len(body),
                "bodySha256": sha256(body),
                "entryBytesHex": body[:4].hex().upper(),
            }
            for role, (rva, body) in spans.items()
        ]

    def write_documents(self) -> None:
        image = self.image_path.read_bytes()
        self.inputs = {
            "gameAssemblySha256": "GA",
            "metadataSha256": "MD",
            "unityPlayerSha256": sha256(image),
        }
        base_document = {
            "schema": "fixture.streaming-native.v1",
            "status": "validated",
            "unityPlayerRanges": self.range_rows(self.base_ranges),
        }
        self.base_path.write_text(json.dumps(base_document), encoding="utf-8")
        self.base_sha = sha256(self.base_path.read_bytes())

        dependency_document = {
            "schema": "fixture.marker17.v2",
            "status": "validated-conditional-static",
            "unityPlayerRanges": self.range_rows(self.marker17_ranges),
            "selectedDefaultSlot3": [
                {
                    "selector": 9,
                    "descriptorConstructorSpan": {"bytesHex": "AA"},
                    "publicationSpan": {"bytesHex": "BB"},
                }
            ],
        }
        self.dependency_path.write_text(json.dumps(dependency_document), encoding="utf-8")
        self.dependency_sha = sha256(self.dependency_path.read_bytes())

        slots = []
        for slot, (rva, body) in self.registrations.items():
            reader_role = f"selector9Slot{slot}Reader"
            downstream_role = f"slot{slot}LocalFourDwordConsumer"
            slots.append(
                {
                    "selector": 9,
                    "key": [255, 0, 0],
                    "slot": slot,
                    "readerRva": self.whole[reader_role][0],
                    "readerRangeRole": reader_role,
                    "downstreamRangeRole": downstream_role,
                    "registrationSpan": {
                        "rva": rva,
                        "fileOffset": self.file_offset(rva),
                        "bytesHex": body.hex().upper(),
                    },
                }
            )
        literal_rva, literal = self.literal
        reuse = []
        for role, (rva, body) in self.base_ranges.items():
            reuse.append({"contract": "base", "role": role, "rva": rva, "size": len(body)})
        for role, (rva, body) in self.marker17_ranges.items():
            reuse.append({"contract": "marker17", "role": role, "rva": rva, "size": len(body)})
        for role in ("selector9Slot5Reader", "slot5LocalFourDwordConsumer"):
            rva, body = self.whole[role]
            reuse.append({"contract": "self", "role": role, "rva": rva, "size": len(body)})
        reuse.append(
            {
                "contract": "self",
                "role": "keyLiteralRange",
                "rva": literal_rva,
                "size": len(literal),
            }
        )

        document = {
            "schema": candidate.SCHEMA,
            "status": "validated-conditional-static",
            "nativeMappingId": "fixture-marker13-v2",
            "dependency": {
                "schema": dependency_document["schema"],
                "sha256": self.dependency_sha,
                "requiredUnityPlayerRoles": ["indexedCallbackAssignment"],
                "requiredDefaultRegistration": {
                    "selector": 9,
                    "slot": 3,
                    "reusedEvidence": ["descriptorConstructorSpan", "publicationSpan"],
                },
            },
            "nativeInputs": self.inputs,
            "unityPlayerRanges": self.range_rows(self.whole),
            "keyLiteralRange": {
                "key": [255, 0, 0],
                "rva": literal_rva,
                "fileOffset": self.file_offset(literal_rva),
                "bytesHex": literal.hex().upper(),
            },
            "selectedDefaultSlots": slots,
            "profile": copy.deepcopy(candidate.EXPECTED_PROFILE),
            "consumerReview": {"readQualification": "fixture"},
            "evidenceBoundary": {"unresolved": ["EOF"]},
            "additionalUnityPlayerRanges": self.range_rows(self.additions),
            "absencePathReusedRanges": reuse,
            "absentSelectorContextWitness": copy.deepcopy(candidate.EXPECTED_ABSENT_WITNESS),
            "absentSelectorEvidence": {
                "serializedPolicy": "fixture keeps absence distinct from explicit selector zero"
            },
        }
        self.contract_path.write_text(json.dumps(document), encoding="utf-8")

    def dependency_result(self) -> dict:
        return {
            "status": "validated",
            "contractSha256": self.dependency_sha,
            "nativeInputs": dict(self.inputs),
            "validationFailures": [],
        }

    def rebase_image_hash_only(self) -> None:
        actual = sha256(self.image_path.read_bytes())
        document = json.loads(self.contract_path.read_text(encoding="utf-8"))
        document["nativeInputs"]["unityPlayerSha256"] = actual
        self.contract_path.write_text(json.dumps(document), encoding="utf-8")
        self.inputs["unityPlayerSha256"] = actual

    def mutate_document(self, callback) -> None:
        document = json.loads(self.contract_path.read_text(encoding="utf-8"))
        callback(document)
        self.contract_path.write_text(json.dumps(document), encoding="utf-8")

    def validate(self, *, dependency_result=None, expected_contract_sha=None):
        document = json.loads(self.contract_path.read_text(encoding="utf-8"))
        expected_inputs = document["nativeInputs"]
        expected_whole = {
            role: (rva, len(body)) for role, (rva, body) in self.whole.items()
        }
        expected_slots = {
            4: (
                self.whole["selector9Slot4Reader"][0],
                "selector9Slot4Reader",
                "slot4LocalFourDwordConsumer",
            ),
            5: (
                self.whole["selector9Slot5Reader"][0],
                "selector9Slot5Reader",
                "slot5LocalFourDwordConsumer",
            ),
        }
        expected_additions = {
            role: (rva, len(body)) for role, (rva, body) in self.additions.items()
        }
        expected_reuse = {
            (row["contract"], row["role"]): (row["rva"], row["size"])
            for row in self._original_reuse_rows()
        }
        selected = self.dependency_result() if dependency_result is None else dependency_result
        dependency_gate = mock.Mock(return_value=selected)
        with (
            mock.patch.object(
                candidate,
                "CONTRACT_SHA256",
                expected_contract_sha or sha256(self.contract_path.read_bytes()),
            ),
            mock.patch.object(candidate, "DEPENDENCY_SHA256", self.dependency_sha),
            mock.patch.object(candidate, "EXPECTED_INPUTS", expected_inputs),
            mock.patch.object(candidate, "EXPECTED_WHOLE", expected_whole),
            mock.patch.object(candidate, "EXPECTED_SLOTS", expected_slots),
            mock.patch.object(candidate, "EXPECTED_ABSENCE_RANGES", expected_additions),
            mock.patch.object(candidate, "EXPECTED_ABSENCE_REUSE", expected_reuse),
            mock.patch.object(candidate.dependency, "DEFAULT_CONTRACT", self.dependency_path),
            mock.patch.object(candidate.dependency, "validate_marker17_native_contract", dependency_gate),
            mock.patch.object(candidate.base, "DEFAULT_CONTRACT", self.base_path),
            mock.patch.object(candidate.base, "CONTRACT_SHA256", self.base_sha),
        ):
            result = candidate.validate_marker13_native_contract(
                game_root=self.game_root, contract_path=self.contract_path
            )
        return result, dependency_gate

    def _original_reuse_rows(self) -> list[dict]:
        rows = []
        for role, (rva, body) in self.base_ranges.items():
            rows.append({"contract": "base", "role": role, "rva": rva, "size": len(body)})
        for role, (rva, body) in self.marker17_ranges.items():
            rows.append({"contract": "marker17", "role": role, "rva": rva, "size": len(body)})
        for role in ("selector9Slot5Reader", "slot5LocalFourDwordConsumer"):
            rva, body = self.whole[role]
            rows.append({"contract": "self", "role": role, "rva": rva, "size": len(body)})
        rva, body = self.literal
        rows.append({"contract": "self", "role": "keyLiteralRange", "rva": rva, "size": len(body)})
        return rows


class Marker13NativeV2CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = Fixture(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def assert_failed_closed(self, result: dict, gate: str) -> None:
        self.assertEqual(result["status"], "validation_failed")
        self.assertIsNone(result["profile"])
        self.assertIsNone(result["consumerReview"])
        self.assertIsNone(result["absentSelectorContextWitness"])
        self.assertTrue(
            any(row["gate"] == gate for row in result["validationFailures"]), result
        )

    def tamper_image_and_rebase(self, role: str, spans: dict[str, tuple[int, bytes]]) -> dict:
        image = bytearray(self.fixture.image_path.read_bytes())
        rva = spans[role][0]
        image[self.fixture.file_offset(rva)] ^= 0xFF
        self.fixture.image_path.write_bytes(image)
        self.fixture.rebase_image_hash_only()
        result, _ = self.fixture.validate()
        return result

    def test_normal_v2_synthetic_pe_and_mocked_dependency(self):
        result, dependency_gate = self.fixture.validate()
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["profile"]["readWidth"], 16)
        witness = result["absentSelectorContextWitness"]
        self.assertIsNone(witness["rawSelector"])
        self.assertEqual(witness["serializedSelectorState"], "absent")
        self.assertEqual(witness["nativeAccessorDefault"], 0)
        self.assertEqual(witness["targetOwnedBytes"], 0)
        self.assertIn("serializedPolicy", result["absentSelectorEvidence"])
        dependency_gate.assert_called_once_with(game_root=self.fixture.game_root)

    def test_missing_additional_body_role_fails_closed(self):
        self.fixture.mutate_document(lambda doc: doc["additionalUnityPlayerRanges"].pop())
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "absence_range_roles")

    def test_missing_additional_pe_body_fails_closed(self):
        rva = self.fixture.additions["selector0PublicationArgumentsAndCall"][0]
        image = self.fixture.image_path.read_bytes()[: self.fixture.file_offset(rva)]
        self.fixture.image_path.write_bytes(image)
        self.fixture.rebase_image_hash_only()
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "absence:selector0PublicationArgumentsAndCall.bounded_range")

    def test_additional_roles_cannot_reuse_one_physical_span(self):
        self.fixture.additions["slot5ScopeWholeBody"] = self.fixture.additions["slot5SelectedMarker2EntryWholeBody"]
        self.fixture.write_documents()
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "absence_range_unique_rva_size")

    def test_missing_reused_role_fails_closed(self):
        self.fixture.mutate_document(lambda doc: doc["absencePathReusedRanges"].pop())
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "absence_reuse_roles")

    def test_mismatched_reused_role_identity_and_catalog_fail_closed(self):
        def mutate(doc: dict) -> None:
            row = next(
                row
                for row in doc["absencePathReusedRanges"]
                if row["contract"] == "base" and row["role"] == "callbackReset"
            )
            row["rva"] += 1

        self.fixture.mutate_document(mutate)
        result, _ = self.fixture.validate()
        gates = {row["gate"] for row in result["validationFailures"]}
        self.assertEqual(result["status"], "validation_failed")
        self.assertIn("absence_reuse:('base', 'callbackReset').identity", gates)
        self.assertIn("absence_reuse:('base', 'callbackReset').catalog", gates)

    def test_tampered_original_whole_body_fails_with_rebased_image_hash(self):
        result = self.tamper_image_and_rebase("selector9Slot4Reader", self.fixture.whole)
        self.assert_failed_closed(result, "selector9Slot4Reader.body_sha256")

    def test_tampered_new_scope_body_fails_with_rebased_image_hash(self):
        result = self.tamper_image_and_rebase("slot5ScopeWholeBody", self.fixture.additions)
        self.assert_failed_closed(result, "absence:slot5ScopeWholeBody.body_sha256")

    def test_tampered_selector0_registration_fails_with_rebased_image_hash(self):
        result = self.tamper_image_and_rebase("selector0Slot5Registration", self.fixture.additions)
        self.assert_failed_closed(result, "absence:selector0Slot5Registration.body_sha256")

    def test_explicit_raw_selector_zero_is_not_serialized_absence(self):
        self.fixture.mutate_document(
            lambda doc: doc["absentSelectorContextWitness"].__setitem__("rawSelector", 0)
        )
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "absent_selector_witness")

    def test_dependency_gate_failure_clears_v2_evidence(self):
        selected = {
            "status": "validation_failed",
            "validationFailures": [{"gate": "installed", "actual": "missing"}],
        }
        result, _ = self.fixture.validate(dependency_result=selected)
        self.assert_failed_closed(result, "dependency_native_gate")
        self.assertEqual(result["dependencyValidationFailures"][0]["gate"], "installed")

    def test_wrong_contract_hash_stops_before_dependency(self):
        result, dependency_gate = self.fixture.validate(expected_contract_sha="00" * 32)
        self.assert_failed_closed(result, "contract_sha256")
        dependency_gate.assert_not_called()



class Marker13NativeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = Fixture(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def assert_failed_closed(self, result: dict, gate: str) -> None:
        self.assertEqual(result["status"], "validation_failed")
        self.assertIsNone(result["profile"])
        self.assertIsNone(result["consumerReview"])
        self.assertTrue(any(row["gate"] == gate for row in result["validationFailures"]), result)

    def test_normal_synthetic_pe_and_mocked_dependency(self):
        result, dependency_gate = self.fixture.validate()
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["profile"]["dwordOffsets"], [0, 4, 8, 12])
        self.assertEqual(result["profile"]["allocatedSizeStatus"], "not-proven-by-native")
        self.assertIn("EOF", result["profile"]["extentStatus"])
        dependency_gate.assert_called_once_with(game_root=self.fixture.game_root)

    def test_missing_dependency_gate_fails_before_image_validation(self):
        selected = {"status": "validation_failed", "validationFailures": [{"gate": "installed", "actual": "missing"}]}
        result, _ = self.fixture.validate(dependency_result=selected)
        self.assert_failed_closed(result, "dependency_native_gate")
        self.assertEqual(result["dependencyValidationFailures"][0]["gate"], "installed")

    def test_mismatched_dependency_native_hash_fails_closed(self):
        selected = self.fixture.dependency_result()
        selected["nativeInputs"]["metadataSha256"] = "OTHER"
        result, _ = self.fixture.validate(dependency_result=selected)
        self.assert_failed_closed(result, "dependency_native_input:metadataSha256")

    def test_missing_explicit_unity_image_fails_closed(self):
        self.fixture.image_path.unlink()
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "marker13_contract_inputs")

    def test_tampered_whole_body_fails_even_when_image_hash_is_rebased(self):
        image = bytearray(self.fixture.image_path.read_bytes())
        rva = self.fixture.whole["selector9Slot4Reader"][0]
        image[self.fixture.file_offset(rva)] ^= 0xFF
        self.fixture.image_path.write_bytes(image)
        document = json.loads(self.fixture.contract_path.read_text())
        document["nativeInputs"]["unityPlayerSha256"] = sha256(image)
        self.fixture.contract_path.write_text(json.dumps(document), encoding="utf-8")
        self.fixture.inputs["unityPlayerSha256"] = sha256(image)
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "selector9Slot4Reader.body_sha256")

    def test_tampered_registration_fails_even_when_image_hash_is_rebased(self):
        image = bytearray(self.fixture.image_path.read_bytes())
        rva = self.fixture.registrations[5][0]
        image[self.fixture.file_offset(rva)] ^= 0xFF
        self.fixture.image_path.write_bytes(image)
        document = json.loads(self.fixture.contract_path.read_text())
        document["nativeInputs"]["unityPlayerSha256"] = sha256(image)
        self.fixture.contract_path.write_text(json.dumps(document), encoding="utf-8")
        self.fixture.inputs["unityPlayerSha256"] = sha256(image)
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "slot5.registration.exact_bytes")

    def test_malformed_profile_fails_closed_and_clears_profile(self):
        document = json.loads(self.fixture.contract_path.read_text())
        document["profile"]["readWidth"] = 12
        document["profile"]["allocatedSizeStatus"] = "proven"
        self.fixture.contract_path.write_text(json.dumps(document), encoding="utf-8")
        result, _ = self.fixture.validate()
        self.assert_failed_closed(result, "profile")

    def test_wrong_contract_hash_stops_before_dependency(self):
        result, dependency_gate = self.fixture.validate(expected_contract_sha="00" * 32)
        self.assert_failed_closed(result, "contract_sha256")
        dependency_gate.assert_not_called()



if __name__ == "__main__":
    unittest.main()
