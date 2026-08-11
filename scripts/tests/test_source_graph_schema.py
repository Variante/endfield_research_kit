from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.endfield_source_graph import (
    SourceGraphBuilder,
    classify_story_audio_reference,
)


class SourceGraphSchemaTests(unittest.TestCase):
    def test_pathless_story_audio_classification_keeps_evidence_separate(self) -> None:
        self.assertEqual(
            classify_story_audio_reference(
                "au_radio_fixture_001",
                "dialog_line",
                {"radio_line"},
                False,
            ),
            {
                "family": "radio",
                "evidenceClass": "owner_table_without_path",
                "ownerKinds": ["radio_line"],
            },
        )
        self.assertEqual(
            classify_story_audio_reference(
                "au_sfx_fixture",
                "dialog_line",
                set(),
                True,
            )["evidenceClass"],
            "wwise_event_media_candidate",
        )
        self.assertEqual(
            classify_story_audio_reference("#N/A", "dialog_line", {"env_talk"}, False)[
                "evidenceClass"
            ],
            "placeholder",
        )

    def test_unique_indexes_cover_source_and_alias_lookups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = SourceGraphBuilder(db_path=Path(temp_dir) / "graph.sqlite")
            builder.open()
            try:
                edge_indexes = {
                    row[1] for row in builder.db.execute("PRAGMA index_list(edges)")
                }
                alias_indexes = {
                    row[1] for row in builder.db.execute("PRAGMA index_list(aliases)")
                }
                self.assertNotIn("idx_edges_src", edge_indexes)
                self.assertNotIn("idx_aliases_alias", alias_indexes)
                self.assertIn("sqlite_autoindex_edges_1", edge_indexes)
                self.assertIn("sqlite_autoindex_aliases_1", alias_indexes)

                source = builder.add_node("test", "source")
                destination = builder.add_node("test", "destination")
                builder.add_edge(source, destination, "test_edge")
                builder.add_alias("source_alias", source, kind="test")

                edge_plan = " ".join(
                    str(value)
                    for row in builder.db.execute(
                        "EXPLAIN QUERY PLAN SELECT dst FROM edges WHERE src = ?",
                        (source,),
                    )
                    for value in row
                )
                alias_plan = " ".join(
                    str(value)
                    for row in builder.db.execute(
                        "EXPLAIN QUERY PLAN SELECT node_id FROM aliases WHERE alias = ?",
                        ("source_alias",),
                    )
                    for value in row
                )
                self.assertIn("sqlite_autoindex_edges_1", edge_plan)
                self.assertIn("sqlite_autoindex_aliases_1", alias_plan)
                self.assertEqual(builder.alias_node_ids("source_alias"), [source])
            finally:
                builder.close()

    def test_audio_dialog_backfills_story_created_audio_node(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = SourceGraphBuilder(db_path=Path(temp_dir) / "graph.sqlite")
            builder.open()
            try:
                line_node = builder.add_node(
                    "line",
                    "dlg_fixture_001",
                    source="webui/story",
                    data={"audio": "au_fixture"},
                )
                audio_node = builder.add_node(
                    "audio",
                    "au_fixture",
                    source="dialog_line",
                )
                builder.add_edge(
                    line_node,
                    audio_node,
                    "uses_audio",
                    source="webui/story",
                )
                row_node = builder.add_node(
                    "table_row",
                    "AudioDialog:fixture",
                    source="AudioDialog",
                )
                builder.add_structured_row_edges(
                    "AudioDialog",
                    "fixture",
                    {
                        "path": "v1d0/Narrating/SubChar/fixture/au_fixture.wem",
                        "speakerChannel": "fixture_actor",
                        "wavDuration": 1.25,
                        "voType": 4,
                        "codec": "vorbis",
                    },
                    row_node,
                )

                path, source, raw_data = builder.db.execute(
                    "SELECT path, source, data FROM nodes WHERE id = ?",
                    (audio_node,),
                ).fetchone()
                self.assertEqual(path, "v1d0/Narrating/SubChar/fixture/au_fixture.wem")
                self.assertEqual(source, "AudioDialog")
                self.assertEqual(
                    json.loads(raw_data),
                    {
                        "id": "fixture",
                        "speaker": "fixture_actor",
                        "duration": 1.25,
                        "path": "v1d0/Narrating/SubChar/fixture/au_fixture.wem",
                        "voType": 4,
                        "codec": "vorbis",
                    },
                )
                linked_path = builder.db.execute(
                    """
                    SELECT audio.path
                    FROM edges AS edge
                    JOIN nodes AS audio ON audio.id = edge.dst
                    WHERE edge.src = ? AND edge.kind = 'uses_audio'
                    """,
                    (line_node,),
                ).fetchone()[0]
                self.assertEqual(
                    linked_path,
                    "v1d0/Narrating/SubChar/fixture/au_fixture.wem",
                )
            finally:
                builder.close()


if __name__ == "__main__":
    unittest.main()
