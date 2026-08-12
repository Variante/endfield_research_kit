from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
RECOVERY_ROOT = SCRIPTS_ROOT / "story_recovery"
for path in (SCRIPTS_ROOT, RECOVERY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_spaceship_story_content_audit as audit  # noqa: E402
from common import spaceship_story_non_mission_content_keys  # noqa: E402


def dialog_tree(option_type: str = "Beyond.Gameplay.SpaceshipOptionWorkData") -> dict:
    return {
        "_assetName": "dlg_npc_0013_aglina_spaceshippresent",
        "type": "Beyond.Gameplay.DialogTree",
        "nodes": [{
            "$id": "0",
            "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
            "_actorNodeData": {
                "mfTrunkActionData": {
                    "_trunkId": "sim_work_aglina_01",
                },
            },
        }, {
            "$id": "1",
            "$type": "Beyond.Gameplay.DialogTreeOptionNode",
            "_normalOptions": [{
                "_optionId": "dlg_spaceship_present_o_1_2",
                "$type": option_type,
            }],
        }],
        "connections": [{
            "$type": "Beyond.Gameplay.DialogTreeConnection",
            "_sourceNode": {"$ref": "0"},
            "_targetNode": {"$ref": "1"},
        }],
    }


class SpaceshipStoryContentAuditTests(unittest.TestCase):
    def test_typed_spaceship_dialog_tree_closes_complete_bucket(self) -> None:
        dialog_rows = {
            "sim_work_aglina_01": {
                "audioOverride": "au_sim_work_aglina_01",
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "tree.json"
            source.write_text("{}", encoding="utf-8")
            rows, paths = audit.collect_dialog_tree_classifications(
                dialog_rows,
                [(dialog_tree()["_assetName"], source, dialog_tree())],
            )
        self.assertEqual(1, len(rows))
        self.assertEqual("misc_sim_work_aglina", rows[0]["storyKey"])
        self.assertEqual(
            ["Beyond.Gameplay.SpaceshipOptionWorkData"],
            rows[0]["consumerClasses"],
        )
        self.assertEqual({source}, paths)

        untyped = dialog_tree("Beyond.Gameplay.DialogOptionData")
        rows, _paths = audit.collect_dialog_tree_classifications(
            dialog_rows,
            [(untyped["_assetName"], source, untyped)],
        )
        self.assertEqual([], rows)

    def test_unconsumed_definition_uses_typed_actor_family_context(self) -> None:
        dialog_rows = {
            "sim_gift_fixture_recv_01": {
                "audioOverride": "au_sim_gift_fixture_recv_01",
            },
            "sim_gift_fixture_recvbye_01": {
                "audioOverride": "au_sim_gift_fixture_recvbye_01",
            },
        }
        tree = dialog_tree("Beyond.Gameplay.SpaceshipOptionGiftData")
        tree["_assetName"] = "dlg_npc_9999_fixture_spaceshipgift"
        tree["nodes"][0]["_actorNodeData"]["mfTrunkActionData"][
            "_trunkId"
        ] = "sim_gift_fixture_recv_01"
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "fixture_tree.json"
            source.write_text("{}", encoding="utf-8")
            rows, paths = audit.collect_unconsumed_spaceship_dialog_definitions(
                dialog_rows,
                [(tree["_assetName"], source, tree)],
                {"misc_sim_gift_fixture_recv"},
            )
        self.assertEqual(1, len(rows))
        self.assertEqual(
            "misc_sim_gift_fixture_recvbye",
            rows[0]["storyKey"],
        )
        self.assertEqual("gift", rows[0]["dialogFamily"])
        self.assertEqual("fixture", rows[0]["actorId"])
        self.assertEqual({source}, paths)

        tree["nodes"].append({
            "$id": "2",
            "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
            "_actorNodeData": {
                "mfTrunkActionData": {
                    "_trunkId": "sim_gift_fixture_recvbye_01",
                },
            },
        })
        rows, _paths = audit.collect_unconsumed_spaceship_dialog_definitions(
            dialog_rows,
            [(tree["_assetName"], source, tree)],
            {"misc_sim_gift_fixture_recv"},
        )
        self.assertEqual([], rows)

    def test_profile_talk_requires_exact_audio_pair_and_complete_bucket(self) -> None:
        character_rows = {
            "chr_0013_aglina": {
                "profileVoice": [{
                    "voId": "chr_0013_aglina_sim_talk_lv02_01",
                }, {
                    "voId": "chr_0013_aglina_sim_talk_lv02_02",
                }],
            },
        }
        dialog_rows = {
            "sim_talk_aglina_lv02_01": {
                "audioOverride": "au_sim_talk_aglina_lv02_01",
            },
            "sim_talk_aglina_lv02_02": {
                "audioOverride": "au_sim_talk_aglina_lv02_02",
            },
        }
        audio_rows = {}
        for index, suffix in enumerate(("01", "02")):
            for stem, channel in ((
                f"chr_0013_aglina_sim_talk_lv02_{suffix}",
                "chr_0013_aglina",
            ), (
                f"au_sim_talk_aglina_lv02_{suffix}",
                "aglina",
            )):
                audio_rows[f"{index}-{stem}"] = {
                    "path": f"v1d0/Characters/chr_0013_aglina/{stem}.wem",
                    "speakerChannel": channel,
                    "codec": 4,
                    "isPlaceholder": False,
                    "wavDuration": float(index + 1),
                    "wavDurationEN": float(index + 2),
                    "wavDurationJP": float(index + 3),
                    "wavDurationKR": float(index + 4),
                }
        rows = audit.collect_profile_talk_classifications(
            character_rows,
            dialog_rows,
            audio_rows,
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("misc_sim_talk_aglina_lv02", rows[0]["storyKey"])

        audio_rows["0-au_sim_talk_aglina_lv02_01"]["wavDuration"] = 99.0
        self.assertEqual(
            [],
            audit.collect_profile_talk_classifications(
                character_rows,
                dialog_rows,
                audio_rows,
            ),
        )

    def test_report_loader_fails_closed_on_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.json"
            source.write_text("fixture", encoding="utf-8")
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            report = root / "report.json"
            report.write_text(json.dumps({
                "_schema": audit.SCHEMA,
                "nativeEvidence": {
                    "validated": True,
                    "mappingId": audit.NATIVE_MAPPING_ID,
                    "gameAssemblySha256": audit.EXPECTED_GAMEASSEMBLY_SHA256,
                    "metadataSha256": audit.EXPECTED_METADATA_SHA256,
                },
                "sources": [{
                    "path": "source.json",
                    "bytes": source.stat().st_size,
                    "sha256": source_hash,
                }],
                "classifications": [{
                    "storyKey": "misc_sim_work_aglina",
                    "recoveryStatus":
                        "closed_exact_spaceship_runtime_non_mission_content",
                    "evidenceKind": "spaceship_dialog_tree",
                    "contentClass": "operator_spaceship_dialog_tree",
                    "lineIds": ["sim_work_aglina_01"],
                    "dialogTreeRoots": [
                        "dlg_npc_0013_aglina_spaceshippresent",
                    ],
                    "consumerClasses": [
                        "Beyond.Gameplay.SpaceshipOptionWorkData",
                    ],
                    "sourceFiles": ["source.json"],
                    "nativeMappingId": audit.NATIVE_MAPPING_ID,
                }],
            }), encoding="utf-8")
            loaded = spaceship_story_non_mission_content_keys(
                report,
                source_root=root,
            )
            self.assertIn("misc_sim_work_aglina", loaded)

            payload = json.loads(report.read_text(encoding="utf-8"))
            payload["classifications"].append({
                "storyKey": "misc_sim_gift_fixture_recvbye",
                "recoveryStatus": (
                    "deferred_current_build_spaceship_dialog_definition_"
                    "without_tree_carrier"
                ),
                "evidenceKind": (
                    "spaceship_dialog_definition_without_tree_carrier"
                ),
                "contentClass": "operator_spaceship_dialog_definition",
                "lineIds": ["sim_gift_fixture_recvbye_01"],
                "dialogTreeRoots": ["dlg_npc_9999_fixture_spaceshipgift"],
                "consumerClasses": [
                    "Beyond.Gameplay.SpaceshipOptionGiftData",
                ],
                "dialogFamily": "gift",
                "actorId": "fixture",
                "carrierStatus": (
                    "absent_from_all_related_typed_dialog_trees"
                ),
                "consumerBoundary": "fixture exact typed negative boundary",
                "sourceFiles": ["source.json"],
                "nativeMappingId": audit.NATIVE_MAPPING_ID,
            })
            report.write_text(json.dumps(payload), encoding="utf-8")
            loaded = spaceship_story_non_mission_content_keys(
                report,
                source_root=root,
            )
            self.assertIn("misc_sim_gift_fixture_recvbye", loaded)

            payload["classifications"][0]["nativeMappingId"] = "stale"
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertNotIn(
                "misc_sim_work_aglina",
                spaceship_story_non_mission_content_keys(
                    report, source_root=root
                ),
            )

            payload["classifications"][0]["nativeMappingId"] = (
                audit.NATIVE_MAPPING_ID
            )
            payload["classifications"][0]["sourceFiles"] = ["unhashed.json"]
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertNotIn(
                "misc_sim_work_aglina",
                spaceship_story_non_mission_content_keys(
                    report, source_root=root
                ),
            )

            payload["classifications"][0]["sourceFiles"] = ["source.json"]
            report.write_text(json.dumps(payload), encoding="utf-8")
            source.write_text("drift", encoding="utf-8")
            self.assertEqual(
                {},
                spaceship_story_non_mission_content_keys(
                    report,
                    source_root=root,
                ),
            )


class SpaceshipNativeGateTests(unittest.TestCase):
    """A different or absent client skips the step instead of failing it."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.report = self.root / "report.json"
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("ENDFIELD_REQUIRE_NATIVE_EVIDENCE", None)

    def run_audit(self, gameassembly: Path) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = audit.main([
                "--gameassembly", str(gameassembly),
                "--metadata", str(gameassembly),
                "--out", str(self.report),
                "--markdown", str(self.root / "report.md"),
            ])
        return code, stderr.getvalue()

    def test_absent_client_skips_without_writing_a_report(self) -> None:
        code, stderr = self.run_audit(self.root / "absent.dll")
        self.assertEqual(0, code)
        self.assertIn("[spaceship-story-content] skipped:", stderr)
        self.assertFalse(self.report.exists())

    def test_another_build_skips_and_names_both_builds(self) -> None:
        other = self.root / "GameAssembly.dll"
        other.write_bytes(b"a different build")

        code, stderr = self.run_audit(other)
        self.assertEqual(0, code)
        self.assertIn("different build", stderr)
        self.assertIn(audit.EXPECTED_GAMEASSEMBLY_SHA256[:12].lower(), stderr)
        self.assertFalse(self.report.exists())

    def test_required_mode_still_fails_closed(self) -> None:
        os.environ["ENDFIELD_REQUIRE_NATIVE_EVIDENCE"] = "1"

        code, stderr = self.run_audit(self.root / "absent.dll")
        self.assertEqual(1, code)
        self.assertIn("[spaceship-story-content] failed:", stderr)


if __name__ == "__main__":
    unittest.main()
