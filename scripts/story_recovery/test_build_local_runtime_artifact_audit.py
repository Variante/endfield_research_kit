from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_local_runtime_artifact_audit as audit  # noqa: E402


class LocalRuntimeArtifactAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.story_keys = {"dlg_e11m4_3", "radio_e11m4_7"}
        self.mission_ids = {"e11m4"}

    def test_typed_same_object_candidate_is_observational_only(self) -> None:
        payload = {
            "dialogId": "dlg_e11m4_3",
            "missionId": "e11m4",
            "scriptId": 23100030043,
        }

        result = audit.audit_json_object(
            payload,
            story_keys=self.story_keys,
            mission_ids=self.mission_ids,
            relative_file="ClientData/test.json",
        )

        self.assertEqual(result["counts"]["sameObjectCandidates"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["status"],
            "observational_same_object_candidate_no_edge",
        )
        self.assertEqual(candidate["ownerMissions"], ["e11m4"])

    def test_untyped_and_neighbor_values_do_not_create_candidate(self) -> None:
        payload = {
            "name": "dlg_e11m4_3",
            "neighbor": {"missionId": "e11m4"},
        }

        result = audit.audit_json_object(
            payload,
            story_keys=self.story_keys,
            mission_ids=self.mission_ids,
            relative_file="ClientData/test.json",
        )

        self.assertEqual(result["storyKeys"], ["dlg_e11m4_3"])
        self.assertEqual(result["counts"]["sameObjectCandidates"], 0)

    def test_log_match_keeps_ids_and_line_number_but_not_text(self) -> None:
        result = audit.audit_log_lines(
            [
                "ordinary line\n",
                "play dlg_e11m4_3 while mission e11m4 is active\n",
                "ErrSceneLevelScriptTriggerCustomEventFailed "
                "[scene map02_lv002 runtime not exist]\n",
            ],
            story_keys=self.story_keys,
            mission_ids=self.mission_ids,
            relative_file="Player.log",
        )

        self.assertEqual(result["storyMatches"], [{
            "sourceFile": "Player.log",
            "line": 2,
            "storyKeys": ["dlg_e11m4_3"],
            "missionIdsOnSameLine": ["e11m4"],
            "status": "observational_log_line_no_edge",
        }])
        self.assertNotIn("text", result["storyMatches"][0])
        self.assertEqual(
            result["levelScriptErrors"][0]["scene"],
            "map02_lv002",
        )

    def test_build_audit_scans_only_supported_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            story_index = root / "index.json"
            story_index.write_text(
                json.dumps({
                    "entries": [
                        {"k": "dlg_e11m4_3", "m": "e11m4"},
                        {"k": "radio_e11m4_7", "m": "e11m4"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "Player.log").write_text(
                "play dlg_e11m4_3\n",
                encoding="utf-8",
            )
            client_data = root / "ClientData"
            client_data.mkdir()
            (client_data / "Default.json").write_text(
                json.dumps({"dialogId": "dlg_e11m4_3"}),
                encoding="utf-8",
            )
            (root / "ignored.txt").write_text(
                "radio_e11m4_7",
                encoding="utf-8",
            )

            result = audit.build_audit(root, story_index)

        self.assertEqual(result["counts"]["filesScanned"], 2)
        self.assertEqual(result["counts"]["observedStoryLogLines"], 1)
        self.assertEqual(result["counts"]["sameObjectCandidates"], 0)
        self.assertEqual(
            result["classification"],
            "observational_candidates_require_manual_schema_review",
        )

    def test_account_directory_is_redacted(self) -> None:
        root = Path("C:/runtime")
        path = root / "ClientData" / "User" / "123456789" / "Default.json"

        self.assertEqual(
            audit.report_relative_path(path, root),
            "ClientData/User/<account>/Default.json",
        )


if __name__ == "__main__":
    unittest.main()
