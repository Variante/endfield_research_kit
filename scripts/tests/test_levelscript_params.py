from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.params import (
    DEFAULT_PARAM_TAIL,
    decode_constant_string_param,
    decode_param_tail,
)


class LevelScriptParamCodecTests(unittest.TestCase):
    def test_default_tail(self) -> None:
        self.assertEqual(
            ({"idRef": -1, "paramSource": 0, "path": None}, 12),
            decode_param_tail(DEFAULT_PARAM_TAIL, 0),
        )

    def test_dynamic_path_tail(self) -> None:
        payload = struct.pack("<iii", 7, 200, 5) + b"value"
        self.assertEqual(
            ({"idRef": 7, "paramSource": 200, "path": "value"}, len(payload)),
            decode_param_tail(payload, 0),
        )

    def test_tail_rejects_invalid_source_and_truncation(self) -> None:
        self.assertIsNone(decode_param_tail(struct.pack("<iii", -1, -1, -1), 0))
        self.assertIsNone(decode_param_tail(DEFAULT_PARAM_TAIL[:-1], 0))

    def test_constant_string(self) -> None:
        payload = b"\x04" + struct.pack("<i", 5) + b"radio" + DEFAULT_PARAM_TAIL
        self.assertEqual(("radio", len(payload)), decode_constant_string_param(payload, 0))

    def test_constant_string_rejects_nondefault_tail(self) -> None:
        payload = b"\x04" + struct.pack("<i", 5) + b"radio" + bytes(12)
        self.assertIsNone(decode_constant_string_param(payload, 0))


if __name__ == "__main__":
    unittest.main()
