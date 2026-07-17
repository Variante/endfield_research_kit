import unittest

from scripts.story_builder.dialog_registry import build_index


class DialogRegistryTests(unittest.TestCase):
    def test_option_only_identifier_does_not_register_dialog_scene(self):
        payload = b"option_dlg_test_3_001"

        self.assertEqual(build_index(payload), {})

    def test_root_and_per_line_tokens_still_register(self):
        payload = b"dlg_test dlg_test_1_001 option_dlg_test_3_001"

        index = build_index(payload)
        self.assertEqual(set(index), {"dlg_test"})
        self.assertTrue(index["dlg_test"]["hasRootKey"])
        self.assertEqual(index["dlg_test"]["linesByTrunk"], {"1": ["dlg_test_1_001"]})
        self.assertEqual(
            index["dlg_test"]["optionsByGroup"],
            {"3": ["option_dlg_test_3_001"]},
        )


if __name__ == "__main__":
    unittest.main()
