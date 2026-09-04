import struct
import tempfile
import unittest
from pathlib import Path

from scripts.game_data import terrain_native


def one_section_pe(*, virtual_size: int = 0x30, raw_size: int = 0x20) -> bytes:
    image = bytearray(0x400)
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", image, 0x86, 1)
    struct.pack_into("<H", image, 0x94, 0xE0)
    section = 0x80 + 24 + 0xE0
    image[section : section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", image, section + 8, virtual_size, 0x1000, raw_size, 0x200)
    return bytes(image)


class TerrainNativeTests(unittest.TestCase):
    def test_pe_rva_maps_only_bounded_raw_section_bytes(self):
        image = one_section_pe()
        self.assertEqual(0x210, terrain_native._pe_file_offset(image, 0x1010))
        with self.assertRaisesRegex(ValueError, "virtual-only"):
            terrain_native._pe_file_offset(image, 0x1025)

    def test_missing_contract_fails_closed_with_actionable_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            report = terrain_native.validate_terrain_native_contract(
                contract_path=missing
            )
        self.assertEqual("validation_failed", report["status"])
        failure = report["validationFailures"][0]
        self.assertEqual("read_valid_contract", failure["gate"])
        self.assertEqual(True, failure["expected"])


if __name__ == "__main__":
    unittest.main()
