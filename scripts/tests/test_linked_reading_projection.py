from __future__ import annotations

import unittest

from scripts.story_builder.bundle_primitives import brace_text, pick_fields, source_ref
from scripts.story_builder.linked_reading_projection import (
    append_linked_reading_content_lines,
    reading_content_refs,
    rich_content_lines_for_source,
    rich_content_row_for_source,
    rich_content_title_text_for_source,
)
from scripts.story_builder.reference_projection import append_reference_line


def _translate(value: object, *, preferred_source: str = "streaming") -> str:
    return f"{preferred_source}:{value}" if value else ""


def _text_trace(
    table: str,
    row_id: str,
    field: str,
    raw: object,
    *,
    preferred_source: str = "streaming",
) -> dict:
    return {
        "table": table,
        "rowId": row_id,
        "field": field,
        "raw": raw,
        "preferredSource": preferred_source,
    }


def _source_label(source: str) -> str:
    return f"source:{source}"


class LinkedReadingProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.streaming_rich = {
            "text_1": {
                "title": {"id": 10},
                "contentList": [
                    {"content": {"id": 11}},
                    {"content": {"id": 12}},
                ],
            },
        }
        self.persistent_rich = {
            **self.streaming_rich,
            "text_persistent": {
                "title": {"id": 20},
                "contentList": [{"content": {"id": 21}}],
            },
        }

    def table_payload(self, source: str, table_name: str) -> dict:
        if table_name != "RichContentTable.json":
            return {}
        return self.streaming_rich if source == "streaming" else self.persistent_rich

    def common_deps(self) -> dict:
        return {
            "collection_table_payload": self.table_payload,
            "fallback_rich_content": self.streaming_rich,
        }

    def test_resolves_source_row_and_persistent_fallback(self) -> None:
        self.assertIs(
            rich_content_row_for_source(
                "text_1",
                "streaming",
                **self.common_deps(),
            ),
            self.streaming_rich["text_1"],
        )
        self.assertEqual(
            rich_content_row_for_source(
                "missing",
                "persistent",
                collection_table_payload=lambda _source, _table: {},
                fallback_rich_content={"missing": {"title": {"id": 30}}},
            ),
            {"title": {"id": 30}},
        )
        self.assertEqual(
            rich_content_row_for_source(
                "missing",
                "streaming",
                collection_table_payload=lambda _source, _table: {},
                fallback_rich_content={"missing": {}},
            ),
            {},
        )

    def test_projects_rich_title_lines_and_debug_source(self) -> None:
        title = rich_content_title_text_for_source(
            "text_1",
            "streaming",
            **self.common_deps(),
            translate=_translate,
        )
        lines = rich_content_lines_for_source(
            "text_1",
            "streaming",
            **self.common_deps(),
            translate=_translate,
            source_ref=source_ref,
            pick_fields=pick_fields,
            text_trace=_text_trace,
            collection_source_label=_source_label,
        )
        self.assertEqual(title, "streaming:10")
        self.assertEqual([line["text"] for line in lines], ["streaming:11", "streaming:12"])
        self.assertEqual(lines[0]["_debug"]["tableSource"], "source:streaming")

    def test_prts_refs_sort_by_order_and_project_labels(self) -> None:
        refs = reading_content_refs(
            "PrtsReading.json",
            "term_1",
            {
                "list": {
                    "late": {"contentId": "text_2", "order": 2, "name": {"id": 2}},
                    "early": {"contentId": "text_1", "order": 1, "name": {"id": 1}},
                    "invalid": "not a row",
                },
            },
            table_source="streaming",
            translate=_translate,
            brace_text=brace_text,
            pick_fields=pick_fields,
        )
        self.assertEqual([ref["contentId"] for ref in refs], ["text_1", "text_2"])
        self.assertEqual(refs[0]["label"], "streaming:1")
        self.assertEqual(refs[0]["path"], "$.list.early.contentId")

    def test_popup_ref_uses_content_id_when_title_is_empty(self) -> None:
        refs = reading_content_refs(
            "ReadingPopUpTable.json",
            "popup_1",
            {"contentId": "radio_1", "title": {"id": 0}},
            table_source="persistent",
            translate=_translate,
            brace_text=brace_text,
            pick_fields=pick_fields,
        )
        self.assertEqual(refs[0]["label"], "radio_1")
        self.assertEqual(refs[0]["nodeId"], 1)

    def append(self, row: dict, *, radio_row_lookup: dict | None = None) -> tuple:
        lines: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        result = append_linked_reading_content_lines(
            "ReadingPopUpTable.json",
            "popup_1",
            row,
            table_source="streaming",
            lines=lines,
            seen_texts=seen,
            **self.common_deps(),
            radio_row_lookup=radio_row_lookup or {},
            translate=_translate,
            source_ref=source_ref,
            pick_fields=pick_fields,
            text_trace=_text_trace,
            collection_source_label=_source_label,
            brace_text=brace_text,
            append_reference_line=append_reference_line,
        )
        return result, lines

    def test_appends_rich_content_with_title_and_preview(self) -> None:
        result, lines = self.append({"contentId": "text_1", "title": {"id": 99}})
        refs, preview = result
        self.assertEqual(refs[0]["source"], "RichContentTable")
        self.assertEqual(refs[0]["lineCount"], 2)
        self.assertEqual(preview, "streaming:10")
        self.assertEqual(
            [line["text"] for line in lines],
            ["streaming:10", "streaming:11", "streaming:12"],
        )
        self.assertIn("linkedFrom", lines[1]["_debug"])

    def test_falls_back_to_radio_lines(self) -> None:
        result, lines = self.append(
            {"contentId": "radio_1", "title": {"id": 0}},
            radio_row_lookup={
                "radio_1": {
                    "lines": [{
                        "id": "radio_line",
                        "text": "Radio text",
                        "actor": "Actor",
                        "aid": "actor_id",
                        "_debug": {"source": "radio"},
                    }],
                },
            },
        )
        refs, preview = result
        self.assertEqual(refs[0]["source"], "RadioTable")
        self.assertEqual(preview, "Radio text")
        self.assertEqual(lines[0]["actor"], "Actor")
        self.assertEqual(lines[0]["aid"], "actor_id")


if __name__ == "__main__":
    unittest.main()
