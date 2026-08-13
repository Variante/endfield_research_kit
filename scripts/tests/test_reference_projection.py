import unittest

from scripts.story_builder.reference_projection import (
    append_reference_line,
    collection_bucket_from_key,
    collection_display_name,
    collection_scene_value,
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
