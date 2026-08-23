from __future__ import annotations

import unittest

from scripts.mission_pipeline.story_binding_coverage_projection import (
    classify_lua_accepted_playback_counts,
)


class StoryBindingCoverageLuaCountsTests(unittest.TestCase):
    def test_partitions_exact_case_and_unique_casefold_associations(self) -> None:
        counts = classify_lua_accepted_playback_counts({
            "acceptedExactPlaybackCalls": [
                {"storyKey": "exact"},
                {
                    "storyKey": "casefold",
                    "recoveryAssociationStatus":
                        "accepted_unique_ascii_case_insensitive",
                },
                {"storyKey": "table_exact"},
            ],
        })
        self.assertEqual(3, counts["acceptedLuaPlaybackCalls"])
        self.assertEqual(2, counts["acceptedLuaExactCasePlaybackCalls"])
        self.assertEqual(
            1, counts["acceptedLuaUniqueCaseInsensitivePlaybackCalls"]
        )


if __name__ == "__main__":
    unittest.main()
