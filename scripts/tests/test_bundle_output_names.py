import unittest

from scripts.story_builder.bundle_support import safe_mission_data_filename


class BundleOutputNameTests(unittest.TestCase):
    def test_allocates_safe_unique_names_case_insensitively(self):
        used = set()
        self.assertEqual(safe_mission_data_filename("m:01", used), "m_01.json")
        self.assertEqual(safe_mission_data_filename("M:01", used), "M_01_2.json")
        self.assertEqual(safe_mission_data_filename("...", used), "mission.json")


if __name__ == "__main__":
    unittest.main()
