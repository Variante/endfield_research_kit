import unittest

from scripts.story_builder.language_bundle import story_text_key_parts


class StoryReadingPopupKeyTests(unittest.TestCase):
    def test_accepts_mission_scoped_content(self):
        self.assertEqual(
            story_text_key_parts("text_c13m3_4"),
            ("c13m3", "4"),
        )

    def test_accepts_map_level_content(self):
        self.assertEqual(
            story_text_key_parts("text_map01_lv001_14007"),
            ("map01_lv001", "14007"),
        )
        self.assertEqual(
            story_text_key_parts("text_map01_lv001_sm1l1m4_1"),
            ("map01_lv001", "sm1l1m4_1"),
        )

    def test_accepts_map_research_content(self):
        self.assertEqual(
            story_text_key_parts("text_map02_research12_1"),
            ("map02_research12", "1"),
        )

    def test_keeps_unplaced_prts_documents_out_of_story(self):
        self.assertIsNone(story_text_key_parts("text_v0d8_1"))
        self.assertIsNone(story_text_key_parts("text_v1d4_4"))


if __name__ == "__main__":
    unittest.main()
