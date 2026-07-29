from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_animestudio_story_reverse_pptr_audit as audit  # noqa: E402


def object_row(
    *,
    path_id: int,
    serialized_file: str,
    scalars: list[list[object]] | None = None,
    pptrs: list[dict[str, object]] | None = None,
    object_type: str = "MonoBehaviour",
    script: str = "Test.Component",
) -> dict[str, object]:
    return {
        "recordType": "object",
        "type": object_type,
        "object": {
            "pathId": path_id,
            "serializedFile": serialized_file,
            "source": "VFS/hash/chunk.chk",
            "sourceOffset": 1,
        },
        "script": (
            {"fullName": script, "assembly": "Test.dll"}
            if object_type == "MonoBehaviour"
            else None
        ),
        "scalars": scalars or [],
        "pptrs": pptrs or [],
    }


class AnimeStudioStoryReversePPtrAuditTests(unittest.TestCase):
    def test_collects_exact_target_and_cross_file_director_relation(
        self,
    ) -> None:
        target = object_row(
            path_id=10,
            serialized_file="CAB-timeline",
            scalars=[["$.m_Name", "s", "cutscene_e1m1_test"]],
            script="UnityEngine.Timeline.TimelineAsset",
        )
        targets, parsed = audit.collect_targets(
            [target],
            {"cutscene_e1m1_test": {"e1m1"}},
            "StreamingAssets",
        )
        self.assertEqual(parsed, 1)
        director = object_row(
            path_id=20,
            serialized_file="CAB-host",
            object_type="PlayableDirector",
            pptrs=[
                {
                    "path": "$.m_GameObject",
                    "pathId": 30,
                    "status": "resolved",
                    "target": {
                        "serializedFile": "CAB-host",
                        "pathId": 30,
                    },
                },
                {
                    "path": "$.m_PlayableAsset",
                    "pathId": 10,
                    "status":
                        "resolved_postmerge_unique_external_filename_pathid",
                    "target": {
                        "serializedFile": "CAB-timeline",
                        "pathId": 10,
                    },
                },
            ],
        )
        relations, parsed = audit.collect_reverse_relations(
            [director], targets, "StreamingAssets"
        )
        self.assertEqual(parsed, 1)
        self.assertEqual(len(relations), 1)
        self.assertEqual(
            relations[0]["scope"], "cross_serialized_file_reference"
        )
        self.assertEqual(relations[0]["referrerGameObjectPathIds"], [30])
        roots = audit.cross_file_director_roots(relations)
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["storyKeys"], ["cutscene_e1m1_test"])

    def test_same_file_relation_is_not_external_director_root(self) -> None:
        target = object_row(
            path_id=10,
            serialized_file="CAB-one",
            scalars=[["$.m_Name", "s", "cutscene_e1m1_test"]],
        )
        targets, _ = audit.collect_targets(
            [target],
            {"cutscene_e1m1_test": {"e1m1"}},
            "StreamingAssets",
        )
        track = object_row(
            path_id=20,
            serialized_file="CAB-one",
            pptrs=[{
                "path": "$.m_Parent",
                "pathId": 10,
                "status": "resolved",
                "target": {
                    "serializedFile": "CAB-one",
                    "pathId": 10,
                },
            }],
            script="UnityEngine.Timeline.ControlTrack",
        )
        relations, _ = audit.collect_reverse_relations(
            [track], targets, "StreamingAssets"
        )
        self.assertEqual(
            relations[0]["scope"], "same_serialized_file_composition"
        )
        self.assertEqual(audit.cross_file_director_roots(relations), [])

    def test_source_is_part_of_exact_object_identity(self) -> None:
        target = object_row(
            path_id=10,
            serialized_file="CAB-shared-name",
            scalars=[["$.m_Name", "s", "cutscene_e1m1_test"]],
        )
        targets, _ = audit.collect_targets(
            [target],
            {"cutscene_e1m1_test": {"e1m1"}},
            "StreamingAssets",
        )
        referrer = object_row(
            path_id=20,
            serialized_file="CAB-other",
            pptrs=[{
                "path": "$.m_PlayableAsset",
                "pathId": 10,
                "status": "resolved",
                "target": {
                    "serializedFile": "CAB-shared-name",
                    "pathId": 10,
                },
            }],
        )
        relations, _ = audit.collect_reverse_relations(
            [referrer],
            targets,
            "Persistent",
        )
        self.assertEqual(relations, [])

    def test_ancestor_chain_reaches_exact_root(self) -> None:
        objects = {
            1: {
                "transformComponentPathId": 101,
                "parentTransformPathId": 0,
            },
            2: {
                "transformComponentPathId": 102,
                "parentTransformPathId": 101,
            },
            3: {
                "transformComponentPathId": 103,
                "parentTransformPathId": 102,
            },
        }
        self.assertEqual(audit.ancestor_chain(objects, 3), [3, 2, 1])

    def test_story_index_keys_reads_compact_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "index.json"
            path.write_text(
                json.dumps({
                    "entries": [
                        {"k": "cutscene_a"},
                        {"k": "dlg_b"},
                    ],
                }),
                encoding="utf-8",
            )
            self.assertEqual(
                audit.story_index_keys(path),
                {"cutscene_a", "dlg_b"},
            )


if __name__ == "__main__":
    unittest.main()
