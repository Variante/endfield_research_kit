from __future__ import annotations

import unittest

from scripts.story_builder.story_keys import line_stem, timeline_stem_to_dialog_key


class StoryKeyTests(unittest.TestCase):
    def test_line_stem_contract(self) -> None:
        self.assertEqual(line_stem("dlg_e1m1_1_1001"), "dlg_e1m1_1")
        self.assertEqual(line_stem("radio_e1m1_1_1001"), "radio_e1m1")
        self.assertEqual(line_stem("plain"), "")

    def test_timeline_stem_to_dialog_key_contract(self) -> None:
        self.assertEqual(timeline_stem_to_dialog_key("dlgtl_e1m1_1"), "dlg_e1m1_1")
        self.assertEqual(
            timeline_stem_to_dialog_key("f_dlgtl_e1m1_1_sub_2"),
            "dlg_e1m1_1",
        )
        self.assertEqual(timeline_stem_to_dialog_key(""), "")


if __name__ == "__main__":
    unittest.main()
