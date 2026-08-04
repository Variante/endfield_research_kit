from __future__ import annotations

import struct
import unittest

from scripts.story_builder.levelscript_binary import (
    decode_levelscript_action_map_lists,
    levelscript_action_map_membership,
)


class LevelScriptActionMapListTests(unittest.TestCase):
    def test_exact_empty_map_keeps_later_uid_records_outside(self) -> None:
        data = bytearray(96)
        data[0:3] = b"\x1b\x02\x03"
        struct.pack_into("<III", data, 3, 0, 0, 0)
        records = [{
            "start": 32,
            "localId": 1,
            "nextId": -1,
            "code": 0,
            "kind": 0,
        }]

        action_map, membership = levelscript_action_map_membership(
            bytes(data),
            records,
        )

        self.assertTrue(action_map["exactEmptyActionMap"])
        self.assertEqual(action_map["emptyMapBoundaryEndOffset"], "0xf")
        self.assertEqual(
            action_map["listCounts"],
            {"actionList": 0, "getterList": 0, "headerList": 0},
        )
        self.assertEqual(membership, {})
        self.assertEqual(
            action_map["serializedLists"][-1]["status"],
            "residual-uid-records-after-exact-empty-map",
        )

    def test_empty_map_decodes_without_uid_records(self) -> None:
        data = b"\x1b\x02\x03" + struct.pack("<III", 0, 0, 0)

        action_map = decode_levelscript_action_map_lists(data, [])

        self.assertTrue(action_map["exactEmptyActionMap"])
        self.assertEqual(len(action_map["serializedLists"]), 3)
        self.assertEqual(
            [row["countOffset"] for row in action_map["serializedLists"]],
            ["0x3", "0x7", "0xb"],
        )


if __name__ == "__main__":
    unittest.main()
