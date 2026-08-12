import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_audio_semantics import audio_hash_generator_compute
from scripts.story_recovery import build_voice_response_audio_event_audit as audit


class VoiceResponseAudioEventAuditTests(unittest.TestCase):
    def test_exact_alias_keeps_trigger_and_tone_evidence_distinct(self) -> None:
        event_name = "chr_test_combat_attack_sv"
        event_hash = audio_hash_generator_compute(event_name)
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "ResponsiveDialog.json").write_text(json.dumps({
                "combat": {"speakers": {"chr_test": {"triggers": {
                    "attack": {"triggerTypeId": 7, "response": [event_hash]}
                }}}}
            }), encoding="utf-8")
            (table_root / "AudioVoTone.json").write_text(json.dumps({
                "123": {"toneList": [event_hash]}
            }), encoding="utf-8")
            audio_index = {
                "eventEvidenceSchemaVersion": 19,
                "wwiseEventInventory": [{
                    "eventHash": event_hash,
                    "bank": "Audio/Windows/default_chinese_banks.pck",
                }],
                "eventEvidence": [],
                "audioDialogWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "eventHashHex": f"0x{event_hash:08x}",
                    "voiceId": event_hash,
                    "name": event_name,
                }],
            }

            report = audit.build_report(audio_index, export_root=export_root)

        self.assertEqual(report["summary"]["audioDialogWwiseEventAliases"], 1)
        self.assertEqual(report["summary"]["newlyRecoveredEventNames"], 1)
        self.assertEqual(report["summary"]["responsiveDialogWwiseEvents"], 1)
        self.assertEqual(report["summary"]["responsiveDialogOccurrences"], 1)
        self.assertEqual(report["summary"]["voiceToneVariantWwiseEvents"], 1)
        self.assertEqual(report["summary"]["voiceToneVariantOccurrences"], 1)
        self.assertEqual(report["summary"]["validationErrors"], 0)
        self.assertEqual(report["aliases"][0]["responsiveDialogOccurrenceCount"], 1)
        self.assertEqual(report["aliases"][0]["toneVariantOccurrenceCount"], 1)

    def test_alias_missing_from_current_event_inventory_fails_closed(self) -> None:
        event_name = "chr_test_missing_sv"
        event_hash = audio_hash_generator_compute(event_name)
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            for name in ("ResponsiveDialog.json", "AudioVoTone.json"):
                (table_root / name).write_text("{}", encoding="utf-8")
            report = audit.build_report({
                "wwiseEventInventory": [],
                "audioDialogWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "eventHashHex": f"0x{event_hash:08x}",
                    "voiceId": event_hash,
                    "name": event_name,
                }],
            }, export_root=export_root)

        self.assertEqual(report["summary"]["validationErrors"], 1)
        self.assertIn("Wwise Event missing", report["validationErrors"][0])


if __name__ == "__main__":
    unittest.main()
