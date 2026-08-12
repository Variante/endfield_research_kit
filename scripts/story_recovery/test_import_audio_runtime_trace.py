import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import import_audio_runtime_trace as importer


def row(session, seq, kind, **values):
    return {
        "schema": importer.EVENT_SCHEMA,
        "sessionId": session,
        "seq": seq,
        "monotonicMs": float(seq),
        "utc": "2026-08-11T00:00:00.000Z",
        "kind": kind,
        **values,
    }


class AudioRuntimeImportTests(unittest.TestCase):
    def test_numeric_event_hash_is_joined_without_claiming_audibility(self):
        session = "fixture-session"
        events = [
            row(session, 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                session,
                1,
                "audio_carrier_enter",
                captureId="carrier-1",
                hookName="PlaySoundAction._DoPostEvent",
                sourceKind="playSoundActionObject",
                arguments={},
            ),
            row(
                session,
                2,
                "audio_request",
                captureId="request-1",
                hookName="AudioAdapter._PostEvent",
                sourceKind="adapterPostEvent",
                arguments={"eventId": 123, "audioObjectId": "42"},
                activeContexts=[{"captureId": "carrier-1"}],
            ),
            row(
                session,
                3,
                "audio_request_result",
                captureId="request-1",
                hookName="AudioAdapter._PostEvent",
                sourceKind="adapterPostEvent",
                returnValue=77,
            ),
            row(
                session,
                4,
                "audio_carrier_leave",
                captureId="carrier-1",
                hookName="PlaySoundAction._DoPostEvent",
                sourceKind="playSoundActionObject",
            ),
            row(session, 5, "session_end"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trace = root / "capture.jsonl"
            index = root / "index.json"
            trace.write_text("\n".join(json.dumps(value) for value in events) + "\n", encoding="utf-8")
            index.write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "eventHash": 123,
                                "eventId": "au_fixture_event",
                                "rel": "wwise/fixture.flac",
                                "eventCategory": "au_fixture",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            normalized, sources = importer.read_events([trace])
            bundle = importer.build_bundle(normalized, sources, index)

        self.assertEqual(bundle["observationCount"], 4)
        self.assertEqual(bundle["resolvedEventObservationCount"], 2)
        request = next(item for item in bundle["observations"] if item["kind"] == "audio_request")
        self.assertEqual(request["eventResolution"]["eventNameCandidates"], ["au_fixture_event"])
        result = next(item for item in bundle["observations"] if item["kind"] == "audio_request_result")
        self.assertEqual(result["requestArguments"]["eventId"], 123)
        self.assertEqual(bundle["evidenceBoundary"]["audibility"].startswith("no observation"), True)
        self.assertEqual(bundle["runtimeEvidenceStatus"], "notRecorded")

    def test_module_mismatch_degrades_runtime_evidence_status(self):
        events = [
            row(
                "s",
                0,
                "session_start",
                gameBuild="fixture",
                captureTool="fixture",
                expectedModulePath="C:\\verified\\GameAssembly.dll",
                expectedModuleSize=10,
            ),
            row(
                "s",
                1,
                "session_end",
                attachedModulePath="C:\\other\\GameAssembly.dll",
                attachedModuleSize=11,
                modulePathMatch=False,
                moduleSizeMatch=False,
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        self.assertEqual(bundle["runtimeEvidenceStatus"], "degraded")
        self.assertEqual(bundle["moduleVerification"][0]["modulePathMatch"], False)

    def test_sequence_must_increase(self):
        events = [
            row("s", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row("s", 0, "session_end"),
        ]
        with self.assertRaisesRegex(importer.AudioTraceValidationError, "strictly increasing"):
            importer.build_bundle(events, ["fixture"], Path("missing-index.json"))

    def test_string_event_key_is_kept_as_observed_key(self):
        events = [
            row("s", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "s",
                1,
                "audio_request",
                captureId="r",
                hookName="GameAction.PlayAudio",
                sourceKind="levelScriptAudioAction",
                arguments={"eventKey": "au_fixture"},
            ),
            row("s", 2, "session_end"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            trigger_contexts = Path(temporary) / "trigger_contexts.json"
            trigger_contexts.write_text(
                json.dumps(
                    {
                        "schemaVersion": 4,
                        "contexts": [
                            {
                                "triggerId": "radio:fixture",
                                "semanticKind": "radio",
                                "triggerRole": "play",
                                "situation": {"radioId": "radio_fixture"},
                                "meaning": {"audio": "au_fixture"},
                                "action": {"runtimeActivationStatus": "unobserved"},
                                "mediaRefs": [{"id": "au_fixture"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            bundle = importer.build_bundle(
                events,
                ["fixture"],
                Path("missing-index.json"),
                trigger_contexts,
            )
        request = bundle["observations"][0]
        self.assertEqual(request["eventResolution"], {"eventKey": "au_fixture", "resolution": "observedStringKey"})
        self.assertEqual(request["staticTriggerContextCandidates"]["bySemanticKind"], {"radio": 1})
        self.assertEqual(bundle["triggerContexts"]["matchedObservationCount"], 1)
        self.assertEqual(bundle["joinStatus"], "degraded")


if __name__ == "__main__":
    unittest.main()
