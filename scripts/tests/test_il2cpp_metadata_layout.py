from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"


def load_metadata_module():
    spec = importlib.util.spec_from_file_location("endfield_metadata_catalog", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Il2CppMetadataLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metadata = load_metadata_module()

    def test_endfield_v29_type_definition_uses_measured_92_byte_layout(self) -> None:
        prefix_words = (11, 12, 13, 14, 15, 16, 17)
        flags = 0x00101081
        starts = tuple(range(101, 109))
        extra_index = 31337
        counts = tuple(range(201, 209))
        bitfield = 0x00001803
        token = 0x0200002A
        record = (
            struct.pack("<7iI8ii8HII", *prefix_words, flags, *starts, extra_index, *counts, bitfield, token)
        )

        prefix = self.metadata.parse_type_reference_prefix(record, 0, 92)
        self.assertEqual((11, 12, 13, None, 14, 15, 16, 17, 28), prefix)

        tail = self.metadata.parse_type_layout_tail(record, prefix[-1], 92)
        self.assertEqual(flags, tail[0])
        self.assertEqual(starts, tail[1])
        self.assertEqual(extra_index, tail[2])
        self.assertEqual(counts, tail[3])
        self.assertEqual(bitfield, tail[4])
        self.assertEqual(token, tail[5])
        self.assertEqual(92, tail[6])

    def test_stock_88_byte_layout_has_no_extra_slot(self) -> None:
        prefix_words = (1, 2, 3, -1, 5, 6, -1)
        starts = tuple(range(8))
        counts = tuple(range(8))
        record = struct.pack(
            "<7iI8i8HII",
            *prefix_words,
            0x81,
            *starts,
            *counts,
            1,
            0x02000001,
        )

        prefix = self.metadata.parse_type_reference_prefix(record, 0, 88)
        tail = self.metadata.parse_type_layout_tail(record, prefix[-1], 88)
        self.assertIsNone(tail[2])
        self.assertEqual(88, tail[6])


if __name__ == "__main__":
    unittest.main()
