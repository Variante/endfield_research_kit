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
    image = bytearray(0x1000)
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", image, 0x86, 1)
    struct.pack_into("<H", image, 0x94, 0xE0)
    section = 0x80 + 24 + 0xE0
    image[section:section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", image, section + 8, 0x800, 0x1000, 0x800, 0x200)
    return image


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.game_root = root / "selected/Endfield_Data"
        self.game_root.mkdir(parents=True)
        self.image_path = self.game_root.parent / "UnityPlayer.dll"
        self.dependency_path = root / "marker17.json"
        self.contract_path = root / "marker13.json"
        self.whole = {
            "selector9Slot4Reader": (0x1010, b"R4-whole"),
            "selector9Slot5Reader": (0x1030, b"R5-whole"),
            "slot4LocalFourDwordConsumer": (0x1050, b"C4-whole-body"),
            "slot5LocalFourDwordConsumer": (0x1080, b"C5-whole-body"),
        }
        self.registrations = {4: (0x10B0, b"register-slot4"), 5: (0x10D0, b"register-slot5")}
        self.literal = (0x10F0, struct.pack("<3I", 255, 0, 0))
        image = one_section_pe()
        for rva, body in list(self.whole.values()) + list(self.registrations.values()) + [self.literal]:
            offset = 0x200 + rva - 0x1000
            image[offset:offset + len(body)] = body
        self.image_path.write_bytes(image)
        self.write_documents()

    def file_offset(self, rva: int) -> int:
        return 0x200 + rva - 0x1000

    def write_documents(self) -> None:
        image = self.image_path.read_bytes()
        self.inputs = {"gameAssemblySha256": "GA", "metadataSha256": "MD",
                       "unityPlayerSha256": sha256(image)}
        dependency_document = {
            "schema": "fixture.marker17.v2", "status": "validated-conditional-static",
            "unityPlayerRanges": [{"role": "indexedCallbackAssignment"}],
            "selectedDefaultSlot3": [{"selector": 9,
                                      "descriptorConstructorSpan": {"bytesHex": "AA"},
                                      "publicationSpan": {"bytesHex": "BB"}}],
        }
        self.dependency_path.write_text(json.dumps(dependency_document), encoding="utf-8")
        self.dependency_sha = sha256(self.dependency_path.read_bytes())
        whole = []
        for role, (rva, body) in self.whole.items():
            whole.append({"role": role, "rva": rva, "fileOffset": self.file_offset(rva),
                          "size": len(body), "bodySha256": sha256(body),
                          "entryBytesHex": body[:4].hex().upper()})
        slots = []
        for slot, (rva, body) in self.registrations.items():
            reader_role = f"selector9Slot{slot}Reader"
            downstream_role = f"slot{slot}LocalFourDwordConsumer"
            slots.append({"selector": 9, "key": [255, 0, 0], "slot": slot,
                          "readerRva": self.whole[reader_role][0],
                          "readerRangeRole": reader_role, "downstreamRangeRole": downstream_role,
                          "registrationSpan": {"rva": rva, "fileOffset": self.file_offset(rva),
                                               "bytesHex": body.hex().upper()}})
        literal_rva, literal = self.literal
        document = {
            "schema": candidate.SCHEMA, "status": "validated-conditional-static",
            "nativeMappingId": "fixture-marker13",
            "dependency": {
                "schema": dependency_document["schema"], "sha256": self.dependency_sha,
                "requiredUnityPlayerRoles": ["indexedCallbackAssignment"],
                "requiredDefaultRegistration": {"selector": 9, "slot": 3,
                                                "reusedEvidence": ["descriptorConstructorSpan", "publicationSpan"]},
            },
            "nativeInputs": self.inputs, "unityPlayerRanges": whole,
            "keyLiteralRange": {"key": [255, 0, 0], "rva": literal_rva,
                                "fileOffset": self.file_offset(literal_rva),
                                "bytesHex": literal.hex().upper()},
            "selectedDefaultSlots": slots, "profile": copy.deepcopy(candidate.EXPECTED_PROFILE),
            "consumerReview": {"readQualification": "fixture"},
            "evidenceBoundary": {"unresolved": ["EOF"]},
        }
        self.contract_path.write_text(json.dumps(document), encoding="utf-8")

    def dependency_result(self) -> dict:
        return {"status": "validated", "contractSha256": self.dependency_sha,
                "nativeInputs": dict(self.inputs), "validationFailures": []}

    def validate(self, *, dependency_result=None, expected_contract_sha=None):
        document = json.loads(self.contract_path.read_text())
        expected_inputs = document["nativeInputs"]
        expected_whole = {role: (rva, len(body)) for role, (rva, body) in self.whole.items()}
        expected_slots = {
            4: (self.whole["selector9Slot4Reader"][0], "selector9Slot4Reader", "slot4LocalFourDwordConsumer"),
            5: (self.whole["selector9Slot5Reader"][0], "selector9Slot5Reader", "slot5LocalFourDwordConsumer"),
        }
        dependency_result = self.dependency_result() if dependency_result is None else dependency_result
        dependency_gate = mock.Mock(return_value=dependency_result)
        with mock.patch.object(candidate, "CONTRACT_SHA256", expected_contract_sha or sha256(self.contract_path.read_bytes())), \
             mock.patch.object(candidate, "DEPENDENCY_SHA256", self.dependency_sha), \
             mock.patch.object(candidate, "EXPECTED_INPUTS", expected_inputs), \
             mock.patch.object(candidate, "EXPECTED_WHOLE", expected_whole), \
             mock.patch.object(candidate, "EXPECTED_SLOTS", expected_slots), \
             mock.patch.object(candidate.dependency, "DEFAULT_CONTRACT", self.dependency_path), \
             mock.patch.object(candidate.dependency, "validate_marker17_native_contract", dependency_gate):
            result = candidate.validate_marker13_native_contract(
                game_root=self.game_root, contract_path=self.contract_path)
        return result, dependency_gate


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
