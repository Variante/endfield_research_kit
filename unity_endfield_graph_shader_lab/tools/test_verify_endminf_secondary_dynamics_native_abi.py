from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_secondary_dynamics_native_abi.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_secondary_dynamics_native_abi", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def fixture(path: Path, corrupt: str | None = None) -> None:
    image = bytearray(0x1000)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", image, 0x84, 0x8664)
    struct.pack_into("<H", image, 0x86, 1)
    struct.pack_into("<H", image, 0x94, 0xF0)
    section = 0x80 + 24 + 0xF0
    image[section:section + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", image, section + 8,
                     0x800, 0x6726000, 0x800, 0x200)
    function = 0x200 + (MODULE.WRITE_TRANSFORM_RVA - 0x6726000)
    for name, (relative, expected_hex) in MODULE.WITNESSES.items():
        payload = bytes.fromhex(expected_hex)
        image[function + relative:function + relative + len(payload)] = payload
    if corrupt is not None:
        relative, _ = MODULE.WITNESSES[corrupt]
        image[function + relative] ^= 0xFF
    path.write_bytes(image)


class NativeAbiTests(unittest.TestCase):
    def test_complete_hidden_return_witness_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "GameAssembly.dll"
            fixture(path)
            report = MODULE.build_report(path, expected_sha256=None)
            self.assertEqual(
                report["status"], "validated_write_transform_hidden_return_abi")
            self.assertEqual(report["abi"]["instance"], "rdx")
            self.assertEqual(len(report["witnesses"]), len(MODULE.WITNESSES))

    def test_epilogue_store_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "GameAssembly.dll"
            fixture(path, corrupt="storeSixteenBytesToBuffer")
            with self.assertRaisesRegex(MODULE.VerificationError,
                                        "storeSixteenBytesToBuffer"):
                MODULE.build_report(path, expected_sha256=None)

    def test_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "GameAssembly.dll"
            fixture(path)
            with self.assertRaisesRegex(MODULE.VerificationError, "hash differs"):
                MODULE.build_report(path, expected_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
