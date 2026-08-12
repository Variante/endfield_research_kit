import unittest

from scripts.build_audio_semantics import audio_hash_generator_compute
from scripts.story_recovery import build_voice_table_audio_event_audit as audit


class VoiceTableAudioEventAuditTests(unittest.TestCase):
    def test_exact_typed_alias_is_validated_without_claiming_live_playback(self) -> None:
        name = "vo_fixture_narrating"
        event_hash = audio_hash_generator_compute(name)
        report = audit.build_report({
            "eventEvidenceSchemaVersion": 20,
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bank": "Audio/Windows/default_banks.pck",
                "mediaIds": [],
                "nonMediaSourceEvidence": [{"sourceKind": "externalSource"}],
            }],
            "eventEvidence": [],
            "voiceTableWwiseEventAliases": [{
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "name": name,
                "usages": [{
                    "table": "AudioDialogChannel.json",
                    "field": "narratingWwiseEvent",
                    "routeKind": "narratingChannelEvent",
                    "occurrenceCount": 2,
                }],
            }],
        })

        self.assertEqual(report["summary"]["validationErrors"], 0)
        self.assertEqual(report["summary"]["newlyRecoveredEventNames"], 1)
        self.assertEqual(report["summary"]["fieldOccurrences"]["AudioDialogChannel.json.narratingWwiseEvent"], 2)
        self.assertEqual(report["summary"]["audioLibraryRelations"]["externalSource"], 1)

    def test_unapproved_field_and_missing_inventory_are_errors(self) -> None:
        name = "vo_fixture_bad"
        event_hash = audio_hash_generator_compute(name)
        report = audit.build_report({
            "wwiseEventInventory": [],
            "voiceTableWwiseEventAliases": [{
                "eventHash": event_hash,
                "name": name,
                "usages": [{
                    "table": "Other.json",
                    "field": "event",
                    "routeKind": "voiceDefaultEvent",
                }],
            }],
        })
        self.assertEqual(report["summary"]["validationErrors"], 2)


if __name__ == "__main__":
    unittest.main()
