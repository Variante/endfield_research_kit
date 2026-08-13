from __future__ import annotations

import unittest

from scripts.story_builder.codecs.levelscript.call_server import (
    decode_call_server_action,
)


class LevelScriptCallServerTests(unittest.TestCase):
    def test_decodes_exact_six_field_prefix_with_callback_uids(self) -> None:
        payload = bytes.fromhex(
            "02 00 00 00 "
            "08 00 00 00 33 30 33 65 34 35 32 62 "
            "08 00 00 00 62 38 37 34 37 63 30 30 "
            "04 01 0a 00 00 00 65 76 65 6e 74 5f 61 72 67 73 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff "
            "04 09 00 00 00 23 65 65 63 39 35 63 35 37 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff 00 01 00"
        )
        detail = decode_call_server_action(payload)
        self.assertEqual(["303e452b", "b8747c00"], detail["callClientOutputUIDs"])
        self.assertEqual("event_args", detail["eventArgsPtr"]["pathValue"])
        self.assertEqual("#eec95c57", detail["eventName"])
        self.assertTrue(detail["waitForCallback"])
        self.assertEqual(len(payload), detail["consumedBytes"])
        self.assertEqual(0, detail["trailingBytes"])

    def test_rejects_invalid_member_shape_and_preserves_container_tail(self) -> None:
        payload = bytes.fromhex(
            "ff ff ff ff 04 01 01 00 00 00 61 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff "
            "04 01 00 00 00 62 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff 00 00 00 aa"
        )
        detail = decode_call_server_action(payload)
        self.assertEqual(1, detail["trailingBytes"])
        self.assertEqual({}, decode_call_server_action(payload[:-5] + b"\x00\x02\x00\xaa"))


if __name__ == "__main__":
    unittest.main()
