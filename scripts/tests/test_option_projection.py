from __future__ import annotations

import re
import unittest

from scripts.story_builder.option_projection import (
    apply_source_hub_option_groups,
    clone_dialog_option_for_hub,
    source_hub_option_groups,
)


def _option_group_parts(option_id: str) -> tuple[str, int, int] | None:
    match = re.search(r"_(\d+)_(\d+)$", option_id)
    return ("dlg_test", int(match.group(1)), int(match.group(2))) if match else None


def _unique_preserve(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _project_scene_link_option(option: dict) -> dict:
    return {"optionId": option.get("optionId") or ""}


class OptionProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conv_key = "dlg_e1_1"
        self.option_ids = (
            "option_dlg_e1_1_2_1",
            "option_dlg_e1_1_2_2",
        )
        self.option_payloads = {
            option_id: {"id": option_id, "i": 99, "text": f"Choice {idx}", "_debug": {}}
            for idx, option_id in enumerate(self.option_ids, start=1)
        }
        self.option_signatures = {
            option_id: (f"Choice {idx}", "")
            for idx, option_id in enumerate(self.option_ids, start=1)
        }
        common_debug = {
            "sourceOptionNodeId": "node_options",
            "groupSceneKeys": [self.conv_key, "dlg_e1_2"],
            "targetSceneKeys": [self.conv_key, "dlg_e1_2"],
        }
        self.source = {
            "file": "dialog_tree.json",
            "sourceSceneKeys": [self.conv_key, "dlg_e1_2"],
            "lineGraph": {
                "nodes": [
                    {"id": "node_options", "optionIds": list(self.option_ids)},
                ],
            },
            "sceneLinks": [
                {
                    "sourceKey": self.conv_key,
                    "sceneKey": self.conv_key,
                    "after": "dialog_e1_1_5",
                    "options": [{"optionId": self.option_ids[0]}],
                    "_debug": dict(common_debug),
                },
                {
                    "sourceKey": self.conv_key,
                    "sceneKey": "dlg_e1_2",
                    "after": "dialog_e1_2_1",
                    "options": [{"optionId": self.option_ids[1]}],
                    "_debug": dict(common_debug),
                },
            ],
        }

    def projection_kwargs(self) -> dict:
        return {
            "option_payload_by_id": self.option_payloads,
            "option_signature_by_id": self.option_signatures,
            "option_group_parts": _option_group_parts,
            "unique_preserve": _unique_preserve,
            "scene_link_option_projector": _project_scene_link_option,
        }

    def test_clone_uses_deep_copy_and_fail_closed_empty_id(self):
        clone = clone_dialog_option_for_hub(
            self.option_ids[0],
            1,
            "dlg_e1_2",
            option_payload_by_id=self.option_payloads,
            option_signature_by_id=self.option_signatures,
        )
        self.assertEqual(clone["i"], 1)
        self.assertEqual(clone["targetSceneKey"], "dlg_e1_2")
        self.assertNotIn("targetSceneKey", self.option_payloads[self.option_ids[0]])
        self.assertIsNone(
            clone_dialog_option_for_hub(
                "",
                1,
                option_payload_by_id=self.option_payloads,
                option_signature_by_id=self.option_signatures,
            )
        )

    def test_source_hub_projection_requires_local_anchor_and_multiple_options(self):
        groups, links = source_hub_option_groups(
            self.conv_key,
            {"dialog_e1_1_5"},
            self.source,
            **self.projection_kwargs(),
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["g"], 2)
        self.assertEqual(groups[0]["after"], "dialog_e1_1_5")
        self.assertEqual([option["i"] for option in groups[0]["options"]], [1, 2])
        self.assertEqual(groups[0]["hubMenu"]["sceneKeys"], [self.conv_key, "dlg_e1_2"])
        self.assertEqual([option["optionId"] for option in links[0]["options"]], list(self.option_ids))
        self.assertEqual(
            source_hub_option_groups(
                self.conv_key,
                {"different_line"},
                self.source,
                **self.projection_kwargs(),
            ),
            ([], []),
        )

    def test_apply_replaces_matching_group_and_narrower_scene_link(self):
        payload = {
            "key": self.conv_key,
            "lines": [{"id": "dialog_e1_1_5"}],
            "optionGroups": [{"g": 2, "after": "dialog_e1_1_5", "options": []}],
        }
        links = [
            {
                "after": "dialog_e1_1_5",
                "options": [{"optionId": self.option_ids[0]}],
                "_debug": {"link": {"sourceOptionNodeId": "node_options"}},
            },
            {"after": "unrelated", "options": []},
        ]
        result = apply_source_hub_option_groups(
            payload,
            links,
            self.source,
            **self.projection_kwargs(),
        )
        self.assertIs(result, links)
        self.assertEqual(len(payload["optionGroups"]), 1)
        self.assertIn("hubMenu", payload["optionGroups"][0])
        self.assertEqual([link.get("after") for link in result], ["unrelated", "dialog_e1_1_5"])


if __name__ == "__main__":
    unittest.main()
