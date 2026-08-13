from __future__ import annotations

import re
import unittest

from scripts.story_builder.cutscene_subtitle_projection import (
    build_cutscene_texttable_line,
    build_fallback_track_line,
    line_has_explicit_gender_switch,
    normalize_subtitle_variant_text,
    subtitle_alternate_line_debug,
    subtitle_candidate_rank,
    subtitle_clip_debug,
    subtitle_slot_key,
    subtitle_track_language_score,
    subtitle_tracks_for_language,
)


CUTSCENE_TEXT_ROW_RE = re.compile(
    r"^(?P<group>cutscene_.+)_(?P<line>\d+)(?P<sub>d\d+)?(?P<gender>_[fm])?$",
    re.IGNORECASE,
)


def _source_ref(table: str, row_id: str, raw: dict, **extra: object) -> dict:
    return {"source": {"table": table, "rowId": row_id, "raw": raw, **extra}}


def _pick_fields(row: dict, *fields: str) -> dict:
    return {field: row[field] for field in fields if field in row}


def _text_trace(table: str, row_id: str, field: str, raw: object) -> dict:
    return {"table": table, "rowId": row_id, "field": field, "raw": raw}


class CutsceneSubtitleProjectionTests(unittest.TestCase):
    def test_language_scoring_and_override_selection(self) -> None:
        tracks = [
            {"parentName": "cutscene_AU_ENG_ENV_ENG"},
            {"parentName": "cutscene_AU_CHI_ENV_CHI"},
            {"parentName": "cutscene_untyped"},
        ]
        self.assertLess(
            subtitle_track_language_score(tracks[1], language_code="CN"),
            subtitle_track_language_score(tracks[0], language_code="CN"),
        )
        self.assertEqual(
            subtitle_tracks_for_language(
                "cutscene_test",
                tracks,
                language_code="CN",
                parent_overrides={},
            ),
            [tracks[1]],
        )
        self.assertEqual(
            subtitle_tracks_for_language(
                "cutscene_test",
                tracks,
                language_code="CN",
                parent_overrides={"CN": {"cutscene_test": {"cutscene_untyped"}}},
            ),
            [tracks[2]],
        )

    def test_builds_texttable_line_with_alias_subline_and_gender(self) -> None:
        row_key = "cutscene_test_alias_07d2_f"
        match = CUTSCENE_TEXT_ROW_RE.match(row_key)
        assert match is not None
        line = build_cutscene_texttable_line(
            row_key,
            {"id": 42, "text": "raw"},
            match,
            "cutscene_test",
            "cutscene_test_alias",
            translate=lambda value: f"localized:{value}",
            source_ref=_source_ref,
            pick_fields=_pick_fields,
            text_trace=_text_trace,
        )
        self.assertEqual(line["cid"], "07d2_f")
        self.assertEqual(line["text"], "localized:42")
        self.assertEqual(line["textGroup"], "cutscene_test_alias")
        self.assertEqual(line["sub"], "d2")
        self.assertEqual(line["gender"], "F")
        self.assertEqual(line["_debug"]["source"]["line"], 7)

    def test_builds_fallback_for_matching_and_unknown_track_ids(self) -> None:
        table = {"cutscene_test_03_m": {"id": 7}}
        matched = build_fallback_track_line(
            "cutscene_test",
            "cutscene_test_03_m",
            {"clipIndex": 9},
            text_table=table,
            cutscene_text_row_re=CUTSCENE_TEXT_ROW_RE,
            translate=lambda value: f"localized:{value}",
            source_ref=_source_ref,
            text_trace=_text_trace,
        )
        self.assertEqual(matched["cid"], "03_m")
        self.assertEqual(matched["text"], "localized:7")
        self.assertEqual(matched["_debug"]["source"]["gender"], "M")

        unknown = build_fallback_track_line(
            "cutscene_test",
            "unknown_row",
            {"clipIndex": 9},
            text_table=table,
            cutscene_text_row_re=CUTSCENE_TEXT_ROW_RE,
            translate=str,
            source_ref=_source_ref,
            text_trace=_text_trace,
        )
        self.assertEqual(unknown["cid"], "9")
        self.assertEqual(unknown["text"], "")
        self.assertIsNone(unknown["_debug"]["fields"]["text"]["raw"])

    def test_projects_slot_and_complete_clip_debug(self) -> None:
        ref = {
            "textId": "cutscene_test_01",
            "start": 1.23456789,
            "duration": 2.34567891,
            "clipIndex": 3,
            "assetPathId": 9,
            "displayName": "subtitle",
        }
        track = {
            "file": "track.json",
            "parentName": "parent",
            "parentFile": "parent.json",
            "gender": "F",
            "pathId": 10,
            "parentPathId": 11,
        }
        self.assertEqual(subtitle_slot_key(ref, 2), (1.234568, 2.345679, 2))
        debug = subtitle_clip_debug(track, ref)
        self.assertEqual(debug["assetGender"], "F")
        self.assertEqual(debug["trackPathId"], 10)
        self.assertEqual(debug["parentPathId"], 11)

    def test_gender_normalization_ranking_and_alternate_debug(self) -> None:
        line = {
            "id": "cutscene_test_01_f",
            "cid": "01_f",
            "text": "{F} Hello! {M}HELLO",
            "textGroup": "cutscene_alias",
        }
        candidate = {
            "rowKey": line["id"],
            "line": line,
            "gender": "F",
            "clipIndex": 4,
            "trackDebug": {"file": "track.json"},
        }
        self.assertTrue(line_has_explicit_gender_switch(line))
        self.assertEqual(normalize_subtitle_variant_text(line["text"]), "hellohello")
        self.assertEqual(
            subtitle_candidate_rank("cutscene_test", candidate),
            (0, 0, 1, 4, "cutscene_test_01_f"),
        )
        self.assertEqual(
            subtitle_alternate_line_debug(candidate),
            {
                "id": line["id"],
                "cid": "01_f",
                "text": line["text"],
                "track": {"file": "track.json"},
                "textGroup": "cutscene_alias",
                "assetGender": "F",
            },
        )


if __name__ == "__main__":
    unittest.main()
