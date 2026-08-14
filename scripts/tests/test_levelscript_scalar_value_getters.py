from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.scalar_value_getters import (
    FLOAT_NEW_COMPARE,
    GETTER_INT,
    GETTER_STRING,
    INT_COMPARE,
    INT_EQUAL,
    INT_RANDOM,
    IS_ENDMIN_GENDER,
    decode_scalar_value_getter,
)


_PARAM_TAIL = struct.pack("<iii", -1, 0, -1)


def _i32(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + _PARAM_TAIL


def _float(value: float) -> bytes:
    return b"\x04" + struct.pack("<f", value) + _PARAM_TAIL


def _getter_ref(local_id: int) -> bytes:
    return b"\x04\x00\x00\x00\x00" + struct.pack("<i", local_id) + b"\xff" * 8


class LevelScriptScalarValueGetterTests(unittest.TestCase):
    def test_number_comparisons_keep_value_type_and_getter_identity(self) -> None:
        int_field, int_detail = decode_scalar_value_getter(
            _i32(2) + _getter_ref(17) + _i32(8),
            INT_COMPARE,
        )
        float_field, float_detail = decode_scalar_value_getter(
            _i32(4) + _getter_ref(19) + _float(1.25),
            FLOAT_NEW_COMPARE,
        )

        self.assertEqual("intCompare", int_field)
        self.assertEqual("int", int_detail["valueType"])
        self.assertEqual(17, int_detail["valueAGetterLocalId"])
        self.assertEqual("floatNewCompare", float_field)
        self.assertEqual("float", float_detail["valueType"])
        self.assertEqual(1.25, float_detail["valueB"]["value"])

    def test_integer_value_equal_and_random_getters(self) -> None:
        int_field, int_detail = decode_scalar_value_getter(_i32(12), GETTER_INT)
        equal_field, equal_detail = decode_scalar_value_getter(
            _getter_ref(7) + _i32(3),
            INT_EQUAL,
        )
        random_field, random_detail = decode_scalar_value_getter(
            _i32(10) + _i32(2),
            INT_RANDOM,
        )

        self.assertEqual(
            ("getterInt", 12),
            (int_field, int_detail["value"]["value"]),
        )
        self.assertEqual("intEqual", equal_field)
        self.assertEqual(7, equal_detail["valueAGetterLocalId"])
        self.assertEqual("intRandom", random_field)
        self.assertEqual(10, random_detail["maximum"]["value"])
        self.assertEqual(2, random_detail["minimum"]["value"])

    def test_string_and_gender_getters_keep_exact_shapes(self) -> None:
        path = b"result_property"
        string_payload = b"\x04" + struct.pack("<iiii", -1, -1, 0, len(path)) + path
        string_field, string_detail = decode_scalar_value_getter(
            string_payload,
            GETTER_STRING,
        )
        gender_field, gender_detail = decode_scalar_value_getter(
            _i32(1),
            IS_ENDMIN_GENDER,
        )

        self.assertEqual(
            ("getterString", "result_property"),
            (string_field, string_detail["path"]),
        )
        self.assertEqual("isEndminGender", gender_field)
        self.assertEqual("Female", gender_detail["genderName"])

    def test_unknown_or_malformed_payloads_fail_closed(self) -> None:
        self.assertEqual(("", {}), decode_scalar_value_getter(b"", (0xFFFF, 0xFF)))
        self.assertEqual(
            ("getterInt", {}),
            decode_scalar_value_getter(b"\x04", GETTER_INT),
        )
        self.assertEqual(
            ("intCompare", {}),
            decode_scalar_value_getter(_i32(0) + b"\x00" * 17, INT_COMPARE),
        )


if __name__ == "__main__":
    unittest.main()
