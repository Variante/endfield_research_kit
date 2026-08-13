from __future__ import annotations

import unittest

from scripts.story_builder.codecs.levelscript.script_stage_changed import (
    decode_script_stage_changed_fields,
)
from scripts.story_builder.levelscript_binary import decode_levelscript_record_payload


class LevelScriptStageChangedTests(unittest.TestCase):
    def test_owner_decodes_exact_mapping_and_dispatcher_matches(self) -> None:
        data = bytearray(54)
        data[4] = 1
        data[5:9] = (23).to_bytes(4, "little", signed=True)
        data[17:19] = b"\x04\x01"
        data[19:23] = (10).to_bytes(4, "little", signed=True)
        data[23:27] = (-1).to_bytes(4, "little", signed=True)
        data[27:31] = (-1).to_bytes(4, "little", signed=True)
        data[31:36] = b"\xff\x00\x00\x00\x00"
        data[36] = 4
        data[37:41] = (3).to_bytes(4, "little", signed=True)
        data[41:45] = (-1).to_bytes(4, "little", signed=True)
        data[45:49] = (0).to_bytes(4, "little", signed=True)
        data[49:53] = (-1).to_bytes(4, "little", signed=True)
        data[53] = 0xFF
        payload = bytes(data)
        owner = decode_script_stage_changed_fields(
            payload,
            "ScriptEvent_OnScriptStageChanged",
        )
        decoded = decode_levelscript_record_payload(
            payload,
            {
                "start": 0,
                "payloadStart": 0,
                "code": 0x12C9,
                "kind": 0,
                "unionTag": 0xC9,
                "serializedMemberCount": 18,
                "localId": 22,
                "nextId": 0,
                "plainStrings": [],
            },
            next_start=len(payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual(3, owner["newStageFilter"])
        self.assertFalse(owner["newStageOutputPresent"])
        for key, value in owner.items():
            self.assertEqual(value, decoded[key])
        self.assertEqual(
            {},
            decode_script_stage_changed_fields(payload, "ScriptEvent_OnScriptActive"),
        )


if __name__ == "__main__":
    unittest.main()
