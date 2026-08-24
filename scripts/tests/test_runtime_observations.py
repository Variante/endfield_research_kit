from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audio_semantics.runtime_observations import apply_verified_runtime_observations


class RuntimeObservationProjectionTests(unittest.TestCase):
    def _bundle(self, *, evidence_status: str = "verified") -> dict:
        return {
            "schema": "audioRuntimeTrace.v1",
            "runtimeEvidenceStatus": evidence_status,
            "sessions": [{"language": "CN"}],
            "observations": [{
                "runtimeExecutionObserved": True,
                "sessionId": "capture-1",
                "seq": 3,
                "monotonicMs": 12.5,
                "kind": "audio_request",
                "sourceKind": "audioAdapterPostEvent",
                "hookName": "PostEvent",
                "captureId": "request-1",
                "eventResolution": {
                    "eventId": 123,
                    "eventNameCandidates": ["au_fixture"],
                    "resolution": "staticEventHashJoin",
                },
            }],
        }

    def test_verified_capture_projects_event_and_media(self):
        events = [{"id": "au_fixture", "hash": 123, "media": []}]
        media = [{"id": 7, "eventIds": ["au_fixture"]}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.json"
            path.write_text(json.dumps(self._bundle()), encoding="utf-8")
            result = apply_verified_runtime_observations(events, media, path, expected_language="CN")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["eventCount"], 1)
        self.assertEqual(result["mediaCount"], 1)
        self.assertEqual(events[0]["runtimeObservationStatus"], "verifiedObservedRequest")
        self.assertEqual(media[0]["runtimeObservationStatus"], "verifiedObservedEventRelation")
        self.assertEqual(events[0]["runtimeObservations"][0]["captureId"], "request-1")

    def test_unverified_capture_does_not_project(self):
        events = [{"id": "au_fixture", "hash": 123}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.json"
            path.write_text(json.dumps(self._bundle(evidence_status="degraded")), encoding="utf-8")
            result = apply_verified_runtime_observations(events, [], path, expected_language="CN")
        self.assertEqual(result["reason"], "gameassembly_not_verified")
        self.assertNotIn("runtimeObservationStatus", events[0])


if __name__ == "__main__":
    unittest.main()
