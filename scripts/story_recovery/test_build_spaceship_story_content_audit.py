from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


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
            payload["classifications"][0]["nativeMappingId"] = "stale"
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(
                {},
                spaceship_story_non_mission_content_keys(
                    report,
                    source_root=root,
                ),
            )

            payload["classifications"][0]["nativeMappingId"] = (
                audit.NATIVE_MAPPING_ID
            )
            payload["classifications"][0]["sourceFiles"] = ["unhashed.json"]
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(
                {},
                spaceship_story_non_mission_content_keys(
                    report,
                    source_root=root,
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


if __name__ == "__main__":
    unittest.main()
