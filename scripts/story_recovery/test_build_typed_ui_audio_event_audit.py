import tempfile
import unittest
from pathlib import Path

from scripts.build_audio_semantics import audio_hash_generator_compute
from scripts.story_recovery import build_typed_ui_audio_event_audit as audit


class TypedUiAudioEventAuditTests(unittest.TestCase):
    def test_valid_alias_requires_current_lua_consumer(self) -> None:
        name = "au_ui_fixture_open"
        event_hash = audio_hash_generator_compute(name)
        with tempfile.TemporaryDirectory() as raw_root:
            lua_root = Path(raw_root)
            rel = Path("Data/LuaScripts/UI/Panels/ActivityStaminaDiscount/ActivityStaminaDiscountCtrl.lua")
            path = lua_root / rel
            path.parent.mkdir(parents=True)
            path.write_text("bgStateData.audioOnOpen\nSetAudioOnOpen(audioOnOpen)\n", encoding="utf-8")
            report = audit.build_report({
                "eventEvidenceSchemaVersion": 21,
                "wwiseEventInventory": [{"eventHash": event_hash, "bank": "default_banks.pck", "mediaIds": [1]}],
                "eventEvidence": [],
                "typedUiTableWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "eventHashHex": f"0x{event_hash:08x}",
                    "name": name,
                    "usages": [{
                        "table": "ActivityStaminaRefundBgStateTable.json",
                        "field": "audioOnOpen",
                        "routeKind": "uiAnimationOpenEvent",
                        "occurrenceCount": 1,
                    }],
                }],
            }, lua_root=lua_root)
        self.assertEqual(report["summary"]["validationErrors"], 0)
        self.assertEqual(report["summary"]["newlyRecoveredEventNames"], 1)
        self.assertEqual(report["summary"]["audioLibraryRelations"]["decodedMedia"], 1)

    def test_missing_lua_consumer_fails_closed(self) -> None:
        name = "au_ui_fixture_open"
        event_hash = audio_hash_generator_compute(name)
        with tempfile.TemporaryDirectory() as raw_root:
            report = audit.build_report({
                "wwiseEventInventory": [{"eventHash": event_hash}],
                "typedUiTableWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "name": name,
                    "usages": [{
                        "table": "ActivityStaminaRefundBgStateTable.json",
                        "field": "audioOnOpen",
                        "routeKind": "uiAnimationOpenEvent",
                    }],
                }],
            }, lua_root=Path(raw_root))
        self.assertGreater(report["summary"]["validationErrors"], 0)

    def test_state_and_game_parameter_events_are_control_not_missing_media(self) -> None:
        name = "au_ui_fixture_control"
        event_hash = audio_hash_generator_compute(name)
        with tempfile.TemporaryDirectory() as raw_root:
            lua_root = Path(raw_root)
            for rel, needles in audit.LUA_CONSUMER_CHECKS["uiVideoAudioEvent"].items():
                path = lua_root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(needles), encoding="utf-8")
            report = audit.build_report({
                "wwiseEventInventory": [{
                    "eventHash": event_hash,
                    "actionEvidence": [{"actionType": 0x1204, "operation": "operation0x1200"}],
                    "mediaIds": [],
                }],
                "typedUiTableWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "name": name,
                    "usages": [{
                        "table": "GachaCharPoolTable.json",
                        "field": "videoAudioKey",
                        "routeKind": "uiVideoAudioEvent",
                    }],
                }],
            }, lua_root=lua_root)
        self.assertEqual(report["summary"]["validationErrors"], 0)
        self.assertEqual(report["summary"]["audioLibraryRelations"]["controlOnly"], 1)
        self.assertEqual(report["aliases"][0]["audioLibraryRelation"], "controlOnly")

    def test_sns_voice_alias_requires_voice_widget_consumers(self) -> None:
        name = "au_ui_event_sns_fixture_voice"
        event_hash = audio_hash_generator_compute(name)
        with tempfile.TemporaryDirectory() as raw_root:
            lua_root = Path(raw_root)
            for rel, needles in audit.SNS_VOICE_LUA_CONSUMER_CHECKS.items():
                path = lua_root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(needles), encoding="utf-8")
            report = audit.build_report({
                "wwiseEventInventory": [{"eventHash": event_hash, "mediaIds": [7]}],
                "snsVoiceWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "name": name,
                    "usages": [{
                        "table": "SNSDialogTable.json",
                        "contentType": 5,
                        "contentTypeName": "Voice",
                        "contentParamIndex": 0,
                    }],
                }],
            }, lua_root=lua_root)
        self.assertEqual(report["summary"]["validationErrors"], 0)
        self.assertEqual(report["summary"]["snsVoiceWwiseEventAliases"], 1)
        self.assertEqual(report["summary"]["audioLibraryRelations"]["decodedMedia"], 1)


if __name__ == "__main__":
    unittest.main()
