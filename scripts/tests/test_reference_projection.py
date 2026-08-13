import unittest

from scripts.story_builder.reference_projection import (
    append_reference_line,
    collection_bucket,
    collection_bucket_from_key,
    collection_bucket_token,
    collection_display_name,
    collection_hint_from_path,
    collection_map_ref_from_identifiers,
    collection_row_title,
    collection_scene_value,
    collection_story_ref_from_bucket,
    collection_story_ref_from_identifiers,
    collection_summary_rows,
    collection_tags,
    normalized_reference_tags,
    prts_archive_category_from_collection_ids,
    prts_archive_category_from_identifier,
    prts_archive_category_from_row,
    prts_attachment_aliases,
    reference_row_texts,
    responsive_preview_values,
    responsive_sort_values,
)
from scripts.story_builder.bundle_support import parse_mission
from scripts.story_builder.context import MISSION_STORY_TYPES


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

    def test_collection_story_and_map_references_are_fail_closed(self):
        self.assertEqual(
            collection_story_ref_from_identifiers(
                "prefix/e2m6_11",
                parse_mission_id=parse_mission,
                mission_story_types=MISSION_STORY_TYPES,
            ),
            ("e2m6", 11, "e"),
        )
        self.assertEqual(
            collection_story_ref_from_identifiers(
                "topic_chat_1",
                parse_mission_id=parse_mission,
                mission_story_types=MISSION_STORY_TYPES,
            ),
            ("topic_chat_1", 0, "topic"),
        )
        self.assertEqual(
            collection_map_ref_from_identifiers("reading_map01_lv05_3"),
            ("map01_lv05", 3, "map"),
        )
        self.assertEqual(
            collection_story_ref_from_bucket(
                "group_e2m6_notes",
                parse_mission_id=parse_mission,
                mission_story_types=MISSION_STORY_TYPES,
            ),
            ("e2m6", 0, "e"),
        )
        self.assertIsNone(collection_story_ref_from_bucket(
            "e2m6_and_a1m1",
            parse_mission_id=parse_mission,
            mission_story_types=MISSION_STORY_TYPES,
        ))

    def test_prts_category_and_collection_tag_projection(self):
        self.assertEqual(prts_archive_category_from_identifier("nar_multi_media_01"), "media")
        self.assertEqual(
            prts_archive_category_from_collection_ids(["paper_1", "digital_1", "paper_2"]),
            "paper",
        )
        row = {
            "categoryDataList": [
                {"collectionIdList": ["document_1", "document_2"]},
            ],
        }
        self.assertEqual(prts_archive_category_from_row("PrtsInvestigate.json", "unknown", row), "document")
        self.assertEqual(
            collection_tags(
                "SystemJumpTable.json",
                "document_1",
                "document_group",
                row,
                table_source="persistent",
                variant=True,
            ),
            [
                "wiki",
                "collection",
                "table_systemjumptable",
                "source_persistent",
                "systemJump",
                "variant",
                "group_document_group",
                "category_document",
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
