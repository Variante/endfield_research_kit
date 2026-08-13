from __future__ import annotations

import struct
import unittest

from scripts.game_data.memorypack import buff as memorypack_buff
from scripts.game_data.memorypack.core import MEMORYPACK_NULL_COUNT
from scripts.game_data.memorypack.schemas import (
    BUFF_MEMBER_COUNT,
    MEMORYPACK_FIELD_SCHEMAS,
    SKILL_MEMBER_COUNT,
)


class CombatMemoryPackSchemaTests(unittest.TestCase):
    def test_current_schema_counts_and_new_fields_stay_in_sync(self) -> None:
        buff_schema = MEMORYPACK_FIELD_SCHEMAS["BuffData"]
        skill_schema = MEMORYPACK_FIELD_SCHEMAS["SkillData"]

        self.assertEqual(30, BUFF_MEMBER_COUNT)
        self.assertEqual(BUFF_MEMBER_COUNT, len(buff_schema))
        self.assertEqual("onlyUseSelfTimeDilation", buff_schema[21])
        self.assertEqual(47, SKILL_MEMBER_COUNT)
        self.assertEqual(SKILL_MEMBER_COUNT, len(skill_schema))
        self.assertEqual("aiExclusiveFrame", skill_schema[1])
        self.assertEqual("useAIExclusiveFrame", skill_schema[-1])

    def test_buff_post_id_suffix_consumes_self_time_dilation_flag(self) -> None:
        data = b"".join((
            b"\x00",  # ignoreCooldownWhenAdding
            b"\x01",  # ignoreTagImmune
            b"\x02",  # lifeType
            b"\x03",  # maxTriggerCnt member count
            struct.pack("<I", MEMORYPACK_NULL_COUNT),
            b"\x00",  # maxTriggerCnt.useBlackboardKey
            struct.pack("<i", 7),
            b"\x01",  # onlyUseSelfTimeDilation
            struct.pack("<I", 0),  # poiseModifier count
            struct.pack("<I", 0),  # shieldConfigs count
        ))

        decoded = memorypack_buff.read_buff_post_ignite_suffix(data, 0, {})

        self.assertTrue(decoded["onlyUseSelfTimeDilation"])
        self.assertEqual(0, decoded["poiseModifierCount"])
        self.assertEqual(7, decoded["maxTriggerCnt"]["value"])

    def test_skill_exact_tail_consumes_ai_exclusive_frame_flag(self) -> None:
        data = b"".join((
            b"\x00",  # switchToCenterBeforeCast
            struct.pack("<I", 0),  # tagDuringAttach count
            struct.pack("<I", 0),  # toggleBuffs count
            struct.pack("<I", 0),  # uiRangeHints count
            b"\x01",  # useAIExclusiveFrame
        ))

        decoded = memorypack_buff.decode_skill_post_switch_tail_at(data, 0, 0, "fixture")

        self.assertEqual("parsed-through-exact-tail", decoded["status"])
        self.assertTrue(decoded["exactLength"])
        self.assertTrue(decoded["useAIExclusiveFrame"])

    def test_current_stack_effect_action_boundary_and_nonempty_stacking_key(self) -> None:
        effect_name = b"P_fixture_stack_effect"
        fixed_bytes = 581
        action = bytearray(fixed_bytes + len(effect_name))
        action[0] = 17
        struct.pack_into("<I", action, 1, 1)
        struct.pack_into("<I", action, 18, 85)
        struct.pack_into("<I", action, 71, len(effect_name))
        action[75:75 + len(effect_name)] = effect_name
        struct.pack_into("<I", action, len(action) - 5, 4)
        action[-1] = 1
        stacking_key = b"FixtureStack"
        data = b"".join((
            b"\x01",
            struct.pack("<I", 1),
            bytes(action),
            struct.pack("<I", len(stacking_key)),
            stacking_key,
        ))

        decoded, end = memorypack_buff.skip_buff_stack_effects_effect_actions_body(data, 0, 1)

        self.assertEqual(5 + len(action), end)
        self.assertEqual({"17": 1}, decoded["effectActionMemberCountCounts"])
        self.assertEqual("FixtureStack", decoded["stackingKeyPreview"])
        self.assertEqual(
            "left-nonempty-string-for-stackingSettings",
            decoded["stackingKeyPrefixHandling"],
        )

    def test_buff_compact_tag_id_list_keeps_packed_ids(self) -> None:
        data = b"".join((
            b"\x00",
            struct.pack("<I", 2),
            struct.pack("<II", 0xA76C2448, 0xE269E5E2),
        ))

        decoded, end = memorypack_buff.read_buff_compact_tag_id_list_field(data, 0, "tags")

        self.assertEqual(len(data), end)
        self.assertEqual("compact-tag-id-list", decoded["branch"])
        self.assertEqual(["0xa76c2448", "0xe269e5e2"], decoded["tagIds"])

    def test_skill_member1_tags_are_id_only_and_preserve_following_counts(self) -> None:
        tags = b"".join(
            b"\x01" + struct.pack("<I", tag_id)
            for tag_id in (0x61F8280C, 0x0BA6F0A8, 0x1A17C9AA)
        )
        data = b"".join((
            b"\x01",  # switchToCenterBeforeCast
            struct.pack("<I", 3),
            tags,
            struct.pack("<I", 0),  # toggleBuffs count
            struct.pack("<I", 0),  # uiRangeHints count
            b"\x00",  # useAIExclusiveFrame
        ))

        decoded = memorypack_buff.decode_skill_post_switch_tail_at(data, 0, 0, "fixture")

        self.assertEqual("parsed-through-exact-tail", decoded["status"])
        self.assertTrue(decoded["exactLength"])
        self.assertEqual(0, decoded["toggleBuffsCount"])
        self.assertEqual(0, decoded["uiRangeHintsCount"])
        self.assertEqual(
            ["member1-id-only"] * 3,
            [tag["encoding"] for tag in decoded["tagDuringAttach"]["tags"]],
        )

    def test_current_energy_shard_nested_block_headers_are_accepted(self) -> None:
        tail_prefix = memorypack_buff.BUFF_IGNITE_NESTED_BLOCK_TAIL_PREFIX
        blocks = []
        for index, tail_code in enumerate((2, 3, 4, 5)):
            variants = (
                memorypack_buff.BUFF_IGNITE_NESTED_BLOCK_LONG_HEADERS
                if index < 3
                else memorypack_buff.BUFF_IGNITE_NESTED_BLOCK_SHORT_HEADERS
            )
            header = dict(variants)[f"energy-shard-{'long' if index < 3 else 'short'}-v2"]
            blocks.append(header + tail_prefix + bytes([tail_code]) + b"\x00\x00\x00")
        data = b"".join(blocks)

        decoded = memorypack_buff.validate_buff_ignite_nested_blocks(data, 0, len(data), 4)

        self.assertEqual(4, decoded["igniteEventActionNestedBlockCount"])
        self.assertEqual(
            ["energy-shard-long-v2"] * 3 + ["energy-shard-short-v2"],
            [block["header"] for block in decoded["igniteEventActionNestedBlocks"]],
        )


if __name__ == "__main__":
    unittest.main()
