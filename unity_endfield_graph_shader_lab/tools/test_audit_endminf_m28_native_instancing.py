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

    def test_static_search_keeps_bit30_false_positive_separate(self) -> None:
        self.assertNotIn(
            MODULE.SRP_KEYWORD_ORDINAL,
            MODULE.DEFAULT_BUILTIN_ORDINALS,
        )
        self.assertIn(
            bytes.fromhex("0fbae81e"),
            MODULE.KEYWORD_ID_BIT30_SEQUENCE,
        )
        self.assertEqual(MODULE.DEFAULT_BUILTIN_ORDINALS, (35, 33, 36, 37))

    def test_direct_call_gate_fails_on_wrong_target(self) -> None:
        data = bytearray(32)
        data[4] = 0xE8
        struct.pack_into("<i", data, 5, 7)
        sections = [{
            "virtualAddress": 0,
            "virtualSize": len(data),
            "rawSize": len(data),
            "rawOffset": 0,
        }]
        MODULE.require_rel32_call(bytes(data), 4, 16, 0, sections)
        with self.assertRaisesRegex(MODULE.AuditError, "target drifted"):
            MODULE.require_rel32_call(bytes(data), 4, 17, 0, sections)


if __name__ == "__main__":
    unittest.main()
