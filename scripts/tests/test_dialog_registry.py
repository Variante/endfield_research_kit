import unittest

from scripts.story_builder.dialog_registry import (
    build_index,
    extract_dialog_brief_info_records,
    extract_used_dialog_timeline_ids,
)


class DialogRegistryTests(unittest.TestCase):
    def test_option_only_identifier_does_not_register_dialog_scene(self):
        payload = b"option_dlg_test_3_001"

        self.assertEqual(build_index(payload), {})

    def test_root_and_per_line_tokens_still_register(self):
        payload = b"dlg_test dlg_test_1_001 option_dlg_test_3_001"

        index = build_index(payload)
        self.assertEqual(set(index), {"dlg_test"})
        self.assertTrue(index["dlg_test"]["hasRootKey"])
        self.assertFalse(index["dlg_test"]["memoryPackRecordKey"])
        self.assertEqual(
            ["printable_root_token", "printable_line_token"],
            index["dlg_test"]["registrationEvidence"],
        )
        self.assertEqual(index["dlg_test"]["linesByTrunk"], {"1": ["dlg_test_1_001"]})
        self.assertEqual(
            index["dlg_test"]["optionsByGroup"],
            {"3": ["option_dlg_test_3_001"]},
        )

    def test_used_timeline_ids_stay_inside_their_validated_map_value(self):
        def text(value: str) -> bytes:
            raw = value.encode("ascii")
            return len(raw).to_bytes(4, "little", signed=True) + raw

        def brief(dialog_id: str, timeline_id: str) -> bytes:
            return (
                b"\x09"
                + b"\xff"  # afterMaskBlendData
                + b"\xff"  # beforeMaskBlendData
                + text(dialog_id)
                + (2).to_bytes(4, "little", signed=True)
                + b"\x00"  # enableSeamlessStartInSameFrame
                + b"\x01"  # LangKey header
                + (-1).to_bytes(4, "little", signed=True)
                + (-1).to_bytes(4, "little", signed=True)  # npcProxyIds
                + b"\x00"  # useBlackScreen
                + (1).to_bytes(4, "little", signed=True)
                + text(timeline_id)
            )

        payload = (
            b"\x05"
            + (2).to_bytes(4, "little", signed=True)
            + text("dlg_test_1")
            + brief("dlg_test_1", "dlgtl_test_1_sub_1")
            + text("dlg_test_2")
            + brief("dlg_test_2", "f_dlgtl_test_2_sub_1")
            + (2).to_bytes(4, "little", signed=True)
        )

        self.assertEqual(
            {
                "dlg_test_1": ["dlgtl_test_1_sub_1"],
                "dlg_test_2": ["f_dlgtl_test_2_sub_1"],
            },
            extract_used_dialog_timeline_ids(payload),
        )
        records = extract_dialog_brief_info_records(payload)
        self.assertEqual(set(records), {"dlg_test_1", "dlg_test_2"})
        index = build_index(payload)
        self.assertTrue(index["dlg_test_1"]["memoryPackRecordKey"])
        self.assertIn(
            "memorypack_record_key",
            index["dlg_test_1"]["registrationEvidence"],
        )


if __name__ == "__main__":
    unittest.main()
