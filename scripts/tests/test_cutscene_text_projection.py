from __future__ import annotations

import re
import unittest

from scripts.story_builder.bundle_primitives import pick_fields, source_ref
from scripts.story_builder.cutscene_semantics import merge_duplicate_cutscene_rows
from scripts.story_builder.cutscene_subtitle_projection import (
    build_cutscene_texttable_line,
    build_fallback_track_line,
    line_has_explicit_gender_switch,
    normalize_subtitle_variant_text,
    subtitle_alternate_line_debug,
    subtitle_candidate_rank,
    subtitle_clip_debug,
    subtitle_slot_key,
    subtitle_start_key,
    subtitle_tracks_for_language,
)
from scripts.story_builder.cutscene_text_projection import (
    CutsceneTextCallbacks,
    CutsceneTextInputs,
    project_cutscene_text_lines,
)


ROW_RE = re.compile(
    r"^(?P<group>cutscene_.+)_(?P<line>\d+)(?P<sub>d\d+)?(?P<gender>_[fm])?$",
    re.IGNORECASE,
)


def _translate(value: object) -> str:
    return str(value or "")


def _text_trace(table: str, row_id: str, field: str, raw: object) -> dict:
    return {"table": table, "rowId": row_id, "field": field, "raw": raw}


def _resolve(group: str, asset_keys: set[str], _raw_groups: set[str]) -> str:
    return group if group in asset_keys else group.rstrip("0")


class CutsceneTextProjectionTests(unittest.TestCase):
    def project(
        self,
        text_table: dict,
        asset_keys: set[str],
        tracks: dict[str, list[dict]],
    ) -> tuple[dict, list[object]]:
        usage: list[object] = []
        result = project_cutscene_text_lines(
            asset_keys,
            tracks,
            inputs=CutsceneTextInputs(text_table, "CN", {}, ROW_RE),
            callbacks=CutsceneTextCallbacks(
                split_parent_key=lambda key: key.rsplit("_", 1)[0] if key.endswith("_1") else "",
                split_child_sort_key=str,
                resolve_text_group=_resolve,
                translate=_translate,
                remember_texttable_row_usage=usage.append,
                source_ref=source_ref,
                pick_fields=pick_fields,
                text_trace=_text_trace,
                build_texttable_line=build_cutscene_texttable_line,
                select_display_text_group=lambda groups, _tracks: next(iter(groups), ""),
                select_tracks_for_language=subtitle_tracks_for_language,
                subtitle_start_key=subtitle_start_key,
                subtitle_slot_key=subtitle_slot_key,
                subtitle_clip_debug=subtitle_clip_debug,
                build_fallback_track_line=build_fallback_track_line,
                subtitle_candidate_rank=subtitle_candidate_rank,
                line_has_explicit_gender_switch=line_has_explicit_gender_switch,
                subtitle_alternate_line_debug=subtitle_alternate_line_debug,
                normalize_subtitle_variant_text=normalize_subtitle_variant_text,
                merge_duplicate_rows=merge_duplicate_cutscene_rows,
                pair_normalize=lambda text: "".join(text.split()),
            ),
        )
        return result, usage

    def test_projects_texttable_rows_without_subtitle_tracks(self) -> None:
        result, usage = self.project(
            {
                "cutscene_test_01": {"id": "First"},
                "cutscene_test_02": {"id": "Second"},
                "dialog_not_cutscene": {"id": "Ignored"},
            },
            {"cutscene_test"},
            {},
        )
        self.assertEqual(
            [line["text"] for line in result["cutscene_test"]],
            ["First", "Second"],
        )
        self.assertEqual(usage, ["cutscene_test_01", "cutscene_test_02"])

    def test_subtitle_tracks_order_lines_by_timing(self) -> None:
        result, usage = self.project(
            {
                "cutscene_test_01": {"id": "First"},
                "cutscene_test_02": {"id": "Second"},
            },
            {"cutscene_test"},
            {
                "cutscene_test": [{
                    "parentName": "track_AU_CHI_ENV_CHI",
                    "file": "track.json",
                    "lines": [
                        {"textId": "cutscene_test_02", "start": 2.0, "duration": 1.0, "clipIndex": 2},
                        {"textId": "cutscene_test_01", "start": 1.0, "duration": 1.0, "clipIndex": 1},
                    ],
                }],
            },
        )
        self.assertEqual(
            [line["id"] for line in result["cutscene_test"]],
            ["cutscene_test_01", "cutscene_test_02"],
        )
        self.assertIn("subtitleTrack", result["cutscene_test"][0]["_debug"])
        self.assertEqual(len(usage), 2)

    def test_gender_tracks_create_explicit_switch(self) -> None:
        tracks = {
            "cutscene_test": [
                {
                    "parentName": "f_track_AU_CHI_ENV_CHI",
                    "file": "f.json",
                    "gender": "F",
                    "lines": [{"textId": "cutscene_test_01_f", "start": 1.0, "duration": 1.0, "clipIndex": 1}],
                },
                {
                    "parentName": "m_track_AU_CHI_ENV_CHI",
                    "file": "m.json",
                    "gender": "M",
                    "lines": [{"textId": "cutscene_test_01_m", "start": 1.0, "duration": 1.0, "clipIndex": 1}],
                },
            ],
        }
        result, _usage = self.project(
            {
                "cutscene_test_01_f": {"id": "Female"},
                "cutscene_test_01_m": {"id": "Male"},
            },
            {"cutscene_test"},
            tracks,
        )
        line = result["cutscene_test"][0]
        self.assertEqual(line["text"], "{F}Female{M}Male")
        self.assertIn("subtitleGenderSwitch", line["_debug"])

    def test_text_only_parent_merges_into_matching_split_child(self) -> None:
        result, usage = self.project(
            {
                "cutscene_test_01": {"id": "Same"},
                "cutscene_test_1_01": {"id": "Same"},
            },
            {"cutscene_test_1"},
            {},
        )
        self.assertNotIn("cutscene_test", result)
        child = result["cutscene_test_1"][0]
        self.assertEqual(child["mergedDuplicateRows"][0]["id"], "cutscene_test_01")
        self.assertIn("cutscene_test_01", usage)


if __name__ == "__main__":
    unittest.main()
