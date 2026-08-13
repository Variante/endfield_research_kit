import unittest

from scripts.story_builder.reference_projection import (
    append_reference_line,
    collection_bucket,
    collection_bucket_from_key,
    collection_bucket_token,
    collection_display_name,
    collection_hint_from_path,
    collection_row_title,
    collection_scene_value,
    collection_summary_rows,
    normalized_reference_tags,
    prts_attachment_aliases,
    reference_row_texts,
    responsive_preview_values,
    responsive_sort_values,
)


class ReferenceProjectionTests(unittest.TestCase):
    def test_append_reference_line_deduplicates_visible_identity(self):
        lines = []
        seen = set()
        append_reference_line(lines, seen, "1", " Text ", hint="Hint", actor="npc")
        append_reference_line(lines, seen, "2", "Text", hint="Hint", actor="npc")
        self.assertEqual(lines, [{"id": "1", "text": "Text", "hint": "Hint", "actor": "npc"}])

    def test_collection_helpers_normalize_names_and_numeric_order(self):
        self.assertEqual(collection_display_name("worldTextEntry"), "World Text Entry")
        self.assertEqual(collection_bucket_from_key("wiki_region_entry"), "wiki_region")
        self.assertEqual(collection_scene_value({"priority": 7}, 2), 7)

    def test_collection_routing_helpers_preserve_reference_groups(self):
        self.assertEqual(
            collection_hint_from_path("$.stageList[2].title"),
            "Stage List 3 / Title",
        )
        self.assertEqual(
            collection_bucket("CommonDeathTips.json", "ignored", None),
            "common_death_tips",
        )
        self.assertEqual(
            collection_bucket("Example.json", "fallback_key", {"roomType": 3}),
            "roomType_3",
        )
        self.assertEqual(
            collection_bucket("TextTable.json", "wiki_region_entry", {"groupId": "ignored"}),
            "wiki_region",
        )
        self.assertEqual(collection_bucket_token("wiki_region"), "wiki_region_1b71")

    def test_collection_row_projection_preserves_titles_and_summary(self):
        self.assertEqual(
            collection_row_title(
                "Example.json",
                "row_1",
                [{"field": "title", "text": "Prefix {Visible title} suffix"}],
            ),
            "Visible title",
        )
        self.assertEqual(
            collection_row_title("TextTable.json", "text_row", [{"field": "desc", "text": "Body"}]),
            "text_row",
        )
        self.assertEqual(
            collection_summary_rows(
                "ExampleTable.json",
                "row_1",
                {"groupId": "group_1", "categoryId": ["a", "b", "c", "d", "e"]},
                "bucket_1",
                table_source="persistent",
                variant=True,
            ),
            [
                {"text": "Table: Example Table"},
                {"text": "Row: row_1"},
                {"text": "Source: Persistent/Table"},
                {"text": "Variant: differs from StreamingAssets row"},
                {"text": "Group: Bucket 1"},
                {"text": "Group Id: group_1"},
            ],
        )

    def test_reference_tags_and_prts_aliases_keep_contract(self):
        self.assertEqual(
            normalized_reference_tags(["collection", "wiki"], "wiki_collection_test"),
            ["other", "wiki"],
        )
        self.assertEqual(prts_attachment_aliases("prts_test_sns"), {"prts_test_sns", "sns_test"})

    def test_row_text_and_responsive_values(self):
        self.assertEqual(
            reference_row_texts([{"field": "name", "text": "Hello", "raw": {"id": 3}}]),
            [{"field": "name", "path": "$", "text": "Hello", "i18nId": "3"}],
        )
        self.assertEqual(responsive_sort_values({"10", "2", "key"}), ["2", "10", "key"])
        self.assertEqual(responsive_preview_values(["a", "b", "c"], limit=2), "a, b +1")


if __name__ == "__main__":
    unittest.main()
