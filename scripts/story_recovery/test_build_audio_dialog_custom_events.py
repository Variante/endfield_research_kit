import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parent / "build_audio_dialog_custom_events.py"
SPEC = importlib.util.spec_from_file_location("audio_dialog_custom_events_test", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


class AudioDialogCustomEventAuditTests(unittest.TestCase):
    def test_signature_and_report_preserve_all_lifecycle_phases(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            custom_path = root / "AudioDialogCustomEventTable.json"
            audio_path = root / "AudioDialog.json"
            custom_path.write_text(json.dumps({
                "dlg_c35m1_10": {
                    "dlgId": "dlg_c35m1_10",
                    "postEnterEvents": [1289066702],
                    "postExitEvents": [],
                    "preEnterEvents": [],
                    "preExitEvents": [-850483119],
                    "preloadEvents": [7],
                },
                "dlg_c35m1_11": {
                    "dlgId": "dlg_c35m1_11",
                    "postEnterEvents": [1289066702],
                    "postExitEvents": [],
                    "preEnterEvents": [],
                    "preExitEvents": [-850483119],
                    "preloadEvents": [7],
                },
            }), encoding="utf-8")
            audio_path.write_text(json.dumps({}), encoding="utf-8")

            with patch.object(audit, "CUSTOM_EVENT_TABLE_PATH", custom_path), \
                    patch.object(audit, "AUDIO_DIALOG_TABLE_PATH", audio_path):
                payload = audit.build_report()

            self.assertEqual(
                (
                    (7,), (), (1289066702,), (-850483119,), ()
                ),
                audit.signature_tuple(payload["entries"][0]),
            )
            self.assertEqual(2, payload["summary"]["dialogCount"])
            self.assertEqual(2, payload["summary"]["eventValueCountsByPhase"]["postEnterEvents"])
            self.assertEqual(1, payload["summary"]["distinctEventIdsByPhase"]["preExitEvents"])
            self.assertEqual(
                audit.RUNTIME_CONSUMER["type"],
                payload["runtimeConsumer"]["type"],
            )
            self.assertEqual(
                "0x060099e8",
                payload["runtimeConsumer"]["methods"]["postEnterEvents"]["token"],
            )
            self.assertEqual(1, payload["summary"]["sharedSignatureCount"])


if __name__ == "__main__":
    unittest.main()
