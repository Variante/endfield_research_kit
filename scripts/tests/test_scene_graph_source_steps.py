from __future__ import annotations

import unittest

from scripts.story_builder.scene_graph import (
    _compact_scene_graph_sequence_steps,
)


class SceneGraphSourceStepTests(unittest.TestCase):
    def test_story_compaction_keeps_endpoint_steps_aligned(self) -> None:
        sequence = [
            "radio_e9m2_27",
            "#1234abcd",
            "cutscene_test_map02_lv002_FZDS_1",
        ]
        steps = [
            {"source": {"recordClass": "play_radio"}},
            {"source": {"recordClass": "split"}},
            {"source": {"recordClass": "preload_cutscene"}},
        ]

        compact, compact_steps = _compact_scene_graph_sequence_steps(
            sequence,
            steps,
            {"radio_e9m2_27"},
        )

        self.assertEqual(
            compact,
            [
                "radio_e9m2_27",
                "cutscene_test_map02_lv002_FZDS_1",
            ],
        )
        self.assertEqual(
            [
                step["source"]["recordClass"]
                for step in compact_steps
            ],
            ["play_radio", "preload_cutscene"],
        )


if __name__ == "__main__":
    unittest.main()
