from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.source_provenance import (
    enrich_story_connection_original_files,
)


class StoryConnectionSourceProvenanceTests(unittest.TestCase):
    def test_collects_nested_paths_without_relation_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streaming = (
                root
                / "export_full"
                / "structured"
                / "StreamingAssets"
                / "Data"
                / "Json"
                / "LevelScriptData"
                / "map_a"
                / "1001.json"
            )
            persistent = (
                root
                / "export_full"
                / "structured"
                / "Persistent"
                / "Data"
                / "Json"
                / "MissionRuntimeAsset"
                / "mission_a.json"
            )
            level_data = (
                root
                / "export_full"
                / "structured"
                / "StreamingAssets"
                / "Data"
                / "Json"
                / "LevelData"
                / "map_a"
                / "map_a.json"
            )
            streaming.parent.mkdir(parents=True)
            persistent.parent.mkdir(parents=True)
            level_data.parent.mkdir(parents=True)
            streaming.write_bytes(b"level-script")
            persistent.write_bytes(b"mission-runtime")
            level_data.write_bytes(b"level-data")
            payload = {
                "mission_a": {
                    "missionStoryConnections": [{
                        "key": "radio_a_1",
                        "relation": "new_generic_relation",
                        "sourceFiles": [
                            "Data/Json/LevelScriptData/map_a/1001.json",
                            "export_full/structured/Persistent/Data/Json/MissionRuntimeAsset/mission_a.json",
                            "map_a.json",
                            "CAB-not-a-file",
                            "Data/Json/Missing/nope.json",
                        ],
                    }],
                    "quests": [{
                        "storyConnections": [{
                            "key": "dlg_a_1",
                            "relation": "nested_generic_relation",
                            "sourceFiles": [
                                "Data/Json/LevelScriptData/map_a/1001.json",
                            ],
                        }],
                    }],
                },
            }

            report = enrich_story_connection_original_files(payload, root=root)

            row = payload["mission_a"]["missionStoryConnections"][0]
            self.assertEqual(
                row["relatedOriginalFilesValidation"]["status"],
                "partial_unresolved_source_references",
            )
            self.assertEqual(
                row["relatedOriginalFilesValidation"]["unresolvedSourceReferences"],
                ["Data/Json/Missing/nope.json"],
            )
            self.assertEqual(
                {entry["kind"] for entry in row["relatedOriginalFiles"]},
                {"level_data", "level_script", "mission_runtime"},
            )
            level_entry = next(
                entry
                for entry in row["relatedOriginalFiles"]
                if entry["kind"] == "level_script"
            )
            self.assertEqual(
                level_entry["sha256"],
                hashlib.sha256(b"level-script").hexdigest(),
            )
            nested = payload["mission_a"]["quests"][0]["storyConnections"][0]
            self.assertEqual(
                nested["relatedOriginalFiles"][0]["kind"],
                "level_script",
            )
            self.assertEqual(report["summary"]["relationRows"], 2)
            self.assertEqual(report["summary"]["attachedOriginalFiles"], 4)
            self.assertEqual(report["summary"]["nonPathSourceReferences"], 1)
            self.assertEqual(report["summary"]["partialMissionCount"], 1)

    def test_ignores_asset_tokens_and_non_relation_source_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "mission_a": {
                    "assetPaths": ["Data/Json/not-a-connection.json"],
                    "storyConnections": [{
                        "key": "dlg_a_1",
                        "relation": "context",
                        "sourceFiles": ["CAB-123", "bare-object-name"],
                    }],
                },
            }

            report = enrich_story_connection_original_files(payload, root=root)

            row = payload["mission_a"]["storyConnections"][0]
            self.assertEqual(row["relatedOriginalFilesValidation"]["status"], "validated")
            self.assertEqual(row["relatedOriginalFilesValidation"]["sourceReferencesConsidered"], 0)
            self.assertEqual(
                row["relatedOriginalFilesValidation"]["nonPathSourceReferences"],
                ["CAB-123", "bare-object-name"],
            )
            self.assertNotIn("relatedOriginalFiles", row)
            self.assertEqual(report["summary"]["unresolvedSourceReferences"], 0)


if __name__ == "__main__":
    unittest.main()
