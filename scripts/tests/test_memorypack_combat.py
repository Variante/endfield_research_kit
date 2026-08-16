from __future__ import annotations

import struct
import unittest

from scripts.game_data.memorypack import buff as memorypack_buff
from scripts.game_data.memorypack.core import (
    MEMORYPACK_NULL_COUNT,
    scan_length_prefixed_utf8_string_hits,
    unique_strings,
)
from scripts.game_data.memorypack.schemas import (
    BUFF_MEMBER_COUNT,
    MEMORYPACK_FIELD_SCHEMAS,
    SKILL_MEMBER_COUNT,
)


class CombatMemoryPackSchemaTests(unittest.TestCase):
    def test_damage_action_is_not_a_streaming_consumer_without_item_boundary(self) -> None:
        self.assertNotIn(
            memorypack_buff.BUFF_DAMAGE_ACTION_TAG,
            memorypack_buff.BUFF_ABILITY_ACTION_CONSUME_DECODERS,
        )

    def test_single_item_uses_registered_consumer_with_proven_end(self) -> None:
        skill_id = b"eny_fixture_skill"
        blackboard_skill_id = (
            b"\x03" + struct.pack("<I", 0) + b"\x00"
            + struct.pack("<I", len(skill_id)) + skill_id
        )
        payload = b"".join((
            b"\x71\x05",
            b"\x01" + struct.pack("<iii", 0, 0, 0),
            struct.pack("<I", 1),
            blackboard_skill_id,
        ))

        status, items, note = memorypack_buff.split_buff_ability_action_items_opaque(
            payload, 0, len(payload), 1,
        )

        self.assertEqual("single-item", status)
        self.assertEqual("", note)
        self.assertEqual("exact", items[0]["decodeStatus"])
        self.assertEqual("exact-skill-id-condition", items[0]["decoded"]["semanticStatus"])

    def test_buff_gameplay_enum_values_follow_memorypack_zigzag(self) -> None:
        self.assertEqual(0, memorypack_buff.memorypack_signed_enum_value(0))
        self.assertEqual(-1, memorypack_buff.memorypack_signed_enum_value(1))
        self.assertEqual(1, memorypack_buff.memorypack_signed_enum_value(2))
        self.assertEqual(-6, memorypack_buff.memorypack_signed_enum_value(11))

    def test_create_buff_input_uses_first_bounded_authored_id_anchor(self) -> None:
        first_id = b"buff_chr_test_dynamic"
        later_id = b"buff_should_not_be_consumed"
        inherited_dynamic_value = b"\x01\x02\x00\x00\x00dynamic-value"
        first = b"".join((
            b"\x05\x01",
            struct.pack("<I", 2),
            inherited_dynamic_value,
            struct.pack("<I", len(first_id)),
            first_id,
            b"\x00" * memorypack_buff.BUFF_CREATE_BUFF_INPUT_TAIL_BYTES,
        ))
        later = b"".join((
            struct.pack("<I", len(later_id)),
            later_id,
            b"\x00" * memorypack_buff.BUFF_CREATE_BUFF_INPUT_TAIL_BYTES,
        ))

        decoded, end = memorypack_buff.read_buff_create_buff_input_partial(
            first + later,
            0,
            len(first + later),
            "createBuffInput",
        )

        self.assertEqual("buff_chr_test_dynamic", decoded["buffId"])
        self.assertEqual(len(first), end)
        self.assertGreaterEqual(decoded["boundedBuffIdCandidateCount"], 2)

    def test_target_settings_envelope_callers_expose_typed_default_fields(self) -> None:
        raw = bytes.fromhex(
            "0d 08 01 00 00 00 00 00 00 ff 00 00 00 00 ff 00 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
            "00 03 ff 00 00 00 00 00 00 00 00 00 00 00 00 01 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 "
            "00 00 00"
        )
        decoded, end = memorypack_buff.read_buff_target_settings_envelope_partial(
            raw, 0, len(raw), "fixture.targetSettings"
        )
        self.assertEqual(len(raw), end)
        self.assertEqual("exact", decoded["status"])
        self.assertEqual(4, decoded["targetSource"])
        self.assertEqual(1, decoded["selectorOwner"])
        self.assertEqual("exact-target-settings-selector-data", decoded["semanticStatus"])

    def test_modify_dynamic_blackboard_uses_current_native_enum_names(self) -> None:
        self.assertEqual(
            {
                0: "Assign",
                1: "Add",
                2: "Multiply",
                3: "Divide",
                4: "Floor",
                5: "Ceil",
                6: "RoundToInt",
            },
            memorypack_buff.BUFF_MODIFY_DYNAMIC_BLACKBOARD_OPERATION_NAMES,
        )
        self.assertEqual(
            {0: "HpRatio"},
            memorypack_buff.BUFF_MODIFY_DYNAMIC_BLACKBOARD_CALCULATION_TYPE_NAMES,
        )

    def test_modify_dynamic_blackboard_promotes_only_exact_target_settings(self) -> None:
        target_settings = bytearray.fromhex(
            "0d 08 01 00 00 00 00 00 00 ff 00 00 00 00 ff 00 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
            "00 03 ff 00 00 00 00 00 00 00 00 00 00 00 00 01 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 "
            "00 00 00"
        )

        def action(target: bytes) -> bytes:
            key = b"curr_duration"
            return b"".join((
                bytes([memorypack_buff.BUFF_MODIFY_DYNAMIC_BLACKBOARD_ACTION_TAG, 10]),
                b"\x01" + struct.pack("<iii", 0, 0, 0),
                struct.pack("<i", 0),
                target,
                b"\x01",
                struct.pack("<I", len(key)) + key,
                struct.pack("<i", 1),
                b"\x03" + struct.pack("<I", 0) + b"\x00" + struct.pack("<f", 0.5),
            ))

        exact_raw = action(bytes(target_settings))
        exact = memorypack_buff.decode_buff_modify_dynamic_blackboard_action(
            exact_raw, 0, len(exact_raw), 1, 10,
        )
        self.assertEqual("exact", exact["decodeStatus"])
        self.assertEqual("exact-modify-dynamic-blackboard-action", exact["semanticStatus"])
        self.assertEqual("exact", exact["calculationTarget"]["status"])
        self.assertEqual(
            "typed-member-cursor-validated-by-envelope",
            exact["calculationTarget"]["boundarySource"],
        )
        self.assertEqual("HpRatio", exact["calculateTypeName"])
        self.assertEqual("Add", exact["operationName"])
        chained = exact_raw + b"\x71\x05" + b"\x01" + struct.pack("<iii", 0, 0, 0)
        chained_decoded, chained_end = memorypack_buff.consume_buff_modify_dynamic_blackboard_action(
            chained, 0, len(chained), 1, 10,
        )
        self.assertEqual(len(exact_raw), chained_end)
        self.assertEqual("exact", chained_decoded["decodeStatus"])
        skill_id = b"eny_fixture_skill"
        check_skill = b"".join((
            b"\x71\x05",
            b"\x01" + struct.pack("<iii", 0, 0, 0),
            struct.pack("<I", 1),
            b"\x03" + struct.pack("<I", 0) + b"\x00"
            + struct.pack("<I", len(skill_id)) + skill_id,
        ))
        chain_status, chain_items, chain_note = memorypack_buff.split_buff_ability_action_items_opaque(
            exact_raw + check_skill, 0, len(exact_raw + check_skill), 2,
        )
        self.assertEqual("typed-chain-items", chain_status)
        self.assertEqual("", chain_note)
        self.assertEqual(
            ["exact-modify-dynamic-blackboard-action", "exact-skill-id-condition"],
            [item["decoded"]["semanticStatus"] for item in chain_items],
        )

        for cutoff in (18, 86, 107, len(exact_raw) - 1):
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                memorypack_buff.consume_buff_modify_dynamic_blackboard_action(
                    exact_raw + b"\xff" * 32, 0, cutoff, 1, 10,
                )

        target_settings[33] = 4  # Invalid SelectorData member count; bounded envelope remains known.
        partial_raw = action(bytes(target_settings))
        partial = memorypack_buff.decode_buff_modify_dynamic_blackboard_action(
            partial_raw, 0, len(partial_raw), 1, 10,
        )
        self.assertEqual("partial", partial["decodeStatus"])
        self.assertEqual("partial-calculation-target-settings-envelope-opaque", partial["semanticStatus"])
        self.assertEqual("partial", partial["calculationTarget"]["status"])
        with self.assertRaisesRegex(ValueError, "tail-at"):
            memorypack_buff.decode_buff_modify_dynamic_blackboard_action(
                exact_raw + b"\x00", 0, len(exact_raw) + 1, 1, 10,
            )

    def test_if_else_promotes_only_when_all_three_branches_are_typed_exact(self) -> None:
        skill_id = b"eny_fixture_skill"
        check_skill = b"".join((
            b"\x71\x05",
            b"\x01" + struct.pack("<iii", 0, 0, 0),
            struct.pack("<I", 1),
            b"\x03" + struct.pack("<I", 0) + b"\x00"
            + struct.pack("<I", len(skill_id)) + skill_id,
        ))
        sequence = b"\x03" + struct.pack("<I", 1) + check_skill + b"\x00\x00"
        raw = b"".join((
            bytes([memorypack_buff.BUFF_IF_ELSE_ACTION_TAG, 8]),
            b"\x01" + struct.pack("<iii", 0, 0, 0),
            b"\x00",
            sequence,
            sequence,
            sequence,
        ))

        decoded, error = memorypack_buff.decode_buff_best_effort_single_action_item(
            raw, 0, len(raw), memorypack_buff.BUFF_IF_ELSE_ACTION_TAG, 1, 8,
        )
        self.assertEqual("", error)
        self.assertEqual("exact", decoded["decodeStatus"])
        self.assertEqual("exact-if-else-action", decoded["semanticKind"])
        self.assertEqual("exact-if-else-action", decoded["semanticStatus"])
        self.assertTrue(
            all(
                memorypack_buff.buff_sequence_action_data_is_exact(decoded[key])
                for key in ("conditionAction", "failActions", "succeedActions")
            )
        )

        self.assertFalse(memorypack_buff.buff_sequence_action_data_is_exact({
            **decoded["conditionAction"],
            "actionDataItems": [{"decodeStatus": "partial", "boundaryProof": "typed-consumption"}],
        }))

        trailing_decoded, trailing_error = memorypack_buff.decode_buff_best_effort_single_action_item(
            raw + b"\x00", 0, len(raw) + 1,
            memorypack_buff.BUFF_IF_ELSE_ACTION_TAG, 1, 8,
        )
        self.assertIsNone(trailing_decoded)
        self.assertIn("end-mismatch", trailing_error)

        truncated_decoded, truncated_error = memorypack_buff.decode_buff_best_effort_single_action_item(
            raw[:15], 0, 15,
            memorypack_buff.BUFF_IF_ELSE_ACTION_TAG, 1, 8,
        )
        self.assertIsNone(truncated_decoded)
        self.assertIn("ifElseAction.alwaysNext", truncated_error)

        two_action_sequence = (
            b"\x03" + struct.pack("<I", 2) + check_skill + check_skill + b"\x00\x00"
        )
        chained_if_else = b"".join((
            bytes([memorypack_buff.BUFF_IF_ELSE_ACTION_TAG, 8]),
            b"\x01" + struct.pack("<iii", 0, 0, 0),
            b"\x00",
            two_action_sequence,
            sequence,
            two_action_sequence,
        ))
        outer_chain = chained_if_else + check_skill
        first, first_end = memorypack_buff.consume_buff_ability_action_item(
            outer_chain, 0, len(outer_chain), 0, 0,
        )
        second, second_end = memorypack_buff.consume_buff_ability_action_item(
            outer_chain, first_end, len(outer_chain), 1, 0,
        )
        self.assertEqual("exact-if-else-action", first["decoded"]["semanticKind"])
        self.assertEqual(2, first["decoded"]["conditionAction"]["actionDataCount"])
        self.assertEqual(2, first["decoded"]["succeedActions"]["actionDataCount"])
        self.assertEqual("exact", second["decodeStatus"])
        self.assertEqual("Core_Conditions_CheckSkillId_Data", second["name"])
        self.assertEqual(len(outer_chain), second_end)

    def test_convert_to_target_context_uses_current_native_enum_names(self) -> None:
        self.assertEqual("ConvertEntityToPosition", memorypack_buff.BUFF_CONVERT_TO_TARGET_CONTEXT_OPERATION_NAMES[1])
        self.assertEqual("ConvertBlackboardValueToPosition", memorypack_buff.BUFF_CONVERT_TO_TARGET_CONTEXT_OPERATION_NAMES[7])
        self.assertEqual("RotateAroundRefCW", memorypack_buff.BUFF_CONVERT_TO_TARGET_CONTEXT_TRANSLATE_OPERATION_NAMES[1])

    def test_compare_float_uses_current_native_compare_type_names(self) -> None:
        self.assertEqual(
            {0: "LT", 1: "LE", 2: "GT", 3: "GE", 4: "Equals"},
            memorypack_buff.BUFF_COMPARE_TYPE_NAMES,
        )

    def test_simple_calc_blackboard_reuses_current_operation_names(self) -> None:
        self.assertEqual("Add", memorypack_buff.BUFF_MODIFY_DYNAMIC_BLACKBOARD_OPERATION_NAMES[1])
        self.assertEqual("RoundToInt", memorypack_buff.BUFF_MODIFY_DYNAMIC_BLACKBOARD_OPERATION_NAMES[6])

    def test_spell_infliction_uses_current_energy_shard_names(self) -> None:
        self.assertEqual("Fire", memorypack_buff.BUFF_SPELL_INFLICTION_TYPE_NAMES[0])
        self.assertEqual("Natural", memorypack_buff.BUFF_SPELL_INFLICTION_TYPE_NAMES[3])
        self.assertEqual("Enum", memorypack_buff.BUFF_SPELL_INFLICTION_TYPE_NAMES[4])

    def test_selector_tag_query_reads_current_raw_tag_ids(self) -> None:
        data = b"".join((
            b"\x02",
            struct.pack("<i", 1),
            struct.pack("<I", 2),
            struct.pack("<ii", 0x10203040, -1),
        ))

        decoded, end = memorypack_buff.read_buff_selector_tag_query(
            data, 0, len(data), "query",
        )

        self.assertEqual(len(data), end)
        self.assertEqual([0x10203040, -1], [row["tagId"] for row in decoded["tags"]])

    def test_buff_empty_action_prefix_decodes_tags_and_attribute_modifiers_exactly(self) -> None:
        param_key = b"slow_ratio"
        data = b"".join((
            bytes([BUFF_MEMBER_COUNT]),
            struct.pack("<I", 0),  # abilityEventAction count
            b"\x03" + struct.pack("<I", 0) + b"\x00" + struct.pack("<f", 0.0),
            struct.pack("<I", 2),
            struct.pack("<II", 0x9A4868A1, 0x2E9DA07C),
            b"\x02",  # AttributeModifierData member count
            struct.pack("<I", 1),
            b"\x04",  # AttributeModifier member count
            struct.pack("<III", 13, 4, 0),
            b"\x03" + struct.pack("<I", len(param_key)) + param_key + b"\x01" + struct.pack("<f", 0.75),
            b"\x00",  # isConvertedAttribute
            b"opaque-before-id",
        ))
        id_boundary = len(data)

        decoded = memorypack_buff.decode_buff_pre_id_modifier_prefix(data, id_boundary)

        self.assertEqual("parsed-through-attribute-modifier", decoded["status"])
        self.assertEqual(["0x9a4868a1", "0x2e9da07c"], decoded["applyTags"]["tagIds"])
        modifier = decoded["attributeModifier"]["attributeModifiers"][0]
        self.assertEqual((13, 4, 0), (
            modifier["attributeType"],
            modifier["formulaItem"],
            modifier["modifyAttributeType"],
        ))
        self.assertEqual("slow_ratio", modifier["param"]["blackboardKey"])
        self.assertEqual(0.75, modifier["param"]["value"])

    def test_buff_nonempty_action_prefix_stops_at_exact_count(self) -> None:
        data = bytes([BUFF_MEMBER_COUNT]) + struct.pack("<I", 3) + b"opaque"

        decoded = memorypack_buff.decode_buff_pre_id_modifier_prefix(data, len(data))

        self.assertEqual("blocked-nonempty-ability-event-actions", decoded["status"])
        self.assertEqual(3, decoded["abilityEventActionCount"])
        self.assertNotIn("attributeModifier", decoded)

    def test_buff_skill_end_cooldown_chain_is_consumed_exactly(self) -> None:
        skill_id = b"eny_0090_wgabyss_skill03"
        blackboard_skill_id = (
            b"\x03" + struct.pack("<I", 0) + b"\x00"
            + struct.pack("<I", len(skill_id)) + skill_id
        )
        target_settings = bytes.fromhex(
            "0d 08 01 00 00 00 00 00 00 ff 00 00 00 00 ff 00 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
            "00 03 ff 00 00 00 00 00 00 00 00 00 00 00 00 01 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 "
            "00 00 00"
        )
        common_prefix = b"\x01" + struct.pack("<iii", 0, 0, 0)
        check_skill = b"".join((
            b"\x71\x05",
            common_prefix,
            struct.pack("<I", 1),
            blackboard_skill_id,
        ))
        set_cooldown = b"".join((
            b"\xfa" + struct.pack("<H", 0x0144) + b"\x0b",
            b"\x01" + struct.pack("<iii", 0, 0, 1),
            b"\x00",  # useSkillType
            struct.pack("<i", 0),  # SkillTypeMask.None
            struct.pack("<I", len(skill_id)) + skill_id,
            struct.pack("<i", 0),  # FunctionType.Reduce
            target_settings,
            b"\x00",  # isPercentage
            b"\x03" + struct.pack("<I", 0) + b"\x00" + struct.pack("<f", 5.0),
        ))
        data = b"".join((
            bytes([BUFF_MEMBER_COUNT]),
            struct.pack("<I", 1),
            b"\x02" + struct.pack("<iI", 31, 1),  # OnSkillEnd, one sequence
            b"\x03" + struct.pack("<I", 2) + check_skill + set_cooldown + b"\x00\x00",
            b"\x03" + struct.pack("<I", 0) + b"\x00" + struct.pack("<f", 0.0),
            struct.pack("<I", 0),
            b"\x02" + struct.pack("<I", 0) + b"\x00",
        ))

        decoded = memorypack_buff.decode_buff_pre_id_modifier_prefix(data, len(data))

        self.assertEqual("parsed-through-attribute-modifier", decoded["status"])
        event_map = decoded["abilityEventActions"][0]
        self.assertEqual(31, event_map["abilityEvent"])
        items = event_map["actions"][0]["actionDataItems"]
        self.assertEqual("eny_0090_wgabyss_skill03", items[0]["decoded"]["skillIdList"][0]["value"])
        cooldown = items[1]["decoded"]
        self.assertEqual("eny_0090_wgabyss_skill03", cooldown["skillId"])
        self.assertFalse(cooldown["isPercentage"])
        self.assertEqual(5.0, cooldown["value"]["value"])

    def test_buff_super_armor_marker_chain_is_consumed_exactly(self) -> None:
        target_settings = bytes.fromhex(
            "0d 08 01 00 00 00 00 00 00 ff 00 00 00 00 ff 00 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
            "00 03 ff 00 00 00 00 00 00 00 00 00 00 00 00 01 "
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 "
            "00 00 00"
        )
        common_prefix = b"\x01" + struct.pack("<iii", 0, 0, 0)
        super_armor_key = b"superarmor"
        check_super_armor = b"".join((
            b"\x75\x07",
            common_prefix,
            target_settings,
            struct.pack("<i", 3),
            b"\x03" + struct.pack("<I", len(super_armor_key)) + super_armor_key
            + b"\x01" + struct.pack("<f", 30.0),
        ))
        marker_id = b"hit_flash_cd"
        create_marker = b"".join((
            b"\x8e\x09",
            b"\x01" + struct.pack("<iii", 0, 0, 1),
            b"\x00",
            b"\x03" + struct.pack("<I", 0) + b"\x00" + struct.pack("<f", 0.25),
            b"\x03" + struct.pack("<I", 0) + b"\x00"
            + struct.pack("<I", len(marker_id)) + marker_id,
            target_settings,
            b"\x00",
        ))
        data = b"".join((
            bytes([BUFF_MEMBER_COUNT]),
            struct.pack("<I", 1),
            b"\x02" + struct.pack("<iI", 12, 1),
            b"\x03" + struct.pack("<I", 2) + check_super_armor + create_marker + b"\x00\x00",
            b"\x03" + struct.pack("<I", 0) + b"\x00" + struct.pack("<f", 0.0),
            struct.pack("<I", 0),
            b"\x02" + struct.pack("<I", 0) + b"\x00",
        ))

        decoded = memorypack_buff.decode_buff_pre_id_modifier_prefix(data, len(data))

        self.assertEqual("parsed-through-attribute-modifier", decoded["status"])
        items = decoded["abilityEventActions"][0]["actions"][0]["actionDataItems"]
        self.assertEqual(30.0, items[0]["decoded"]["value"]["value"])
        self.assertEqual("hit_flash_cd", items[1]["decoded"]["markerId"]["value"])
        self.assertEqual(0.25, items[1]["decoded"]["duration"]["value"])

    def test_keyed_blackboard_scan_keeps_exact_pre_id_values_only(self) -> None:
        key = b"duration"
        field = b"".join((
            b"\x03",
            struct.pack("<I", len(key)),
            key,
            b"\x01",
            struct.pack("<f", 15.0),
        ))
        data = b"\x1e" + field + b"opaque-id-tail"

        rows = memorypack_buff.scan_buff_blackboard_float_candidates_before_id(
            data,
            1 + len(field),
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("duration", rows[0]["blackboardKey"])
        self.assertEqual(15.0, rows[0]["value"])

    def test_shared_string_sampling_primitives_are_bounded(self) -> None:
        data = b"prefix" + struct.pack("<I", 5) + b"Alpha" + b"tail"

        self.assertEqual(
            scan_length_prefixed_utf8_string_hits(data, start=6),
            [{"offset": "0x6", "length": 5, "value": "Alpha"}],
        )
        self.assertEqual(unique_strings([" A ", "A", "", "B"], 2), ["A", "B"])

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
