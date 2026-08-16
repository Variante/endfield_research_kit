import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import runtime_trace_audio_import as importer


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

    def test_codec_stream_callback_summary_preserves_indirect_boundary(self):
        events = [
            row("codec-session", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "codec-session",
                1,
                "audio_native_call",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="codec-1",
                hookName="AkSoundEngine.CodecStreamRead",
                sourceKind="wwiseCodecStreamRead",
                rva="0x1c9fa0",
                decodedArguments={"requestedBytes": 4096},
                memory={
                    "streamCallback": "0x180abc000",
                    "streamCallbackContext": "0x12340000",
                    "bufferedBytes": "8192",
                    "streamBuffer": "0x12340100",
                    "streamCapacity": 65536,
                    "streamCursor": 128,
                },
            ),
            row(
                "codec-session",
                2,
                "audio_native_result",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="codec-1",
                hookName="AkSoundEngine.CodecStreamRead",
                sourceKind="wwiseCodecStreamRead",
                rva="0x1c9fa0",
                nativeCallDecodedArguments={"requestedBytes": 4096},
                nativeCallMemory={
                    "streamCallback": "0x180abc000",
                    "streamCallbackContext": "0x12340000",
                    "streamBuffer": "0x12340100",
                },
                memoryAfter={"streamCallback": "0x180abc000"},
            ),
            row(
                "codec-session",
                3,
                "audio_native_call",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="copy-1",
                hookName="AkSoundEngine.CodecMemorySourceCopy",
                sourceKind="wwiseCodecMemorySourceCopy",
                rva="0x1c44d0",
                decodedArguments={"requestedBytes": 1024},
                memory={
                    "sourceBuffer": "0x12340200",
                    "sourceAvailable": 4096,
                    "sourceOffset": 256,
                    "refillObject": "0x12340300",
                },
            ),
            row(
                "codec-session",
                4,
                "audio_native_result",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="copy-1",
                hookName="AkSoundEngine.CodecMemorySourceCopy",
                sourceKind="wwiseCodecMemorySourceCopy",
                rva="0x1c44d0",
                nativeCallDecodedArguments={"requestedBytes": 1024},
                nativeCallMemory={"sourceBuffer": "0x12340200", "sourceAvailable": 4096, "sourceOffset": 256, "refillObject": "0x12340300"},
                returnValue=1024,
            ),
            row("codec-session", 5, "session_end"),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        summary = bundle["nativePairing"]["codecStreamCallbacks"][0]
        self.assertEqual(summary["callCount"], 1)
        self.assertEqual(summary["resultCount"], 1)
        self.assertEqual(summary["callbackPointers"], ["0x180abc000"])
        self.assertEqual(summary["contextPointers"], ["0x12340000"])
        self.assertEqual(summary["bufferPointers"], ["0x12340100"])
        self.assertEqual(summary["streamCapacities"], [65536])
        self.assertEqual(summary["streamCursors"], [128])
        self.assertEqual(summary["requestedBytes"], [4096])
        self.assertIn("not proof", summary["evidenceBoundary"])
        memory_copy = bundle["nativePairing"]["codecMemorySourceCopies"][0]
        self.assertEqual(memory_copy["callCount"], 1)
        self.assertEqual(memory_copy["resultCount"], 1)
        self.assertEqual(memory_copy["sourceBufferPointers"], ["0x12340200"])
        self.assertEqual(memory_copy["refillObjectPointers"], ["0x12340300"])
        self.assertEqual(memory_copy["sourceAvailable"], [4096])
        self.assertEqual(memory_copy["sourceOffsets"], [256])

    def test_native_observations_are_preserved_and_need_verified_native_module(self):
        events = [
            row(
                "native-session",
                0,
                "session_start",
                gameBuild="fixture",
                captureTool="fixture",
                expectedNativeModulePath="C:\\verified\\AkSoundEngine.dll",
                expectedNativeModuleSize=64,
                expectedNativeModuleSha256="a" * 64,
            ),
            row(
                "native-session",
                1,
                "audio_native_call",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="native-1",
                hookName="AkSoundEngine.ExternalSourceManagerLookup",
                sourceKind="externalSourceLookup",
                rva="0xe2820",
                arguments={"arg1": "0x7b"},
                decodedArguments={"externalKey": 123},
                memory={"descriptorKey": 123},
            ),
            row(
                "native-session",
                2,
                "audio_native_result",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="native-1",
                hookName="AkSoundEngine.ExternalSourceManagerLookup",
                sourceKind="externalSourceLookup",
                rva="0xe2820",
                decodedArgumentsAfter={},
                memoryAfter={"descriptorKey": 123},
            ),
            row(
                "native-session",
                3,
                "audio_native_call",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="native-2",
                hookName="AkSoundEngine.SourceMediaLookup",
                sourceKind="wwiseSourceMediaLookup",
                rva="0x10df60",
                memory={"sourceKey": 123},
            ),
            row(
                "native-session",
                4,
                "session_end",
                attachedNativeModulePath="C:\\verified\\AkSoundEngine.dll",
                attachedNativeModuleSize=64,
                nativeModulePathMatch=True,
                nativeModuleSizeMatch=True,
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        self.assertEqual(bundle["nativeRuntimeEvidenceStatus"], "verified")
        self.assertEqual(bundle["sessions"][0]["expectedNativeModuleSha256"], "a" * 64)
        self.assertEqual(bundle["countsByKind"]["audio_native_call"], 2)
        self.assertEqual(bundle["nativePairing"]["pairedCallResultCount"], 1)
        self.assertEqual(bundle["nativePairing"]["keyCorrelations"][0]["sharedKeys"], [123])
        observation = bundle["observations"][0]
        self.assertTrue(observation["native"])
        self.assertEqual(observation["decodedArguments"]["externalKey"], 123)
        self.assertEqual(observation["memory"]["descriptorKey"], 123)
        result = bundle["observations"][1]
        self.assertEqual(result["nativeCallMemory"]["descriptorKey"], 123)

    def test_native_key_lifecycle_keeps_join_and_decoder_boundaries_separate(self):
        events = [
            row("lifecycle", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "lifecycle", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="registration",
                hookName="AkSoundEngine.ExternalSourceManagerConstructor",
                sourceKind="externalSourceRegistration", rva="0xe1320",
                decodedArguments={"sourceKey": 123},
            ),
            row(
                "lifecycle", 2, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="join",
                hookName="AkSoundEngine.ExternalSourceManagerJoin",
                sourceKind="externalSourceManagerJoin", rva="0xe2cd0",
                decodedArguments={"sourceKey": 123},
                memory={"sourceStateKey": 123, "sourceStateKey268": 123},
            ),
            row(
                "lifecycle", 3, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="registry",
                hookName="AkSoundEngine.SourceKeyDecoderRegistry",
                sourceKind="sourceKeyDecoderRegistry", rva="0x13f440",
                decodedArguments={"sourceKey": 123, "decoder": "0x180abc000"},
            ),
            row(
                "lifecycle", 4, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="source-media",
                hookName="AkSoundEngine.SourceMediaLookup",
                sourceKind="wwiseSourceMediaLookup", rva="0x10df60",
                memory={"sourceKey": 123},
            ),
            row(
                "lifecycle", 5, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="descriptor",
                hookName="AkSoundEngine.ExternalDescriptorCopy",
                sourceKind="externalDescriptorCopy", rva="0xc08d0",
                memory={"externalFile": "voice/test.wem"},
            ),
            row(
                "lifecycle", 6, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="open",
                hookName="AkSoundEngine.DefaultIoOpenDispatch",
                sourceKind="wwiseDefaultIoOpenDispatch", rva="0x5030",
                decodedArguments={"filePath": "voice/test.wem"},
            ),
            row(
                "lifecycle", 7, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="provider",
                hookName="AkSoundEngine.SourceProviderPreparation",
                sourceKind="wwiseSourceProviderPreparation", rva="0x1af7a0",
                memory={"sourceInfoPath": "voice/test.wem"},
            ),
            row(
                "lifecycle", 8, "session_end",
                attachedNativeModulePath="C:\\verified\\AkSoundEngine.dll",
                attachedNativeModuleSize=64,
                nativeModulePathMatch=True, nativeModuleSizeMatch=True,
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        lifecycle = bundle["nativePairing"]["keyLifecycle"][0]
        self.assertEqual(lifecycle["registrationKeys"], [123])
        self.assertEqual(lifecycle["managerJoinRequestedKeys"], [123])
        self.assertEqual(lifecycle["sameJoinArgumentAndStateKeys"], [123])
        self.assertEqual(lifecycle["sameJoinArgumentAndStateKeys268"], [123])
        self.assertEqual(lifecycle["sharedManagerJoinDecoderKeys"], [123])
        self.assertEqual(lifecycle["sharedStateMediaLookupKeys"], [123])
        self.assertEqual(lifecycle["decoderPointers"], ["0x180abc000"])
        self.assertEqual(lifecycle["externalDescriptorFiles"], ["voice/test.wem"])
        self.assertEqual(lifecycle["fileOpenPaths"], ["voice/test.wem"])
        self.assertEqual(lifecycle["sourceProviderPaths"], ["voice/test.wem"])
        self.assertEqual(lifecycle["sharedProviderOpenPaths"], ["voice/test.wem"])
        self.assertEqual(lifecycle["sharedDescriptorOpenPaths"], ["voice/test.wem"])
        self.assertIn("do not prove", lifecycle["evidenceBoundary"])
        self.assertIn("nativeKeyLifecycle", bundle["evidenceBoundary"])

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
