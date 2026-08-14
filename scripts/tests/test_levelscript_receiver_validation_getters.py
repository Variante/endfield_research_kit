from __future__ import annotations

import struct
import unittest

import scripts.story_builder.levelscript_binary as levelscript
from scripts.story_builder.codecs.levelscript import boolean_getters


PARAM_TAIL = struct.pack("<iii", -1, 0, -1)


def bool_param(value: bool, *, source: int = 0, path: str | None = None) -> bytes:
    if path is None:
        path_bytes = struct.pack("<i", -1)
    else:
        encoded = path.encode("ascii")
        path_bytes = struct.pack("<i", len(encoded)) + encoded
    return (
        b"\x04"
        + bytes([int(value)])
        + struct.pack("<ii", -1, source)
        + path_bytes
    )


def i32_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + PARAM_TAIL


def pure_bool_ref(local_id: int) -> bytes:
    return b"\x04\x00" + struct.pack("<i", local_id) + b"\xff" * 8


class ReceiverValidationGetterTests(unittest.TestCase):
    def test_boolean_compare_accepts_polymorphic_getter_operand(self):
        detail = boolean_getters.decode_boolean_compare(
            i32_param(0) + pure_bool_ref(12) + bool_param(False)
        )
        self.assertEqual("Equal", detail["comparerName"])
        self.assertEqual(12, detail["valueA"]["getterLocalId"])
        self.assertFalse(detail["valueB"]["value"])

    def test_boolean_combinators_decode_general_child_shapes(self):
        binary = boolean_getters.decode_binary(
            pure_bool_ref(3) + pure_bool_ref(8),
            operation="And",
        )
        self.assertEqual("And", binary["operation"])
        self.assertEqual(3, binary["valueA"]["getterLocalId"])
        self.assertEqual(8, binary["valueB"]["getterLocalId"])

        inverted = boolean_getters.decode_invert(pure_bool_ref(5))
        self.assertEqual("Not", inverted["operation"])
        self.assertEqual(5, inverted["value"]["getterLocalId"])

        all_values = boolean_getters.decode_multi_and(
            struct.pack("<I", 3)
            + pure_bool_ref(1)
            + pure_bool_ref(2)
            + pure_bool_ref(3)
        )
        self.assertEqual("All", all_values["operation"])
        self.assertEqual(
            [1, 2, 3],
            [value["getterLocalId"] for value in all_values["values"]],
        )

    def test_boolean_combinators_fail_closed_on_bad_count_or_trailing_byte(self):
        self.assertEqual(
            {},
            boolean_getters.decode_multi_and(struct.pack("<I", 0)),
        )
        self.assertEqual(
            {},
            boolean_getters.decode_invert(pure_bool_ref(5) + b"\x01"),
        )

    def test_getter_bool_keeps_property_path(self):
        detail = boolean_getters.decode_getter_bool(
            bool_param(False, source=100, path="03_01")
        )
        self.assertEqual("03_01", detail["value"]["path"])
        self.assertEqual(100, detail["value"]["paramSource"])

    def test_interactive_check_state_uses_repeated_entity_ptr_pattern(self):
        target = (
            b"\x04\x03"
            + struct.pack("<QI?", 0, 40001, True)
            + PARAM_TAIL
        )
        detail = levelscript._decode_interactive_check_state_getter(
            i32_param(0) + target + i32_param(1)
        )
        self.assertEqual("Equal", detail["comparerName"])
        self.assertEqual(40001, detail["target"]["slotId"])
        self.assertTrue(detail["target"]["useSlotId"])
        self.assertEqual(1, detail["value"]["value"])

    def test_get_lsm_completed_keeps_lossless_pointer_identity(self):
        lsm_param = b"\x04" + bytes.fromhex("03fb471408000000") + PARAM_TAIL
        script_param = b"\x04" + struct.pack("<QQ", 0, 0) + struct.pack(
            "<iii", -1, 1002, -1
        )
        detail = levelscript._decode_get_lsm_is_completed_getter(
            lsm_param + script_param
        )
        self.assertEqual("03fb471408000000", detail["lsmPtr"]["rawValueHex"])
        self.assertEqual("current_script", detail["scriptPtr"]["mode"])
        self.assertEqual("LevelScriptModule.isCompleted", detail["resultField"])

    def test_recursive_reference_collector_is_structure_driven(self):
        refs = levelscript._predicate_local_getter_refs({
            "valueA": {"getterLocalId": 4},
            "valueAGetterLocalId": 4,
            "values": [
                {"getterLocalId": 7},
                {"value": False},
            ],
        })
        self.assertEqual(
            [
                {"path": "valueA.getterLocalId", "getterLocalId": 4},
                {"path": "values[0].getterLocalId", "getterLocalId": 7},
            ],
            refs,
        )


if __name__ == "__main__":
    unittest.main()
