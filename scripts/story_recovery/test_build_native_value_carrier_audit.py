from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "story_recovery" / "build_native_value_carrier_audit.py"
MAPPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = load("test_native_value_carrier_audit", SCRIPT)
mapper = load("test_native_value_carrier_mapper", MAPPER)


class NativeValueCarrierAuditTests(unittest.TestCase):
    def test_access_overlap_matches_nested_paths_and_chunk_writes(self) -> None:
        self.assertTrue(
            audit.access_overlaps_path(
                "this+0x20+0x60",
                "this",
                [0x20, 0x68],
                16,
                8,
            )
        )
        self.assertFalse(
            audit.access_overlaps_path(
                "this+0x10+0x60",
                "this",
                [0x20, 0x68],
                16,
                8,
            )
        )

    def test_stack_local_initializer_recovers_zeroed_fields_without_names(self) -> None:
        instructions = [
            {"offset": 0, "va": "0x1000", "text": "xorps xmm0, xmm0", "bytes": "0f 57 c0", "write": {"register": "xmm0", "value": "0"}},
            {"offset": 3, "va": "0x1003", "text": "xor eax, eax", "bytes": "33 c0", "write": {"register": "eax", "value": "0"}},
            {"offset": 5, "va": "0x1005", "text": "movaps [rbp-0x19], xmm0", "bytes": "0f 11 45 e7"},
            {"offset": 9, "va": "0x1009", "text": "movaps [rbp-0x9], xmm0", "bytes": "0f 11 45 f7"},
            {"offset": 13, "va": "0x100d", "text": "movaps [rbp+0x7], xmm0", "bytes": "0f 11 45 07"},
            {"offset": 17, "va": "0x1011", "text": "mov [rbp+0x17], rax", "bytes": "48 89 45 17"},
            {"offset": 21, "va": "0x1015", "text": "call 0x2000", "bytes": "e8 00 00 00 00"},
        ]
        focus = [
            {"name": "owner", "offset": 0x18, "width": 8},
            {"name": "script", "offset": 0x20, "width": 8},
            {"name": "selector", "offset": 0x28, "width": 8},
            {"name": "perform", "offset": 0x30, "width": 8},
        ]
        result = audit.local_initializer(
            mapper,
            instructions,
            len(instructions) - 1,
            {"localExpression": "rbp-0x19", "classification": "stack_local"},
            0x38,
            focus,
        )
        self.assertEqual(
            result["focusFieldStates"],
            {"owner": "zero", "script": "zero", "selector": "zero", "perform": "zero"},
        )

    def test_later_unknown_write_overrides_a_zero_chunk(self) -> None:
        instructions = [
            {"offset": 0, "va": "0x1000", "text": "xorps xmm0, xmm0", "bytes": "0f 57 c0", "write": {"register": "xmm0", "value": "0"}},
            {"offset": 3, "va": "0x1003", "text": "movaps [rbp+0x7], xmm0", "bytes": "0f 11 45 07"},
            {"offset": 7, "va": "0x1007", "text": "mov [rbp+0xf], rcx", "bytes": "48 89 4d 0f"},
            {"offset": 11, "va": "0x100b", "text": "call 0x2000", "bytes": "e8 00 00 00 00"},
        ]
        result = audit.local_initializer(
            mapper,
            instructions,
            len(instructions) - 1,
            {"localExpression": "rbp-0x19", "classification": "stack_local"},
            0x38,
            [{"name": "selector", "offset": 0x28, "width": 8}],
        )
        self.assertEqual(result["focusFieldStates"]["selector"], "unknown")


if __name__ == "__main__":
    unittest.main()
