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


if __name__ == "__main__":
    unittest.main()
