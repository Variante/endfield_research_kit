import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.build_audio_semantics import audio_hash_generator_compute
from scripts.story_recovery import build_skill_id_audio_event_audit as audit


class SkillIdAudioEventAuditTests(unittest.TestCase):
    def fixture(self, root: Path, *, include_hash: bool = False) -> tuple[dict, Path]:
        export_root = root / "export_full"
        name = "eny_fixture_skill_audio_identity"
        event_hash = audio_hash_generator_compute(name)
        sources = []
        skill_sources = []
        for source_root in ("StreamingAssets", "Persistent"):
            table_root = export_root / "structured" / source_root / "Table"
            table_root.mkdir(parents=True)
            table_path = table_root / "NumIdStrTable.json"
            table_path.write_text(json.dumps({"skill_id": {"dic": {"7": name}}}), encoding="utf-8")
            sources.append(table_path.relative_to(export_root).as_posix())
            skill_root = export_root / "structured" / source_root / "Data/Json/SkillData"
            skill_root.mkdir(parents=True)
            skill_path = skill_root / f"{name}.json"
            skill_path.write_bytes(b"fixture" + (struct.pack("<I", event_hash) if include_hash else b""))
            skill_sources.append(skill_path.relative_to(export_root).as_posix())
            (export_root / "structured" / source_root / "Data/Json/BuffData").mkdir(parents=True)
        index = {
            "eventEvidenceSchemaVersion": 23,
            "generated": "fixture",
            "skillIdDictionaryWwiseEventAliases": [{
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "name": name,
                "dictionaryKind": "skill_id",
                "numericSkillIds": ["7"],
                "tableSources": sources,
                "skillDataSources": skill_sources,
                "evidence": "skillIdDictionaryNameAndSkillDataFileHashEqualsCurrentWwiseEventId",
                "playbackPlacementStatus": "identityOnlyNoAudioConsumer",
            }],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bank": "default_banks.pck",
                "mediaIds": [11],
                "actionEvidence": [{"operation": "play"}],
            }],
        }
        return index, export_root

    def test_valid_identity_only_alias(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            index, export_root = self.fixture(Path(raw_root))
            report = audit.build_report(index, export_root)
        self.assertEqual(report["summary"]["validationErrors"], 0)
        self.assertEqual(report["summary"]["aliases"], 1)
        self.assertEqual(report["summary"]["serializedUint32EventHashHits"], 0)
        self.assertEqual(report["aliases"][0]["audioLibraryRelation"], "decodedMedia")

    def test_serialized_hash_invalidates_identity_only_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            index, export_root = self.fixture(Path(raw_root), include_hash=True)
            report = audit.build_report(index, export_root)
        self.assertGreater(report["summary"]["validationErrors"], 0)
        self.assertGreater(report["summary"]["serializedUint32EventHashHits"], 0)


if __name__ == "__main__":
    unittest.main()
