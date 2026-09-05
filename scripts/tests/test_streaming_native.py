import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import InstalledNativeInputs
from scripts.game_data import streaming_native


def _one_section_pe() -> bytearray:
    image = bytearray(0x400)
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", image, 0x86, 1)
    struct.pack_into("<H", image, 0x94, 0xE0)
    section = 0x80 + 24 + 0xE0
    image[section : section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", image, section + 8, 0x100, 0x1000, 0x100, 0x200)
    return image


class StreamingNativeTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, InstalledNativeInputs]:
        game_root = root / "Endfield_Data"
        metadata = game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
        metadata.parent.mkdir(parents=True)
        metadata.write_bytes(b"metadata")
        gameassembly = root / "GameAssembly.dll"
        gameassembly.write_bytes(b"gameassembly")
        image = _one_section_pe()
        image[0x210:0x214] = b"ABCD"
        image[0x214:0x218] = b"EFGH"
        diagnostic = b"layout diagnostic\0"
        image[0x220 : 0x220 + len(diagnostic)] = diagnostic
        unity_player = root / "UnityPlayer.dll"
        unity_player.write_bytes(image)
        contract = {
            "schema": streaming_native.SCHEMA,
            "status": "validated",
            "nativeMappingId": "fixture",
            "nativeInputs": {
                "gameAssemblySha256": "GA",
                "metadataSha256": "MD",
                "unityPlayerSha256": hashlib.sha256(image).hexdigest().upper(),
            },
            "unityPlayerRanges": [
                {
                    "role": "fixtureAccessor",
                    "rva": 0x1010,
                    "fileOffset": 0x210,
                    "size": 4,
                    "bodySha256": hashlib.sha256(b"ABCD").hexdigest().upper(),
                    "entryBytesHex": b"ABCD".hex().upper(),
                },
                {
                    "role": "fixtureField5Consumer",
                    "rva": 0x1014,
                    "fileOffset": 0x214,
                    "size": 4,
                    "bodySha256": hashlib.sha256(b"EFGH").hexdigest().upper(),
                    "entryBytesHex": b"EFGH".hex().upper(),
                }
            ],
            "rowLayout": [{"fieldIndex": 0, "representation": "scalar32"}],
            "utf8Strings": [
                {
                    "role": "fixtureCarrierPath",
                    "rva": 0x1020,
                    "text": "layout diagnostic",
                }
            ],
            "consumerObservations": {
                "diagnosticRva": 0x1020,
                "diagnosticUtf8": "layout diagnostic",
            },
            "evidenceBoundary": {},
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
        contract_path = root / "contract.json"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        native = InstalledNativeInputs(
            gameassembly=gameassembly,
            metadata=metadata,
            gameassembly_sha256="GA",
            metadata_sha256="MD",
            status="validated",
            detail="fixture",
        )
        return game_root, contract_path, native

    def test_validates_bounded_native_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, contract_path, native = self._fixture(Path(directory))
            contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
            with (
                patch.object(streaming_native, "CONTRACT_SHA256", contract_hash),
                patch.object(
                    streaming_native,
                    "check_installed_native_inputs",
                    return_value=native,
                ),
            ):
                report = streaming_native.validate_streaming_field2_native_contract(
                    contract_path=contract_path, game_root=game_root
                )
        self.assertEqual("validated", report["status"])
        self.assertEqual([], report["validationFailures"])

    def test_changed_accessor_body_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, contract_path, native = self._fixture(Path(directory))
            contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
            unity_player = native.gameassembly.parent / "UnityPlayer.dll"
            image = bytearray(unity_player.read_bytes())
            image[0x210] ^= 0xFF
            unity_player.write_bytes(image)
            with (
                patch.object(streaming_native, "CONTRACT_SHA256", contract_hash),
                patch.object(
                    streaming_native,
                    "check_installed_native_inputs",
                    return_value=native,
                ),
            ):
                report = streaming_native.validate_streaming_field2_native_contract(
                    contract_path=contract_path, game_root=game_root
                )
        self.assertEqual("validation_failed", report["status"])
        self.assertTrue(
            any(
                failure["gate"] == "fixtureAccessor.body_sha256"
                for failure in report["validationFailures"]
            )
        )

    def test_changed_field5_consumer_body_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, contract_path, native = self._fixture(Path(directory))
            contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
            unity_player = native.gameassembly.parent / "UnityPlayer.dll"
            image = bytearray(unity_player.read_bytes())
            image[0x214] ^= 0xFF
            unity_player.write_bytes(image)
            with (
                patch.object(streaming_native, "CONTRACT_SHA256", contract_hash),
                patch.object(
                    streaming_native,
                    "check_installed_native_inputs",
                    return_value=native,
                ),
            ):
                report = streaming_native.validate_streaming_field2_native_contract(
                    contract_path=contract_path, game_root=game_root
                )
        self.assertEqual("validation_failed", report["status"])
        self.assertTrue(
            any(
                failure["gate"] == "fixtureField5Consumer.body_sha256"
                for failure in report["validationFailures"]
            )
        )

    def test_changed_carrier_string_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, contract_path, native = self._fixture(Path(directory))
            contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
            unity_player = native.gameassembly.parent / "UnityPlayer.dll"
            image = bytearray(unity_player.read_bytes())
            image[0x220] ^= 0xFF
            unity_player.write_bytes(image)
            with (
                patch.object(streaming_native, "CONTRACT_SHA256", contract_hash),
                patch.object(
                    streaming_native,
                    "check_installed_native_inputs",
                    return_value=native,
                ),
            ):
                report = streaming_native.validate_streaming_field2_native_contract(
                    contract_path=contract_path, game_root=game_root
                )
        self.assertEqual("validation_failed", report["status"])
        self.assertTrue(
            any(
                failure["gate"] == "fixtureCarrierPath.utf8"
                for failure in report["validationFailures"]
            )
        )

    def test_missing_contract_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            report = streaming_native.validate_streaming_field2_native_contract(
                contract_path=Path(directory) / "missing.json"
            )
        self.assertEqual("validation_failed", report["status"])
        self.assertEqual("read_valid_contract", report["validationFailures"][0]["gate"])

    def test_bounded_native_span_rejects_invalid_ranges(self):
        image = _one_section_pe()
        self.assertEqual((0x210, bytes(image[0x210:0x214])), streaming_native._bounded_pe_range(image, 0x1010, 4))
        for rva, size in ((-1, 4), (0x1010, 0), (0x1010, -4), (0x10FE, 4)):
            with self.subTest(rva=rva, size=size), self.assertRaisesRegex(ValueError, "expected.*actual"):
                streaming_native._bounded_pe_range(image, rva, size)
        with self.assertRaisesRegex(ValueError, "expected end.*actual"):
            streaming_native._bounded_pe_range(image[:0x212], 0x1010, 4)
        # Appended bytes cannot make a span outside the section readable.
        with self.assertRaisesRegex(ValueError, "crossing section"):
            streaming_native._bounded_pe_range(image + b"tail", 0x10FE, 4)

    def test_context_evidence_is_withheld_after_native_body_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, contract_path, native = self._fixture(Path(directory))
            contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
            with (
                patch.object(streaming_native, "CONTRACT_SHA256", contract_hash),
                patch.object(streaming_native, "check_installed_native_inputs", return_value=native),
            ):
                report = streaming_native.validate_streaming_field2_native_contract(contract_path=contract_path, game_root=game_root)
                self.assertEqual("validated", report["status"])
                self.assertEqual("unresolved", report["nestedContextObservations"]["marker15SelectionStatus"])
                self.assertEqual("unresolved", report["nestedContextObservations"]["recordExtentStatus"])
                phase = report["nestedReaderPhaseObservations"]
                self.assertEqual(phase["sourceRoot"], "second-secondary-root")
                self.assertEqual(phase["marker15WidthStatus"], "unresolved")
                self.assertEqual(phase["targetOwnedBytes"], 0)
                unity = native.gameassembly.parent / "UnityPlayer.dll"
                unity.write_bytes(unity.read_bytes()[:0x212])
                report = streaming_native.validate_streaming_field2_native_contract(contract_path=contract_path, game_root=game_root)
        self.assertEqual("validation_failed", report["status"])
        self.assertIsNone(report["nestedContextObservations"])
        self.assertIsNone(report["nestedReaderPhaseObservations"])


if __name__ == "__main__":
    unittest.main()
