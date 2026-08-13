import unittest

from scripts.story_builder.source_links import (
    compact_story_source_link,
    story_source_link_index_summary,
    story_source_link_search_text,
)


class StorySourceLinkProjectionTests(unittest.TestCase):
    def test_compact_link_preserves_source_debug_fields(self):
        link = {
            "source": "mission",
            "file": "MissionRuntimeAsset/m01.json",
            "path": "$.nodes[0]",
            "raw": "dlg_test_1",
            "kind": "dialog",
            "matchKind": "exact",
            "mission": "m01",
            "context": {"owner": {"questId": "q01"}},
        }

        compact = compact_story_source_link(link)

        self.assertEqual(compact["mission"], "m01")
        self.assertEqual(compact["_debug"]["source"]["matchKind"], "exact")
        self.assertEqual(compact["context"]["owner"]["questId"], "q01")

    def test_search_text_includes_owner_values(self):
        text = story_source_link_search_text(
            [{"raw": "dlg_test_1", "context": {"owner": {"questId": "q01"}}}]
        )

        self.assertEqual(text, "dlg_test_1 q01")

    def test_summary_counts_sources_and_preserves_unique_file_order(self):
        summary = story_source_link_index_summary(
            [
                {"source": "levelScript", "file": "b.json"},
                {"source": "mission", "file": "a.json"},
                {"source": "levelScript", "file": "b.json"},
            ]
        )

        self.assertEqual(summary["n"], 3)
        self.assertEqual(summary["sources"], {"levelScript": 2, "mission": 1})
        self.assertEqual(summary["files"], ["b.json", "a.json"])


if __name__ == "__main__":
    unittest.main()
