import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import build_option_override_coverage_audit as audit


class OptionOverrideCoverageAuditTests(unittest.TestCase):
    def fixture(self, overrides: dict) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        conv_root = root / "conv"
        conv_root.mkdir()
        scene = "dlg_fixture_1"
        option_ids = [
            "option_dlg_fixture_1_1_001",
            "option_dlg_fixture_1_1_002",
            "option_dlg_fixture_1_1_003",
        ]
        (conv_root / f"{scene}.json").write_text(
            json.dumps(
                {
                    "key": scene,
                    "lines": [
                        {"id": "dlg_fixture_1_001"},
                        {"id": "dlg_fixture_1_002"},
                        {"id": "dlg_fixture_1_003"},
                        {"id": "dlg_fixture_1_004"},
                    ],
                    "optionGroups": [
                        {
                            "g": "1",
                            "options": [{"id": option_id} for option_id in option_ids],
                        }
                    ],
                    "warnings": [
                        {
                            "code": "inferredOptionResponse",
                            "reason": "optionTargetsMissing",
                            "groups": [
                                {
                                    "group": "1",
                                    "source": "dialogTimeline",
                                    "optionIds": option_ids,
                                    "candidateLineIdsByOption": {
                                        option_ids[0]: ["dlg_fixture_1_002"],
                                        option_ids[1]: ["dlg_fixture_1_003"],
                                        option_ids[2]: ["dlg_fixture_1_004"],
                                    },
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        overrides_path = root / "options.json"
        overrides_path.write_text(
            json.dumps({"scenes": {scene: overrides}}),
            encoding="utf-8",
        )
        return temporary, conv_root, overrides_path

    def test_response_evidence_distinguishes_match_conflict_and_candidate(self):
        option_prefix = "option_dlg_fixture_1_1_00"
        temporary, conv_root, overrides_path = self.fixture(
            {
                "responses": {
                    option_prefix + "1": ["dlg_fixture_1_002"],
                    option_prefix + "2": ["dlg_fixture_1_004"],
                }
            }
        )
        self.addCleanup(temporary.cleanup)

        payload = audit.build_payload("CN", conv_root, overrides_path)

        by_option = {
            row["optionId"]: row for row in payload["responseEvidenceRows"]
        }
        self.assertEqual(
            by_option[option_prefix + "1"]["classification"],
            "manual-matches-inference",
        )
        self.assertEqual(
            by_option[option_prefix + "2"]["classification"],
            "manual-conflicts-inference",
        )
        self.assertEqual(
            by_option[option_prefix + "3"]["classification"],
            "candidate-uncovered",
        )
        self.assertEqual(payload["counts"]["responseConflicts"], 1)
        self.assertEqual(payload["counts"]["uncoveredResponseCandidates"], 1)

    def test_stale_override_targets_remain_fail_closed(self):
        option_id = "option_dlg_fixture_1_1_001"
        temporary, conv_root, overrides_path = self.fixture(
            {"responses": {option_id: ["dlg_fixture_1_missing"]}}
        )
        self.addCleanup(temporary.cleanup)

        payload = audit.build_payload("CN", conv_root, overrides_path)

        self.assertEqual(payload["counts"]["invalidOverrideReferences"], 1)
        self.assertEqual(
            payload["invalidOverrideReferences"][0]["problem"],
            "missing target line",
        )
        self.assertEqual(
            payload["responseEvidenceRows"][0]["classification"],
            "invalid-override",
        )

    def test_candidate_paths_prefer_full_branch_path(self):
        option_id = "option_dlg_fixture_1_1_001"
        group = {
            "optionIds": [option_id],
            "candidateLineIdsByOption": {option_id: ["line_a"]},
            "branchLineIdsByOption": {option_id: ["line_a", "line_b"]},
        }

        self.assertEqual(
            audit.response_candidate_paths(group, [option_id]),
            {option_id: ["line_a", "line_b"]},
        )


if __name__ == "__main__":
    unittest.main()
