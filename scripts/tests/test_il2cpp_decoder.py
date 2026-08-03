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

    def test_body_summary_tracks_typed_call_return_into_later_field_read(self) -> None:
        helper = load_helper()
        start_va = 0x180000000
        getter_va = 0x180000100
        consumer_va = 0x180000200
        first_rel32 = getter_va - (start_va + 5)
        second_call_offset = 5 + 3 + 4
        second_rel32 = consumer_va - (start_va + second_call_offset + 5)
        data = (
            b"\xe8" + struct.pack("<i", first_rel32)
            + bytes.fromhex("48 8b d8")
            + bytes.fromhex("48 8b 4b 60")
            + b"\xe8" + struct.pack("<i", second_rel32)
            + b"\xc3"
        )
        summary = helper.build_method_body_summary(
            {
                "flags": "0x0000",
                "parameterDetails": [],
                "method": "ApplyFixture",
                "type": "FixtureSystem",
            },
            data,
            start_va,
            {
                getter_va: [{
                    "type": "FixtureSystem",
                    "method": "GetFixture",
                    "returnTypeName": "Fixture",
                }],
                consumer_va: [{
                    "type": "FixtureSystem",
                    "method": "ConsumeFixtureField",
                    "returnTypeName": "System.Void",
                }],
            },
            max_instructions=64,
        )

        self.assertEqual(summary["calls"][0]["returnOrigin"], "return:Fixture")
        self.assertEqual(
            summary["calls"][1]["argumentOrigins"]["rcx"],
            "return:Fixture+0x60",
        )
        self.assertTrue(any(
            row["origin"] == "return:Fixture+0x60"
            for row in summary["fieldAccesses"]
        ))

    def test_body_summary_restores_this_across_adjusted_stack_slot(self) -> None:
        helper = load_helper()
        start_va = 0x180000000
        data = bytes.fromhex(
            "48 89 4c 24 08 "  # mov [rsp+8], rcx
            "53 "              # push rbx
            "48 83 ec 20 "     # sub rsp, 20h
            "48 8b 74 24 30 "  # mov rsi, [rsp+30h] => entry rsp+8
            "48 8b 86 b8 00 00 00 "  # mov rax, [rsi+b8h]
            "48 83 c4 20 "     # add rsp, 20h
            "5b "              # pop rbx
            "c3"
        )
        summary = helper.build_method_body_summary(
            {
                "flags": "0x0000",
                "parameterDetails": [],
                "method": "ReadAfterSpill",
                "type": "FixtureAsset",
            },
            data,
            start_va,
            {},
            max_instructions=64,
        )

        self.assertTrue(any(
            row["origin"] == "this+0xb8"
            for row in summary["fieldAccesses"]
        ))
        self.assertEqual(summary["stackOriginFlow"]["spillCount"], 1)
        self.assertEqual(summary["stackOriginFlow"]["restoreCount"], 1)


if __name__ == "__main__":
    unittest.main()
