import unittest

from scripts.story_builder.dialog_tree import _dialog_tree_node_reaches
from scripts.story_builder.language_bundle import (
    dialog_tree_option_nodes_form_sequence,
    dialog_tree_option_prompt_sequence,
)


class DialogTreeOptionPromptSequenceTests(unittest.TestCase):
    def test_directed_reachability_distinguishes_forward_prompt_from_cycle(self):
        successors = {"10": ["11"], "11": ["12"], "12": ["13"], "13": []}
        self.assertTrue(_dialog_tree_node_reaches(successors, "10", "12"))
        self.assertFalse(_dialog_tree_node_reaches(successors, "12", "10"))

        cyclic = {**successors, "13": ["10"]}
        self.assertTrue(_dialog_tree_node_reaches(cyclic, "12", "10"))

    def test_separate_nodes_follow_prime_reachability_not_table_suffix_order(self):
        option_ids = ["option_scene_5_001", "option_scene_5_002"]
        layouts = {
            "option_scene_5_001": [{
                "nodeId": "12",
                "reachableFromPrime": True,
            "distanceFromPrime": 12,
            "sourceKey": "scene",
            "file": "tree.json",
            "reachableNodeIds": [],
            }],
            "option_scene_5_002": [{
                "nodeId": "10",
                "reachableFromPrime": True,
            "distanceFromPrime": 10,
            "sourceKey": "scene",
            "file": "tree.json",
            "reachableNodeIds": ["11", "12"],
            }],
        }

        self.assertEqual(
            dialog_tree_option_prompt_sequence(option_ids, layouts),
            ["option_scene_5_002", "option_scene_5_001"],
        )
        self.assertTrue(dialog_tree_option_nodes_form_sequence(
            ["option_scene_5_002", "option_scene_5_001"], layouts
        ))

    def test_distinct_branch_nodes_are_not_called_a_sequence(self):
        layouts = {
            "option_scene_5_001": [{
                "nodeId": "12", "sourceKey": "scene", "file": "tree.json",
                "reachableNodeIds": [],
            }],
            "option_scene_5_002": [{
                "nodeId": "10", "sourceKey": "scene", "file": "tree.json",
                "reachableNodeIds": [],
            }],
        }
        self.assertFalse(dialog_tree_option_nodes_form_sequence(
            ["option_scene_5_002", "option_scene_5_001"], layouts
        ))

    def test_unreachable_nodes_keep_stable_table_order(self):
        option_ids = ["option_scene_5_001", "option_scene_5_002"]
        layouts = {
            option_id: [{
                "nodeId": str(index),
                "reachableFromPrime": False,
                "distanceFromPrime": None,
            }]
            for index, option_id in enumerate(option_ids)
        }

        self.assertEqual(
            dialog_tree_option_prompt_sequence(option_ids, layouts),
            option_ids,
        )


if __name__ == "__main__":
    unittest.main()
