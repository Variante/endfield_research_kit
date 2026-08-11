from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "gameplay_builder" / "projectiles.py"
SPEC = importlib.util.spec_from_file_location("gameplay_builder_projectiles", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProjectileBuilderTests(unittest.TestCase):
    def test_current_projectile_fields_are_preserved(self) -> None:
        component = {
            "$decoded": True,
            "id": "projectile_chr_0001_test_attack1",
            "targetFilter": {
                "serializedLayout": "current",
                "tagEntryLayout": "idOnly",
                "filterObjectType": True,
                "objectType": {"value": 2, "enumType": "Beyond.Gameplay.TargetObjectType"},
                "tagQuery": {
                    "queryType": {"value": 0, "name": "HasAny"},
                    "tags": [{"tagId": {"value": 123, "hex": "0x0000007b"}}],
                },
            },
            "collisionDetectTiming": {"value": 1, "enumType": "Beyond.Gameplay.ProjectileCollisionDetectTiming"},
            "hitAndBlockDetectDelayTime": {"value": 0.25, "blackboardKey": ""},
            "hitAndBlockDetectDelayDistance": {"value": 3.5, "blackboardKey": ""},
            "canTraceTargetAfterReach": True,
            "moveSegments": [{"skipHitAndBlockDetection": True}],
            "tail": {
                "remainingRawWordCount": 0,
                "moveModeDict": {
                    "values": [{
                        "key": "surround",
                        "surroundCenterKey": "TargetPoint",
                        "surroundLineSpeed": {"value": 4.0, "blackboardKey": ""},
                        "reachOnMaxCentrifugalRadius": True,
                        "surroundAxisRotation": {"valueCandidate": {"x": 0.0, "y": 1.0, "z": 0.0}},
                    }],
                },
                "structuredRemainingTail": {
                    "structuredDecodeStatus": "decoded",
                    "remainingRawWordCount": 0,
                    "consumedWordCount": 1,
                    "wordCount": 1,
                    "postAlertEffectSoundTail": {},
                },
            },
        }
        template = {
            "$decoded": True,
            "skillDataBundle": {
                "allActiveSkillId": ["chr_0001_test_attack1_hit"],
                "normalSkillId": "chr_0001_test_normal_skill",
                "ultimateSkillId": "chr_0001_test_ultimate_skill",
                "comboSkillId": "chr_0001_test_combo_skill",
                "hudPanelName": "test_panel",
            },
        }
        payload = {
            "$animestudio": {"name": "data_projectile_chr_0001_test_attack1", "pathId": 7},
            "references": {"RefIds": [
                {"type": {"class": "ProjectileTemplateData"}, "data": template},
                {"type": {"class": "ProjectileComponentData"}, "data": component},
            ]},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "StreamingAssets" / "json_by_type" / "MonoBehaviour"
            root.mkdir(parents=True)
            source = root / "data_projectile_chr_0001_test_attack1.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            entry = MODULE.build_entry(source, root)

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertTrue(entry["confidence"]["byteComplete"])
        self.assertTrue(entry["targeting"]["targetFilter"]["filterObjectType"])
        self.assertEqual(entry["targeting"]["targetFilter"]["tagEntryLayout"], "idOnly")
        self.assertEqual(entry["targeting"]["targetFilter"]["tagQuery"]["tags"][0]["tagId"]["value"], 123)
        self.assertEqual(entry["targeting"]["collisionDetectTiming"]["value"], 1)
        self.assertEqual(entry["movement"]["segments"][0]["skipHitAndBlockDetection"], True)
        self.assertEqual(entry["movement"]["modes"][0]["surroundCenterKey"], "TargetPoint")
        self.assertEqual(entry["template"]["normalSkillId"], "chr_0001_test_normal_skill")
        self.assertEqual(entry["template"]["hudPanelName"], "test_panel")

    def test_hydrates_current_audio_index_by_unsigned_event_hash(self) -> None:
        event_hash = 0xFFFFFFFF
        entry = {"sounds": {"launchSound": {"value": -1, "hex": "0xffffffff"}}}
        with tempfile.TemporaryDirectory() as directory:
            index_path = Path(directory) / "index.json"
            index_path.write_text(json.dumps({
                "projectileEventHashes": [event_hash],
                "eventEvidence": [{
                    "eventId": "au_projectile_named_event",
                    "eventHash": event_hash,
                }],
                "events": [{
                    "eventId": "au_projectile_named_event",
                    "eventHash": event_hash,
                    "src": "/export_full/structured/Audio/shared/wwise/unknown/7.wav",
                    "mediaId": 7,
                    "format": "wav",
                }],
            }), encoding="utf-8")
            stats = MODULE.hydrate_audio_links([entry], index_path)

        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats["projectileSoundRefsLinked"], 1)
        launch = entry["sounds"]["launchSound"]
        self.assertTrue(launch["event"]["foundInWwise"])
        self.assertEqual(launch["event"]["canonicalEventIds"], ["au_projectile_named_event"])
        self.assertEqual(launch["audio"][0]["mediaId"], 7)


if __name__ == "__main__":
    unittest.main()
