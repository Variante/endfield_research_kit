from __future__ import annotations

import unittest

from scripts.story_builder.standalone_video_projection import (
    emit_standalone_video_outputs,
    video_scene_hint,
    video_text_candidate_rows,
)


class StandaloneVideoProjectionTests(unittest.TestCase):
    def test_scene_hint_prefers_manual_attachment_and_strips_prefix(self) -> None:
        refs = [
            {
                "baseStem": "f_cs_video_e1m1_3",
                "_resolvedKey": "cutscene_fallback",
                "_videoAttachmentAttachOverride": {
                    "targetKey": "cutscene_e1m1_7"
                },
            }
        ]
        self.assertEqual(video_scene_hint(refs), "e1m1_7")

    def test_video_text_candidates_sort_line_and_subline_ids(self) -> None:
        table = {
            "cs_video_e1m1_3_2": {"id": "second"},
            "cs_video_e1m1_3_1d2_f": {"id": "first-sub"},
            "cs_video_e1m1_3_1": {"id": "first"},
            "cs_video_other_1": {"id": "other"},
        }
        rows = video_text_candidate_rows(
            "cs_video_e1m1_3",
            text_table=table,
            translate=lambda value: f"text:{value}",
            source_ref=lambda table_name, row_id, fields, **extra: {
                "table": table_name,
                "rowId": row_id,
                "fields": fields,
                **extra,
            },
            pick_fields=lambda row, *fields: {
                field: row.get(field) for field in fields
            },
            text_trace=lambda *_args: {"trace": True},
        )

        self.assertEqual(
            [row["id"] for row in rows],
            [
                "cs_video_e1m1_3_1",
                "cs_video_e1m1_3_1d2_f",
                "cs_video_e1m1_3_2",
            ],
        )
        self.assertEqual(rows[1]["sub"], "d2")

    def test_emit_preserves_raw_definition_and_writes_payload(self) -> None:
        written: dict[str, dict] = {}
        raw_ref = {
            "name": "cs_video_e1m1_3.mp4",
            "baseStem": "cs_video_e1m1_3",
            "stem": "cs_video_e1m1_3",
            "rel": "videos/cs_video_e1m1_3.mp4",
            "source": "structured",
            "format": "mp4",
            "size": 42,
            "definition": {
                "numericIds": [7],
                "timelineEvidence": {
                    "trackCount": 1,
                    "clipCount": 2,
                    "subtitleClipCount": 0,
                    "audioEventKeys": ["event_1"],
                },
            },
        }
        entries = emit_standalone_video_outputs(
            {"video_cs_video_e1m1_3": [raw_ref]},
            narrative_video_name_sort_key=lambda ref: (ref["name"],),
            compact_narrative_video_ref=lambda ref: {
                "name": ref["name"],
                "definition": ref["definition"],
            },
            parse_mission=lambda mission: ("main", 1),
            unique_preserve=lambda values: list(dict.fromkeys(values)),
            mission_name_trace=lambda mission: {"mission": mission},
            write_conv_payload=lambda key, payload: written.setdefault(key, payload),
            narrative_video_index_summary=lambda refs: {"n": len(refs)},
            preview=lambda text: text[:80],
            merge_search_text=lambda *values: " ".join(
                str(value) for value in values if value
            ),
            mission_context_text=lambda mission: f"context:{mission}",
            text_table={},
            translate=lambda value: str(value or ""),
            source_ref=lambda *_args, **_kwargs: {},
            pick_fields=lambda *_args: {},
            text_trace=lambda *_args: {},
        )

        payload = written["video_cs_video_e1m1_3"]
        self.assertIn("fmv_id=7", payload["summary"][4]["text"])
        self.assertIn("1 track(s), 2 clip(s)", payload["summary"][5]["text"])
        self.assertIs(
            payload["narrativeVideos"][0]["definition"],
            raw_ref["definition"],
        )
        self.assertEqual(entries[0]["vid"], {"n": 1})
        self.assertEqual(entries[0]["videoSources"], {"structured": 1})


if __name__ == "__main__":
    unittest.main()
