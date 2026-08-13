from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


from scripts.story_builder.animestudio_story_objects import carrier as audit


def object_row(
    scalars: list[list[object]],
    *,
    decode_status: str = "decoded",
    script_name: str | None = "Beyond.Gameplay.TestCarrier",
    truncated: bool = False,
    scene_context: dict | None = None,
) -> dict:
    row = {
        "recordType": "object",
        "schemaVersion": 1,
        "object": {
            "serializedFile": "CAB-test",
            "source": "VFS/test.chk",
            "sourceOffset": 20,
            "pathId": 30,
        },
        "type": "MonoBehaviour",
        "decodeStatus": decode_status,
        "schemaId": "a" * 64,
        "scalarsTruncated": truncated,
        "script": {
            "fileId": 1,
            "pathId": 2,
            "fullName": script_name,
            "assembly": "Gameplay.Beyond.dll" if script_name else None,
        },
        "scalars": scalars,
        "pptrs": [],
    }
    if scene_context is not None:
        row["sceneContext"] = scene_context
    return row


class AnimeStudioStoryCarrierAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.targets = {"dlg_e11m1_30": {"e11m1"}}

    def test_exact_story_owner_runtime_fields_create_candidate_only(self) -> None:
        row = object_row([
            ["$.dialogId", "s", "dlg_e11m1_30"],
            ["$.missionId", "s", "e11m1"],
            ["$.sceneNumId", "i", 231],
            ["$.scriptId", "i", 23100010001],
        ])

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        self.assertEqual(result["counts"]["typedCarrierCandidates"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(
            candidate["candidateStatus"],
            "exact_same_object_story_owner_and_runtime_identifiers",
        )
        self.assertEqual(
            candidate["ownerMissionAgreement"],
            "owner_agrees_with_gap_mission",
        )
        self.assertEqual(candidate["edgeStatus"], "no_edge_candidate_only")

    def test_boolean_scalar_is_valid_and_does_not_become_an_identifier(self) -> None:
        row = object_row([
            ["$.dialogId", "s", "dlg_e11m1_30"],
            ["$.missionId", "s", "e11m1"],
            ["$.useRadioTriggerOnce", "b", True],
        ])

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        candidate = result["candidates"][0]
        self.assertEqual(candidate["ownerFields"][0]["value"], "e11m1")
        self.assertEqual(candidate["runtimeFields"], [])

    def test_malformed_scalar_reports_object_and_expected_type_contract(self) -> None:
        row = object_row([["$.enabled", "b", 1]])

        with self.assertRaisesRegex(
            audit.AuditError,
            r"source='VFS/test\.chk'.*pathId=30 index=0; expected .*b:boolean",
        ):
            audit.scalar_rows(row)

    def test_exact_scene_context_is_preserved_without_promoting_an_edge(self) -> None:
        scene_context = {
            "gameObjectName": "RadioTriggerZone",
            "worldPosition": {"x": 1.0, "y": 2.0, "z": 3.0},
            "worldPositionStatus": "exact_transform_hierarchy",
        }
        row = object_row(
            [
                ["$.radioId", "s", "dlg_e11m1_30"],
                ["$.missionId", "s", "e11m1"],
            ],
            scene_context=scene_context,
        )

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        self.assertEqual(result["candidates"][0]["sceneContext"], scene_context)
        self.assertEqual(
            result["counts"]["exactValueMatchesWithExactWorldPosition"],
            1,
        )
        self.assertEqual(result["candidates"][0]["edgeStatus"], "no_edge_candidate_only")

    def test_untyped_name_match_is_rejected_even_with_mission_id(self) -> None:
        row = object_row([
            ["$.m_Name", "s", "dlg_e11m1_30"],
            ["$.missionId", "s", "e11m1"],
        ])

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        self.assertEqual(result["counts"]["typedCarrierCandidates"], 0)
        self.assertIn(
            "story_value_is_not_in_a_typed_story_identifier_field",
            result["rejectedExactValueMatchSamples"][0]["rejectionReasons"],
        )

    def test_substring_and_neighbor_values_never_match(self) -> None:
        rows = [
            object_row([["$.dialogId", "s", "prefix_dlg_e11m1_30"]]),
            object_row([["$.missionId", "s", "e11m1"]]),
        ]

        result = audit.audit_object_rows(rows, self.targets, "StreamingAssets")

        self.assertEqual(result["counts"].get("objectsWithExactTargetValue", 0), 0)
        self.assertEqual(result["candidates"], [])

    def test_gendered_cutscene_variant_matches_only_canonical_target(self) -> None:
        targets = {"cutscene_e11m1_fire_end": {"e11m1"}}
        row = object_row([
            ["$.cutsceneId", "s", "f_cutscene_e11m1_fire_end"],
            ["$.missionId", "s", "e11m1"],
        ])

        result = audit.audit_object_rows(
            [row],
            targets,
            "StreamingAssets",
        )

        candidate = result["candidates"][0]
        self.assertEqual(candidate["storyKey"], "cutscene_e11m1_fire_end")
        self.assertEqual(
            candidate["sourceStoryValue"],
            "f_cutscene_e11m1_fire_end",
        )
        self.assertEqual(
            candidate["storyValueNormalization"],
            "canonical_cutscene_variant",
        )
        self.assertEqual(
            audit.canonical_target_story_key(
                "prefix_cutscene_e11m1_fire_end",
                targets,
            ),
            "",
        )
        self.assertEqual(
            audit.canonical_target_story_key(
                "f_cutscene_e11m1_fire_end_Actor",
                targets,
            ),
            "",
        )

    def test_empty_or_zero_owner_runtime_fields_do_not_qualify(self) -> None:
        row = object_row([
            ["$.dialogId", "s", "dlg_e11m1_30"],
            ["$.missionId", "s", ""],
            ["$.sceneNumId", "i", 0],
            ["$.scriptId", "i", 0],
        ])

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        self.assertEqual(result["counts"]["typedCarrierCandidates"], 0)
        self.assertIn(
            "no_owner_or_runtime_identifier_in_same_object",
            result["rejectedExactValueMatchSamples"][0]["rejectionReasons"],
        )

    def test_partial_or_truncated_object_is_rejected(self) -> None:
        for row in (
            object_row(
                [
                    ["$.dialogId", "s", "dlg_e11m1_30"],
                    ["$.missionId", "s", "e11m1"],
                ],
                decode_status="partial",
            ),
            object_row(
                [
                    ["$.dialogId", "s", "dlg_e11m1_30"],
                    ["$.missionId", "s", "e11m1"],
                ],
                truncated=True,
            ),
        ):
            with self.subTest(row=row):
                result = audit.audit_object_rows(
                    [row],
                    self.targets,
                    "StreamingAssets",
                )
                self.assertEqual(
                    result["counts"].get("typedCarrierCandidates", 0),
                    0,
                )
                self.assertIn(
                    "object_is_not_a_complete_decoded_schema_row",
                    result["rejectedExactValueMatchSamples"][0][
                        "rejectionReasons"
                    ],
                )

    def test_unresolved_monoscript_identity_is_rejected(self) -> None:
        row = object_row(
            [
                ["$.dialogId", "s", "dlg_e11m1_30"],
                ["$.missionId", "s", "e11m1"],
            ],
            script_name=None,
        )

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        self.assertIn(
            "object_type_or_monoscript_identity_is_unresolved",
            result["rejectedExactValueMatchSamples"][0]["rejectionReasons"],
        )

    def test_conflicting_exact_owner_stays_visible_as_conflict(self) -> None:
        row = object_row([
            ["$.dialogId", "s", "dlg_e11m1_30"],
            ["$.missionId", "s", "e10m4"],
        ])

        result = audit.audit_object_rows([row], self.targets, "StreamingAssets")

        self.assertEqual(
            result["candidates"][0]["ownerMissionAgreement"],
            "owner_conflicts_with_gap_mission",
        )
        self.assertEqual(result["candidates"][0]["edgeStatus"], "no_edge_candidate_only")

    def test_quest_id_recovers_only_its_exact_mission_prefix(self) -> None:
        self.assertEqual(audit.mission_from_quest_id("e11m1_q#17"), "e11m1")
        self.assertEqual(audit.mission_from_quest_id("e11m10_q#17"), "e11m10")
        self.assertEqual(audit.mission_from_quest_id("e11m1"), "")

    def test_gap_targets_use_stable_core_isolated_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gap.json"
            path.write_text(
                json.dumps({
                    "missions": [{
                        "mission": "e11m4",
                        "coreIsolatedSceneKeys": [
                            "radio_e11m4_29",
                            "radio_e11m4_30",
                        ],
                        "actionableCoreIsolatedSceneKeys": [
                            "radio_e11m4_30",
                        ],
                    }],
                }),
                encoding="utf-8",
            )

            targets = audit.load_gap_targets(path)

        self.assertEqual(
            targets,
            {
                "radio_e11m4_29": {"e11m4"},
                "radio_e11m4_30": {"e11m4"},
            },
        )
        self.assertEqual(
            audit.target_set_sha256(targets),
            audit.target_set_sha256({
                "radio_e11m4_30": {"e11m4"},
                "radio_e11m4_29": {"e11m4"},
            }),
        )

    def test_published_scan_uses_the_export_root_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            export_root = Path(temporary) / "export_full"
            index_dir = audit.animestudio_object_index_dir(
                export_root,
                "StreamingAssets",
            )
            index_dir.mkdir(parents=True)
            objects = index_dir / "objects.jsonl.gz"
            with gzip.open(objects, "wt", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        object_row(
                            [
                                ["$.dialogId", "s", "dlg_e11m1_30"],
                                ["$.missionId", "s", "e11m1"],
                            ]
                        )
                    )
                    + "\n"
                )
            summary = {
                "complete": True,
                "mergeContract": "test",
                "stageSignature": {"sha256": "a" * 64},
                "counts": {"objects": 1},
                "outputs": {"objects": {"path": objects.name}},
            }

            with mock.patch.object(
                audit,
                "load_animestudio_object_index_summary",
                return_value=summary,
            ) as load_summary:
                result = audit.scan_published_source(
                    export_root,
                    "StreamingAssets",
                    self.targets,
                )

            load_summary.assert_called_once_with(
                export_root,
                "StreamingAssets",
            )
            self.assertEqual(result["counts"]["objectsScanned"], 1)
            self.assertEqual(result["index"]["objects"], str(objects))


if __name__ == "__main__":
    unittest.main()
