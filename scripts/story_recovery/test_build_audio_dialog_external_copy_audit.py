import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_audio_dialog_external_copy_audit.py")
SPEC = importlib.util.spec_from_file_location("audio_dialog_external_copy_audit", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)
build_audio = audit.load_build_audio()


class AudioDialogExternalCopyAuditTests(unittest.TestCase):
    def test_exact_hash_and_bytes_are_audited_without_deleting_numeric_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table = export_root / "structured/StreamingAssets/Table/AudioDialog.json"
            table.parent.mkdir(parents=True)
            dialog_path = "v1d4/Narrating/Test/au_fixture.wem"
            table.write_text(json.dumps({"1": {"path": dialog_path, "speakerChannel": "test"}}), encoding="utf-8")
            external_id = build_audio.audio_dialog_external_media_id(dialog_path, "chinese")
            numeric = export_root / f"structured/Audio/CN/wwise/unknown/{external_id}.flac"
            canonical_rel = build_audio.audio_rel_for_dialog_path(dialog_path, ".flac")
            canonical = export_root / "structured/Audio/CN" / Path(*Path(canonical_rel).parts)
            numeric.parent.mkdir(parents=True)
            canonical.parent.mkdir(parents=True)
            numeric.write_bytes(b"same")
            canonical.write_bytes(b"same")

            payload = audit.build_audit(export_root)

            self.assertEqual(payload["summary"]["externalNumericPathCount"], 1)
            self.assertEqual(payload["summary"]["byteIdenticalCurrentAuthoredCopyCount"], 1)
            self.assertEqual(payload["summary"]["validationErrorCount"], 0)
            self.assertTrue(numeric.is_file())

    def test_bounded_recovered_numeric_file_remains_a_trigger_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            numeric = export_root / "structured/Audio/CN/wwise/unknown/955778167792087661.flac"
            numeric.parent.mkdir(parents=True)
            numeric.write_bytes(b"unmatched")

            payload = audit.build_audit(export_root)

            self.assertEqual(payload["summary"]["boundedRecoveredAuthoredPathHashCount"], 1)
            self.assertEqual(payload["summary"]["absentFromCurrentAudioDialogCount"], 0)
            self.assertEqual(payload["summary"]["validationErrorCount"], 0)
            self.assertEqual(payload["records"][0]["identityStatus"], "boundedRecoveredAuthoredPathHash")
            self.assertEqual(payload["records"][0]["recoveredAudioId"], "au_voice_c35m3_3_001")


if __name__ == "__main__":
    unittest.main()
