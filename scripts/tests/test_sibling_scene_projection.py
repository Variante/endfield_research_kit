from __future__ import annotations

import unittest

from scripts.story_builder.sibling_scene_projection import (
    sibling_scene_template_branch_for_group,
)


class SiblingSceneProjectionTests(unittest.TestCase):
    def _project(
        self,
        *,
        local_line_ids: list[str],
        local_text: dict[str, str],
        sibling_branches: dict[str, list[str]],
        sibling_text: dict[str, str],
        sibling_after: str = "s_after",
        after_id: str = "",
        local_icons: tuple[str, str] = ("left", "right"),
        sibling_icons: tuple[str, str] = ("left", "right"),
    ) -> dict:
        local_option_ids = ["local_a", "local_b"]
        sibling_option_ids = ["sibling_a", "sibling_b"]
        option_signatures = {
            "local_a": ("accept", local_icons[0]),
            "local_b": ("decline", local_icons[1]),
            "sibling_a": ("accept", sibling_icons[0]),
            "sibling_b": ("decline", sibling_icons[1]),
        }
        dialog_signatures = {**local_text, **sibling_text, sibling_after: "anchor"}

        return sibling_scene_template_branch_for_group(
            local_option_ids,
            after_id,
            7,
            conversation_key="local_scene",
            line_indices=list(enumerate(local_line_ids)),
            lines=[{"id": line_id, "text": local_text[line_id]} for line_id in local_line_ids],
            valid_line_ids=set(local_line_ids),
            option_group_keys_by_group_and_count={
                (7, 2): [("local_scene", 7), ("sibling_scene", 7)]
            },
            option_group_ids_by_key={
                ("local_scene", 7): local_option_ids,
                ("sibling_scene", 7): sibling_option_ids,
            },
            option_signatures_by_id=option_signatures,
            dialog_line_text_signature=lambda line_id: dialog_signatures.get(line_id, ""),
            load_dialog_tree=lambda scene: {
                "after": {option_id: sibling_after for option_id in sibling_option_ids},
                "branches": sibling_branches,
                "file": "sibling.json",
                "sourceKey": "sibling/source",
            }
            if scene == "sibling_scene"
            else {},
            option_text_signature=lambda text: text.casefold(),
            sequence_similarity_at_least=lambda left, right, _threshold: left == right,
            unique_preserve=lambda values: list(dict.fromkeys(values)),
        )

    def test_maps_all_sibling_branch_lines(self) -> None:
        result = self._project(
            local_line_ids=["local_after", "local_a_line", "local_b_line"],
            local_text={
                "local_after": "anchor",
                "local_a_line": "alpha",
                "local_b_line": "beta",
            },
            sibling_branches={
                "sibling_a": ["sibling_a_line"],
                "sibling_b": ["sibling_b_line"],
            },
            sibling_text={"sibling_a_line": "alpha", "sibling_b_line": "beta"},
        )

        self.assertEqual(result["after"], "local_after")
        self.assertEqual(
            result["branchLineIdsByOption"],
            {"local_a": ["local_a_line"], "local_b": ["local_b_line"]},
        )
        self.assertEqual(result["siblingScene"], "sibling_scene")
        self.assertEqual(
            result["sources"],
            ["sibling_scene", "sibling/source", "sibling.json"],
        )

    def test_infers_one_unmatched_branch_from_local_span(self) -> None:
        result = self._project(
            local_line_ids=[
                "local_after",
                "unmatched_1",
                "unmatched_2",
                "local_b_line",
            ],
            local_text={
                "local_after": "anchor",
                "unmatched_1": "one",
                "unmatched_2": "two",
                "local_b_line": "beta",
            },
            sibling_branches={
                "sibling_a": ["sibling_a_line"],
                "sibling_b": ["sibling_b_line"],
            },
            sibling_text={
                "sibling_a_line": "different",
                "sibling_b_line": "beta",
            },
        )

        self.assertEqual(
            result["branchLineIdsByOption"],
            {
                "local_b": ["local_b_line"],
                "local_a": ["unmatched_1", "unmatched_2"],
            },
        )

    def test_rejects_icon_mismatch_and_late_existing_after(self) -> None:
        common = {
            "local_line_ids": ["local_after", "local_a_line", "local_b_line"],
            "local_text": {
                "local_after": "anchor",
                "local_a_line": "alpha",
                "local_b_line": "beta",
            },
            "sibling_branches": {
                "sibling_a": ["sibling_a_line"],
                "sibling_b": ["sibling_b_line"],
            },
            "sibling_text": {"sibling_a_line": "alpha", "sibling_b_line": "beta"},
        }
        self.assertEqual(
            self._project(**common, sibling_icons=("other", "right")),
            {},
        )
        self.assertEqual(
            self._project(**common, after_id="local_a_line"),
            {},
        )


if __name__ == "__main__":
    unittest.main()
