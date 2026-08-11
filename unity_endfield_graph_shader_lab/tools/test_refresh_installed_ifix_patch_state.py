import struct
import unittest
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("refresh_installed_ifix_patch_state.py")
SPEC = importlib.util.spec_from_file_location("refresh_installed_ifix_patch_state", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
discover_patch_layout = MODULE.discover_patch_layout
find_bridge_offset = MODULE.find_bridge_offset


def encode_string(value: str) -> bytes:
    payload = value.encode("utf-8")
    length = len(payload)
    out = bytearray()
    while length >= 0x80:
        out.append((length & 0x7F) | 0x80)
        length >>= 7
    out.append(length)
    out.extend(payload)
    return bytes(out)


def synthetic_patch() -> bytes:
    data = bytearray(b"\x00" * 0x88)
    data.extend(encode_string("IFix.ILFixInterfaceBridge, Gameplay.Beyond"))
    types = ["Beyond.Test.Actor, Gameplay.Beyond", "System.Int32"]
    data.extend(struct.pack("<i", len(types)))
    for value in types:
        data.extend(encode_string(value))
    data.extend(struct.pack("<i", 1))
    data.extend(b"\x00")
    data.extend(struct.pack("<i", 0))
    data.extend(encode_string("Tick"))
    data.extend(struct.pack("<i", 1))
    data.extend(struct.pack("<i", 1))
    data.extend(struct.pack("<i", 7))
    data.extend(struct.pack("<i", 0))
    return bytes(data)


class RefreshIfixPatchTests(unittest.TestCase):
    def test_discovers_bridge_and_unique_target_table(self) -> None:
        payload = synthetic_patch()
        self.assertEqual(find_bridge_offset(payload), 0x88)
        targets, layout = discover_patch_layout(payload)
        self.assertEqual(layout["target_count"], 1)
        self.assertEqual(layout["terminal_int32"], 0)
        self.assertEqual(targets[0]["type"], "Beyond.Test.Actor")
        self.assertEqual(targets[0]["parameters"], ["System.Int32"])
        self.assertEqual(targets[0]["implementation_index"], 7)

    def test_rejects_payload_without_a_self_terminating_target_table(self) -> None:
        payload = synthetic_patch()[:-4] + struct.pack("<i", 1)
        with self.assertRaises(ValueError):
            discover_patch_layout(payload)


if __name__ == "__main__":
    unittest.main()
