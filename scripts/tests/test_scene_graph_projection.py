import unittest

from scripts.story_builder.scene_graph import (
    graph_fragments_text,
    scene_link_option_payload,
    scene_links_text,
)


class SceneGraphProjectionTests(unittest.TestCase):
    def test_fragment_text_includes_lines_options_and_terminals(self):
        text = graph_fragments_text(
            [{
                "sourceKey": "dlg_a",
                "lineIds": ["line_1"],
                "terminalCounts": {"finish": 1, "none": 0},
                "optionGroups": [{
                    "after": "line_1",
                    "optionIds": ["opt_1"],
                    "branches": {"opt_1": ["line_2"]},
                    "merge": {"opt_1": "line_3"},
                }],
            }]
        )
        self.assertEqual(text, "dlg_a line_1 finish:1 line_1 opt_1 line_2 line_3")

    def test_scene_link_text_includes_submenu_and_loop_routes(self):
        text = scene_links_text(
            [{"sourceKey": "dlg_a", "options": [{
                "optionId": "opt_1",
                "loop": {"kind": "back", "sceneKeys": ["dlg_a"]},
                "submenuTargets": [{"sceneKey": "dlg_b", "text": "More"}],
            }]}]
        )
        self.assertEqual(text, "dlg_a opt_1 back dlg_a dlg_b More")

    def test_option_payload_drops_internal_fields(self):
        payload = scene_link_option_payload(
            {"optionId": "opt_1", "firstLineId": "line_1", "internal": 7}
        )
        self.assertEqual(payload, {"optionId": "opt_1", "firstLineId": "line_1"})


if __name__ == "__main__":
    unittest.main()
