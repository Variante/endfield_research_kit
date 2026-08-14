from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.control_flow_actions import (
    BRANCH_SEQUENCE,
    IF_ELSE,
    SPLIT,
    WHILE,
    decode_control_flow_action,
)


_PARAM_TAIL = struct.pack("<iii", -1, 0, -1)


class LevelScriptControlFlowActionTests(unittest.TestCase):
    def test_split_and_branch_keep_distinct_flow_roles(self) -> None:
        payload = struct.pack("<Iii", 2, 7, 11)
        split = decode_control_flow_action(payload, SPLIT)
        self.assertEqual([7, 11], split["splitActionLocalIds"])
        self.assertEqual("typed-split-action-list", split["branchRole"])

        branch = decode_control_flow_action(payload, BRANCH_SEQUENCE)
        self.assertEqual([7, 11], branch["branchSequenceActionLocalIds"])
        self.assertEqual("typed-branch-ordered-action-list", branch["sequenceRole"])

    def test_if_else_and_while_decode_exact_conditions(self) -> None:
        getter_condition = b"\x04\x01" + struct.pack("<i", 23) + b"\xff" * 8
        if_else = decode_control_flow_action(
            getter_condition + struct.pack("<ii", 31, 47),
            IF_ELSE,
        )
        self.assertEqual(23, if_else["conditionGetterLocalId"])
        self.assertEqual([47, 31], if_else["branchLocalRefs"])

        bool_condition = b"\x04\x01" + _PARAM_TAIL
        while_action = decode_control_flow_action(
            bool_condition + struct.pack("<i", 9),
            WHILE,
        )
        self.assertTrue(while_action["whileConditionParam"]["value"])
        self.assertEqual(9, while_action["whileDoActionLocalId"])
        self.assertEqual([9], while_action["branchLocalRefs"])

    def test_unknown_or_malformed_payloads_fail_closed(self) -> None:
        self.assertEqual({}, decode_control_flow_action(b"", SPLIT))
        self.assertEqual(
            {},
            decode_control_flow_action(struct.pack("<Ii", 1, 0), BRANCH_SEQUENCE),
        )
        self.assertEqual({}, decode_control_flow_action(bytes(20), (0xFFFF, 0xFF)))


if __name__ == "__main__":
    unittest.main()
