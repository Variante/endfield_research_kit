from __future__ import annotations

import unittest

from scripts.story_builder.levelscript_binary import (
    _decode_manual_levelscript_control,
)


class LevelScriptManualControlTests(unittest.TestCase):
    def test_default_operands_preserve_both_numeric_param_sources(self) -> None:
        payload = (
            b"\x04"
            + b"\xff" * 8
            + (1000).to_bytes(4, "little", signed=True)
            + b"\xff" * 4
            + b"\x04"
            + b"\x00" * 16
            + b"\xff" * 4
            + (1002).to_bytes(4, "little", signed=True)
            + b"\xff" * 4
        )

        decoded = _decode_manual_levelscript_control(
            payload,
            "manual-start",
        )

        self.assertEqual(
            decoded["parameterSources"],
            {"levelId": 1000, "scriptId": 1002},
        )
        self.assertEqual(
            decoded["payloadShape"],
            "manual-levelscript-default-operands",
        )

    def test_unknown_payload_does_not_invent_param_sources(self) -> None:
        decoded = _decode_manual_levelscript_control(
            bytes(range(46)),
            "manual-start",
        )

        self.assertNotIn("parameterSources", decoded)


if __name__ == "__main__":
    unittest.main()
