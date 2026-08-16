from __future__ import annotations

import unittest
import json
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import serve


class AudioNotesOverrideTests(unittest.TestCase):
    def test_audio_notes_endpoint_is_writable(self) -> None:
        target, validator = serve.Handler.WRITABLE_OVERRIDES["/overrides/audio_notes.json"]
        self.assertEqual(target, serve.AUDIO_NOTES_OVERRIDE_PATH)
        self.assertEqual(validator, "validate_audio_notes_payload")

    def test_valid_audio_notes_payload(self) -> None:
        payload = {
            "_schema": "audioNotes.v1",
            "notes": {
                "CN:events:AU_TEST": "First line\nMore detail",
                "CN:media:123": "Playable variant",
            },
        }
        self.assertEqual(serve.validate_audio_notes_payload(payload), "")

    def test_audio_notes_payload_rejects_invalid_entries(self) -> None:
        cases = [
            ({}, "must contain a notes object"),
            ({"notes": {"": "note"}}, "keys must be non-empty"),
            ({"notes": {"CN:events:AU_TEST": ""}}, "must be a non-empty string"),
            ({"notes": {"CN:events:AU_TEST": "x" * 10001}}, "exceeds 10000 characters"),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertIn(expected, serve.validate_audio_notes_payload(payload))

    def test_put_persists_audio_notes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            test_webui_root = Path(temp_dir) / "webui"
            target = test_webui_root / "overrides" / "audio_notes.json"
            original = serve.Handler.WRITABLE_OVERRIDES["/overrides/audio_notes.json"]
            serve.Handler.WRITABLE_OVERRIDES["/overrides/audio_notes.json"] = (
                target,
                "validate_audio_notes_payload",
            )
            original_root = serve.WEBUI_ROOT
            serve.WEBUI_ROOT = test_webui_root
            server = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                payload = {
                    "_schema": "audioNotes.v1",
                    "notes": {"CN:events:AU_TEST": "First line\nMore detail"},
                }
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/overrides/audio_notes.json",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="PUT",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                serve.WEBUI_ROOT = original_root
                serve.Handler.WRITABLE_OVERRIDES["/overrides/audio_notes.json"] = original


if __name__ == "__main__":
    unittest.main()
