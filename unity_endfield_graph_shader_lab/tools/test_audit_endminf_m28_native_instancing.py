#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("audit_endminf_m28_native_instancing.py")
SPEC = importlib.util.spec_from_file_location(
    "audit_endminf_m28_native_instancing", MODULE_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AuditEndminfM28NativeInstancingTests(unittest.TestCase):
    def test_keyword_table_uses_exact_16_byte_entries(self) -> None:
        data = bytearray(512)
        names = ("INSTANCING_ON", "SRP_INSTANCING_ON", "VERTEX_SKINNING_ON")
        offsets = (256, 288, 320)
        for index, (name, offset) in enumerate(zip(names, offsets)):
            encoded = name.encode("ascii") + b"\0"
            data[offset : offset + len(encoded)] = encoded
            struct.pack_into("<QQ", data, index * 16, offset, 0)
        self.assertEqual(
            MODULE.read_keyword_table(bytes(data), 0, 3, lambda value: value),
            list(names),
        )

    def test_keyword_auxiliary_lane_fails_closed(self) -> None:
        data = bytearray(128)
        data[64:69] = b"TEST\0"
        struct.pack_into("<QQ", data, 0, 64, 1)
        with self.assertRaisesRegex(MODULE.AuditError, "auxiliary lane"):
            MODULE.read_keyword_table(bytes(data), 0, 1, lambda value: value)

    def test_exact_instance_contract_is_rederived(self) -> None:
        contract = MODULE.validate_instance_contract()
        self.assertEqual(contract["recordBytes"], 256)
        self.assertEqual(contract["capacity"], 256)
        self.assertFalse(contract["shaderSideBaseOffset"])
        self.assertEqual(contract["sourceConsumerBurstCount"], 1)


if __name__ == "__main__":
    unittest.main()
