from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("endfield_il2cpp_body_decoder", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Il2CppDecoderTests(unittest.TestCase):
    def test_truncated_terminal_instruction_is_retained_as_unknown_bytes(self) -> None:
        helper = load_helper()
        # REX.W + MOV r64,r/m64 + ModRM requesting a missing SIB byte.
        rows = helper.decode_x64_subset(b"\x48\x8b\x04", 0x180000000, stop_offset=3)

        self.assertEqual([0, 1, 2], [row["offset"] for row in rows])
        self.assertTrue(all(row.get("truncatedTerminal") for row in rows))
        self.assertEqual("db 0x48", rows[0]["text"])

    def test_body_summary_tracks_parameter_field_origin_into_call_arguments(self) -> None:
        helper = load_helper()
        start_va = 0x180000000
        target_va = 0x180000100
        prefix = bytes.fromhex("48 8b da 48 8b 53 18")
        call_offset = len(prefix)
        rel32 = target_va - (start_va + call_offset + 5)
        data = prefix + b"\xe8" + struct.pack("<i", rel32) + b"\xc3"
        row = {
            "flags": "0x0000",
            "parameterDetails": [{"name": "msg", "typeName": "Fixture"}],
            "method": "Handle_Fixture",
            "type": "FixtureSystem",
        }

        summary = helper.build_method_body_summary(
            row,
            data,
            start_va,
            {target_va: [{"type": "FixtureSystem", "method": "StartFixture"}]},
            max_instructions=64,
        )

        self.assertEqual(
            summary["calls"][0]["argumentOrigins"]["rdx"],
            "param:msg+0x18",
        )


if __name__ == "__main__":
    unittest.main()
