from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
