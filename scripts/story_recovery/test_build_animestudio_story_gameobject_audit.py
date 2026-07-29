from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_animestudio_story_gameobject_audit as audit  # noqa: E402


def object_row(
    *,
    path_id: int,
    serialized_file: str = "CAB-test",
    scalars: list[list[object]] | None = None,
    pptrs: list[dict[str, object]] | None = None,
    script: str = "Test.Component",
) -> dict[str, object]:
    return {
        "recordType": "object",
        "schemaVersion": 1,
        "decodeStatus": "decoded",
        "schemaId": "schema",
        "type": "MonoBehaviour",
        "object": {
            "pathId": path_id,
            "serializedFile": serialized_file,
            "source": "VFS/hash/chunk.chk",
            "sourceOffset": 100,
        },
        "script": {
            "fullName": script,
            "assembly": "Test.dll",
        },
        "scalars": scalars or [],
        "pptrs": pptrs or [],
    }


class AnimeStudioStoryGameObjectAuditTests(unittest.TestCase):
    def test_targeted_dump_batches_bound_command_growth(self) -> None:
        logical_names = [f"Data/Bundles/{index}.ab" for index in range(130)]

        batches = audit.batched_logical_names(logical_names)

        self.assertEqual([len(batch) for batch in batches], [64, 64, 2])
        self.assertEqual(
            [name for batch in batches for name in batch],
            logical_names,
        )

    def test_collects_exact_resolved_gameobject_carrier(self) -> None:
        rows = [
            object_row(
                path_id=11,
                scalars=[["$._timelineName", "s", "cutscene_e1m1_test"]],
                pptrs=[{
                    "path": "$.m_GameObject",
                    "pathId": 22,
                    "status": "resolved",
                }],
            ),
        ]
        found, counts = audit.collect_story_game_objects(
            rows,
            {"cutscene_e1m1_test": {"e1m1"}},
            "StreamingAssets",
        )
        self.assertEqual(counts["objectsWithResolvedGameObject"], 1)
        self.assertEqual(found[0]["gameObjectPathIds"], [22])
        self.assertEqual(found[0]["expectedGapMissions"], ["e1m1"])

    def test_rejects_unresolved_gameobject_pointer(self) -> None:
        rows = [
            object_row(
                path_id=11,
                scalars=[["$._timelineName", "s", "cutscene_e1m1_test"]],
                pptrs=[{
                    "path": "$.m_GameObject",
                    "pathId": 22,
                    "status": "unresolved",
                }],
            ),
        ]
        found, counts = audit.collect_story_game_objects(
            rows,
            {"cutscene_e1m1_test": {"e1m1"}},
            "StreamingAssets",
        )
        self.assertEqual(found, [])
        self.assertEqual(counts["objectsWithExactTargetValue"], 1)

    def test_maps_source_offset_to_exact_logical_bundle(self) -> None:
        chunk = {
            "fileName": "chunk.chk",
            "files": [
                {
                    "blockType": "Bundle",
                    "name": "Data/Bundles/a.ab",
                    "offset": 100,
                    "length": 20,
                    "dataMd5": "ABC",
                },
                {
                    "blockType": "Bundle",
                    "name": "Data/Bundles/b.ab",
                    "offset": 120,
                    "length": 10,
                    "dataMd5": "DEF",
                },
            ],
        }
        result = audit.logical_bundle_for_offset(chunk, 119)
        self.assertEqual(result["name"], "Data/Bundles/a.ab")
        self.assertEqual(result["offset"], 100)

    def test_loads_only_chunk_object_with_files(self) -> None:
        payload = {
            "blocks": [{
                "chunks": [{
                    "fileName": "chunk.chk",
                    "contentMd5": "ABC",
                    "files": [{
                        "blockType": "Bundle",
                        "name": "Data/Bundles/a.ab",
                        "offset": 0,
                        "length": 10,
                    }],
                }],
            }],
            "files": [{
                "chunkFile": "chunk.chk",
                "fileName": "Data/Bundles/a.ab",
            }],
        }
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "index.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            chunk = audit.load_chunk_record(path, "chunk.chk")
        self.assertEqual(chunk["contentMd5"], "ABC")
        self.assertEqual(len(chunk["files"]), 1)

    def test_reads_gameobject_component_membership(self) -> None:
        payload = {
            "m_Name": "root",
            "m_Components": [
                {"m_PathID": 101},
                {"m_PathID": 202},
            ],
            "m_Transform": {
                "m_GameObject": {"m_PathID": 55},
                "m_Father": {"m_PathID": 0},
                "m_Children": [
                    {"m_PathID": 303},
                    {"m_PathID": 404},
                ],
            },
        }
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            (root / "root.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            result = audit.game_object_components(root)
        self.assertEqual(result[55]["componentPathIds"], [101, 202])
        self.assertEqual(result[55]["transformComponentPathId"], 101)
        self.assertEqual(result[55]["parentTransformPathId"], 0)
        self.assertEqual(result[55]["childTransformPathIds"], [303, 404])

    def test_resolves_exact_recursive_descendant_hierarchy(self) -> None:
        game_objects = {
            1: {
                "name": "root",
                "componentPathIds": [101, 11],
                "transformComponentPathId": 101,
                "parentTransformPathId": 0,
                "childTransformPathIds": [102],
            },
            2: {
                "name": "child",
                "componentPathIds": [102, 22],
                "transformComponentPathId": 102,
                "parentTransformPathId": 101,
                "childTransformPathIds": [103],
            },
            3: {
                "name": "grandchild",
                "componentPathIds": [103, 33],
                "transformComponentPathId": 103,
                "parentTransformPathId": 102,
                "childTransformPathIds": [],
            },
        }
        descendants, unresolved = audit.descendant_game_objects(
            game_objects, 1
        )
        self.assertEqual(unresolved, [])
        self.assertEqual(
            [(row["pathId"], row["depth"]) for row in descendants],
            [(2, 1), (3, 2)],
        )

    def test_rejects_unresolved_declared_child_transform(self) -> None:
        game_objects = {
            1: {
                "name": "root",
                "componentPathIds": [101, 11],
                "transformComponentPathId": 101,
                "parentTransformPathId": 0,
                "childTransformPathIds": [999],
            },
        }
        with self.assertRaises(audit.AuditError):
            audit.descendant_game_objects(game_objects, 1)

    def test_analyze_roots_emits_typed_owner_sibling_candidate(self) -> None:
        roots = [{
            "storyKeys": ["cutscene_e1m1_test"],
            "expectedGapMissions": ["e1m1"],
            "source": "StreamingAssets",
            "object": {
                "serializedFile": "CAB-test",
                "pathId": 11,
            },
            "type": {},
            "gameObjectPathIds": [22],
            "logicalBundle": {"name": "Data/Bundles/a.ab"},
        }]
        game_objects = {
            "StreamingAssets": {
                22: {
                    "name": "root",
                    "componentPathIds": [100, 11, 33],
                    "transformComponentPathId": 100,
                    "parentTransformPathId": 0,
                    "childTransformPathIds": [],
                },
            },
        }
        component_rows = {
            ("StreamingAssets", "CAB-test", 33): object_row(
                path_id=33,
                scalars=[["$.missionId", "s", "e1m1"]],
                script="Test.Owner",
            ),
        }
        analyzed, counts = audit.analyze_roots(
            roots, game_objects, component_rows
        )
        self.assertEqual(counts["gameObjectsWithCandidateSibling"], 1)
        candidate = analyzed[0]["candidateSiblingComponents"][0]
        self.assertEqual(candidate["type"]["scriptFullName"], "Test.Owner")
        self.assertEqual(candidate["ownerFields"][0]["value"], "e1m1")
        self.assertEqual(analyzed[0]["unindexedComponentPathIds"], [])

    def test_analyze_roots_emits_typed_owner_descendant_candidate(self) -> None:
        roots = [{
            "storyKeys": ["cutscene_e1m1_test"],
            "expectedGapMissions": ["e1m1"],
            "source": "StreamingAssets",
            "object": {
                "serializedFile": "CAB-test",
                "pathId": 11,
            },
            "type": {},
            "gameObjectPathIds": [22],
            "logicalBundle": {"name": "Data/Bundles/a.ab"},
        }]
        game_objects = {
            "StreamingAssets": {
                22: {
                    "name": "root",
                    "componentPathIds": [100, 11],
                    "transformComponentPathId": 100,
                    "parentTransformPathId": 0,
                    "childTransformPathIds": [200],
                },
                23: {
                    "name": "child",
                    "componentPathIds": [200, 33],
                    "transformComponentPathId": 200,
                    "parentTransformPathId": 100,
                    "childTransformPathIds": [],
                },
            },
        }
        component_rows = {
            ("StreamingAssets", "CAB-test", 33): object_row(
                path_id=33,
                scalars=[["$.missionId", "s", "e1m1"]],
                script="Test.DescendantOwner",
            ),
        }
        analyzed, counts = audit.analyze_roots(
            roots, game_objects, component_rows
        )
        self.assertEqual(counts["gameObjectsWithCandidateDescendant"], 1)
        descendant = analyzed[0]["descendantGameObjects"][0]
        self.assertEqual(descendant["pathId"], 23)
        self.assertEqual(descendant["depth"], 1)
        self.assertEqual(
            descendant["candidateComponents"][0]["type"]["scriptFullName"],
            "Test.DescendantOwner",
        )


if __name__ == "__main__":
    unittest.main()
