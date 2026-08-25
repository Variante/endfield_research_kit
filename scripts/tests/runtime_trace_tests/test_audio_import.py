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


def native_end(session, seq, **values):
    values.setdefault("nativeModulePathMatch", True)
    values.setdefault("nativeModuleSizeMatch", True)
    values.setdefault("nativeModuleSha256Match", True)
    return row(session, seq, "session_end", **values)


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
                stackArguments={"codec": 20},
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
        self.assertEqual(request["stackArguments"]["codec"], 20)
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
            native_end("codec-session", 5),
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
                nativeModuleSha256Match=True,
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

    def test_native_pairing_is_withheld_without_session_end_gate(self):
        events = [
            row("no-end", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "no-end", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="native-1",
                hookName="AkSoundEngine.ExternalSourceManagerLookup",
                sourceKind="externalSourceLookup", rva="0xe2820",
                decodedArguments={"externalKey": 123},
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        self.assertEqual(bundle["nativeRuntimeEvidenceStatus"], "notRecorded")
        self.assertFalse(bundle["nativePairing"]["available"])
        self.assertEqual(bundle["nativePairing"]["keyLifecycle"], [])

    def test_native_pairing_is_withheld_on_hash_gate_mismatch(self):
        events = [
            row("mismatch", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "mismatch", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="native-1",
                hookName="AkSoundEngine.ExternalSourceManagerLookup",
                sourceKind="externalSourceLookup", rva="0xe2820",
                decodedArguments={"externalKey": 123},
            ),
            row(
                "mismatch", 2, "session_end",
                nativeModulePathMatch=False, nativeModuleSizeMatch=False,
                nativeModuleSha256Match=False,
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        self.assertEqual(bundle["nativeRuntimeEvidenceStatus"], "degraded")
        self.assertFalse(bundle["nativePairing"]["available"])
        self.assertEqual(bundle["nativePairing"]["nativeCallRelations"], [])

    def test_native_pairing_is_withheld_when_bounded_queue_dropped_events(self):
        events = [
            row("dropped", 0, "session_start", gameBuild="fixture", captureTool="native-fixture"),
            row(
                "dropped", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="native-1",
                hookName="AkSoundEngine.SourceMediaLookup",
                sourceKind="wwiseSourceMediaLookup", rva="0x10df60",
                memory={"sourceKey": 123},
            ),
            row(
                "dropped", 2, "session_end",
                nativeModulePathMatch=True, nativeModuleSizeMatch=True,
                nativeModuleSha256Match=True, captureComplete=False,
                droppedEventCount=1,
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        self.assertEqual(bundle["nativeRuntimeEvidenceStatus"], "verified")
        self.assertFalse(bundle["nativePairing"]["available"])
        self.assertEqual(bundle["nativePairing"]["status"], "incompleteCapture")
        self.assertEqual(bundle["nativePairing"]["incompleteCaptureSessions"], ["dropped"])

    def test_native_call_relations_require_exact_parent_capture_id(self):
        events = [
            row("nested", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "nested", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="outer",
                hookName="AkSoundEngine.PostEventExternal",
                sourceKind="externalDescriptorPostEvent", rva="0xc38b0",
            ),
            row(
                "nested", 2, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="inner",
                nativeParentCaptureId="outer",
                hookName="AkSoundEngine.CopyExternalSourceDescriptor",
                sourceKind="externalDescriptorCopy", rva="0xc08d0",
            ),
            row(
                "nested", 3, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="orphan",
                nativeParentCaptureId="missing",
                hookName="AkSoundEngine.OpenExternalSource",
                sourceKind="wwiseDefaultIoOpenDispatch", rva="0x5040",
            ),
            native_end("nested", 4),
        ]
        normalized = [importer.normalize_event(event, "nested.jsonl") for event in events]
        self.assertEqual(normalized[2]["nativeParentCaptureId"], "outer")
        bundle = importer.build_bundle(normalized, ["fixture"], Path("missing-index.json"))
        self.assertEqual(
            bundle["nativePairing"]["nativeCallRelations"],
            [{
                "sessionId": "nested",
                "parentNativeCaptureId": "outer",
                "childNativeCaptureId": "inner",
                "parentSourceKind": "externalDescriptorPostEvent",
                "childSourceKind": "externalDescriptorCopy",
                "parentHookName": "AkSoundEngine.PostEventExternal",
                "childHookName": "AkSoundEngine.CopyExternalSourceDescriptor",
                "relation": "synchronousNativeHookNesting",
            }],
        )

    def test_native_key_lifecycle_keeps_join_and_decoder_boundaries_separate(self):
        events = [
            row("lifecycle", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "lifecycle", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="registration",
                hookName="AkSoundEngine.ExternalSourceManagerConstructor",
                sourceKind="externalSourceRegistration", rva="0xe1320",
                decodedArguments={"sourceKey": 123},
                derivedArgumentsAfter={
                    "managerEntryPointer": "0x180abc200",
                    "managerEntryFound": True,
                    "managerEntrySerial": 123,
                    "managerEntryDescriptorInfo": "0x180abc100",
                },
                memory={"descriptorAllocationBase": "0x180abc100"},
            ),
            row(
                "lifecycle", 1.1, "audio_native_result", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="registration",
                hookName="AkSoundEngine.ExternalSourceManagerConstructor",
                sourceKind="externalSourceRegistration", rva="0xe1320",
                returnValue=1,
                derivedArgumentsAfter={
                    "managerEntryPointer": "0x180abc200",
                    "managerEntryFound": True,
                    "managerEntrySerial": 123,
                    "managerEntryDescriptorInfo": "0x180abc100",
                },
            ),
            row(
                "lifecycle", 2, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="join",
                hookName="AkSoundEngine.ExternalSourceManagerJoin",
                sourceKind="externalSourceManagerJoin", rva="0xe2cd0",
                decodedArguments={"sourceKey": 123},
                derivedArguments={
                    "managerEntryPointer": "0x180abc200",
                    "managerEntryFound": True,
                    "managerEntrySerial": 123,
                },
                memory={"sourceStateKey": 123, "sourceStateKey268": 123},
            ),
            row(
                "lifecycle", 3, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="source-state",
                hookName="AkSoundEngine.ExternalSourceStateCallback",
                sourceKind="externalSourceStateCallback", rva="0x143990",
                memory={
                    "sourceContext": "0x180abc400",
                    "sourceKeyFromContext": 123,
                },
            ),
            row(
                "lifecycle", 4, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="sibling-lookup",
                hookName="AkSoundEngine.ExternalSourceManagerSiblingLookup",
                sourceKind="externalSourceSiblingLookup", rva="0xe28d0",
                decodedArguments={"sourceKey": 123, "callbackContext": "0x180abc400"},
                derivedArguments={
                    "managerEntryPointer": "0x180abc200",
                    "managerEntryFound": True,
                    "managerEntrySerial": 123,
                },
            ),
            row(
                "lifecycle", 5, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="registry",
                hookName="AkSoundEngine.SourceKeyDecoderRegistry",
                sourceKind="sourceKeyDecoderRegistry", rva="0x13f440",
                decodedArguments={"sourceKey": 123, "decoder": "0x180abc000"},
            ),
            row(
                "lifecycle", 5.5, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="decoder-call",
                hookName="AkSoundEngine.CodecDecoderDecode",
                sourceKind="wwiseCodecDecoderDecode", rva="0x1c7ec0",
                nativeReturnAddress="0x1801c4780",
                decodedArguments={"decoder": "0x180abc000"},
                memory={
                    "decoderOwner": "0x180abc900",
                    "decoderOwnerKey": 123,
                    "decoderProviderInterface": "0x180abc300",
                    "decoderBuffer": "0x180abd000",
                    "decoderAvailable": 4096,
                    "decoderPosition": 512,
                    "decodedFloatBuffer": "0x180abe000",
                    "decodedFrameCount": 480,
                },
                memoryAfter={
                    "decodedFloatBuffer": "0x180abe000",
                    "decodedFrameCount": 480,
                },
            ),
            row(
                "lifecycle", 6, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="source-media",
                hookName="AkSoundEngine.SourceMediaLookup",
                sourceKind="wwiseSourceMediaLookup", rva="0x10df60",
                memory={"sourceKey": 123},
            ),
            row(
                "lifecycle", 6.5, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="source-state-init",
                hookName="AkSoundEngine.SourceStateInitializer",
                sourceKind="sourceStateInitializer", rva="0xd1f90",
                nativeReturnAddress="0x180036622",
                decodedArguments={
                    "sourceState": "0x180abc900",
                    "sourceConfig": "0x180abc800",
                    "sourceInfo": "0x180abc600",
                },
                memory={
                    "sourceStateKey268": 123,
                    "sourceStateSourceInfo": "0x180abc600",
                    "sourceConfigKey34": 123,
                    "sourceInfoKey": 123,
                    "sourceInfoPath": "voice/test.wem",
                },
            ),
            row(
                "lifecycle", 7, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="descriptor",
                hookName="AkSoundEngine.ExternalDescriptorCopy",
                sourceKind="externalDescriptorCopy", rva="0xc08d0",
                memory={
                    "externalFile": "voice/test.wem",
                    "copiedAllocationBase": "0x180abc100",
                },
            ),
            row(
                "lifecycle", 8, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="open",
                hookName="AkSoundEngine.DefaultIoOpenDispatch",
                sourceKind="wwiseDefaultIoOpenDispatch", rva="0x5030",
                decodedArguments={"filePath": "voice/test.wem"},
                memoryAfter={
                    "openProviderContext": "0x180abc350",
                    "openFileSize": "65536",
                    "openHandle": "0x123",
                },
            ),
            row(
                "lifecycle", 9, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="provider",
                hookName="AkSoundEngine.SourceProviderPreparation",
                sourceKind="wwiseSourceProviderPreparation", rva="0x1af7a0",
                memory={
                    "sourceOwner": "0x180abc900",
                    "sourceInfoPointer": "0x180abc600",
                    "sourceInfoPath": "voice/test.wem",
                    "sourceInfoKey": 123,
                    "sourceOwnerSelectedDescriptor": "0x180abc710",
                },
                memoryAfter={"decoderProvider": "0x180abc300"},
            ),
            row(
                "lifecycle", 10, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="provider-dispatch",
                hookName="AkSoundEngine.DeviceQueueDispatch",
                sourceKind="wwiseDeviceQueueDispatch", rva="0x24200",
                memory={"provider0": "0x180abc300", "provider1": "0x0"},
            ),
            row(
                "lifecycle", 11, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="async-read",
                hookName="AkSoundEngine.AsyncBatchRead",
                sourceKind="wwiseAsyncBatchRead", rva="0x24270",
                memory={
                    "descriptorProviderObject": "0x180abc300",
                    "descriptorProviderHandle": "0x123",
                },
            ),
            row(
                "lifecycle", 12, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="source-info",
                hookName="AkSoundEngine.SourceInfoSelectionConsumer",
                sourceKind="sourceInfoSelectionConsumer", rva="0xd2ed0",
                memory={"sourceInfoKey": 123, "sourceInfoPointer": "0x180abc600"},
                memoryAfter={"sourceObjectSelectedDescriptor": "0x180abc710"},
            ),
            row(
                "lifecycle", 13, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="source-info-selector",
                hookName="AkSoundEngine.SourceInfoSelector",
                sourceKind="sourceInfoSelector", rva="0xf5030",
                decodedArguments={"sourceInfoKey": 123, "sourceInfoMode": 7},
                memory={
                    "selectedEntry": "0x180abc700",
                    "selectedEntryKey": 123,
                    "selectedDescriptor": "0x180abc710",
                    "selectedDescriptorAux": 456,
                },
            ),
            native_end(
                "lifecycle", 14,
                attachedNativeModulePath="C:\\verified\\AkSoundEngine.dll",
                attachedNativeModuleSize=64,
                nativeModulePathMatch=True, nativeModuleSizeMatch=True,
            ),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        lifecycle = bundle["nativePairing"]["keyLifecycle"][0]
        self.assertEqual(lifecycle["registrationKeys"], [123])
        self.assertEqual(lifecycle["registrationManagerEntryPointers"], ["0x180abc200"])
        self.assertEqual(lifecycle["managerJoinEntryPointers"], ["0x180abc200"])
        self.assertEqual(lifecycle["sharedRegistrationJoinEntryPointers"], ["0x180abc200"])
        self.assertEqual(lifecycle["sharedRegistrationLookupEntryPointers"], ["0x180abc200"])
        self.assertEqual(lifecycle["managerEntryDescriptorInfoPointers"], ["0x180abc100"])
        self.assertEqual(lifecycle["managerJoinRequestedKeys"], [123])
        self.assertEqual(lifecycle["sameJoinArgumentAndStateKeys"], [123])
        self.assertEqual(lifecycle["sameJoinArgumentAndStateKeys268"], [123])
        self.assertEqual(lifecycle["registrationManagerJoinRequestedKeys"], [123])
        self.assertEqual(lifecycle["registrationManagerJoinStateKeys"], [123])
        self.assertEqual(lifecycle["registrationManagerJoinStateKeys268"], [123])
        self.assertEqual(lifecycle["registrationExternalLookupKeys"], [])
        self.assertEqual(lifecycle["registrationSourceMediaLookupKeys"], [123])
        self.assertEqual(lifecycle["sourceStateCallbackKeys"], [123])
        self.assertEqual(lifecycle["sourceStateCallbackContexts"], ["0x180abc400"])
        self.assertEqual(lifecycle["sourceInfoSelectionKeys"], [123])
        self.assertEqual(lifecycle["sourceInfoSelectorKeys"], [123])
        self.assertEqual(lifecycle["sourceInfoSelectedEntryKeys"], [123])
        self.assertEqual(
            lifecycle["sourceInfoSelectedDescriptorPointers"], ["0x180abc710"]
        )
        self.assertEqual(lifecycle["sourceInfoSelectedDescriptorAux"], [456])
        self.assertEqual(lifecycle["sharedSourceInfoSelectorEntryKeys"], [123])
        self.assertEqual(
            lifecycle["sharedSourceInfoSelectorObjectDescriptorPointers"],
            ["0x180abc710"],
        )
        self.assertEqual(
            lifecycle["sharedSourceInfoSelectorProviderDescriptorPointers"],
            ["0x180abc710"],
        )
        self.assertEqual(
            lifecycle["sharedSourceObjectProviderDescriptorPointers"],
            ["0x180abc710"],
        )
        self.assertEqual(lifecycle["sourceInfoProviderKeys"], [123])
        self.assertEqual(lifecycle["sourceStateInitializerKeys"], [123])
        self.assertEqual(lifecycle["sourceStateInitializerConfigKeys"], [123])
        self.assertEqual(lifecycle["sourceStateInitializerInfoKeys"], [123])
        self.assertEqual(lifecycle["sourceStateInitializerReturnAddresses"], ["0x180036622"])
        self.assertEqual(lifecycle["registrationStatuses"], [1])
        self.assertEqual(lifecycle["sourceStateInitializerPointers"], ["0x180abc900"])
        self.assertEqual(
            lifecycle["sourceStateInitializerSourceInfoPointers"], ["0x180abc600"]
        )
        self.assertEqual(
            lifecycle["sourceStateInitializerConfigPointers"], ["0x180abc800"]
        )
        self.assertEqual(
            lifecycle["sharedSourceStateInitializerProviderOwnerPointers"],
            ["0x180abc900"],
        )
        self.assertEqual(
            lifecycle["sharedSourceStateInitializerDecoderOwnerPointers"],
            ["0x180abc900"],
        )
        self.assertEqual(
            lifecycle["sharedSourceStateInitializerInfoPointers"], ["0x180abc600"]
        )
        self.assertEqual(lifecycle["sharedSourceStateInitializerJoinKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceStateInitializerDecoderKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceStateSourceInfoKeys"], [123])
        self.assertEqual(lifecycle["registrationSourceInfoKeys"], [123])
        self.assertEqual(lifecycle["sourceInfoSelectionMediaKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceInfoProviderKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceStateProviderKeys"], [123])
        self.assertEqual(lifecycle["externalSiblingLookupKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceStateSiblingKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceStateManagerJoinKeys"], [123])
        self.assertEqual(lifecycle["sharedManagerJoinDecoderKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceProviderOwnerDecoderPointers"], ["0x180abc900"])
        self.assertEqual(lifecycle["sharedStateMediaLookupKeys"], [123])
        self.assertEqual(lifecycle["decoderPointers"], ["0x180abc000"])
        self.assertEqual(lifecycle["decoderDecodePointers"], ["0x180abc000"])
        self.assertEqual(lifecycle["decoderDecodeOwnerKeys"], [123])
        self.assertEqual(lifecycle["decoderDecodeProviderPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["decoderDecodeFloatBuffers"], ["0x180abe000"])
        self.assertEqual(lifecycle["decoderDecodeFrameCounts"], [480])
        self.assertEqual(lifecycle["decoderReturnAddresses"], ["0x1801c4780"])
        self.assertEqual(lifecycle["pcmConversionCallerReturnAddresses"], ["0x1801c4780"])
        self.assertEqual(lifecycle["pcmConversionDecoderCaptureCount"], 1)
        self.assertEqual(lifecycle["decoderRetryCaptureCount"], 0)
        self.assertEqual(lifecycle["sharedDecoderRegistryDecodePointers"], ["0x180abc000"])
        self.assertEqual(lifecycle["sharedSourceProviderDecoderPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["sharedDecoderRegistryDecodeKeys"], [123])
        self.assertEqual(lifecycle["sharedManagerJoinDecoderDecodeKeys"], [123])
        self.assertEqual(lifecycle["sharedSourceInfoDecoderDecodeKeys"], [123])
        self.assertEqual(lifecycle["descriptorAllocationBases"], ["0x180abc100"])
        self.assertEqual(lifecycle["externalDescriptorAllocationBases"], ["0x180abc100"])
        self.assertEqual(lifecycle["sharedDescriptorAllocationBases"], ["0x180abc100"])
        self.assertEqual(lifecycle["sharedManagerDescriptorAllocationBases"], ["0x180abc100"])
        self.assertEqual(lifecycle["externalDescriptorFiles"], ["voice/test.wem"])
        self.assertEqual(lifecycle["fileOpenPaths"], ["voice/test.wem"])
        self.assertEqual(lifecycle["fileOpenProviderContexts"], ["0x180abc350"])
        self.assertEqual(lifecycle["fileOpenHandles"], [0x123])
        self.assertEqual(lifecycle["asyncDescriptorProviderHandles"], [0x123])
        self.assertEqual(lifecycle["sharedOpenAsyncHandles"], [0x123])
        self.assertEqual(lifecycle["sourceProviderPaths"], ["voice/test.wem"])
        self.assertEqual(lifecycle["sourceProviderPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["sourceProviderOwnerPointers"], ["0x180abc900"])
        self.assertEqual(lifecycle["sourceInfoPointers"], ["0x180abc600"])
        self.assertEqual(lifecycle["decoderDecodeOwnerPointers"], ["0x180abc900"])
        self.assertEqual(lifecycle["ioProviderPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["asyncDescriptorProviderPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["sharedSourceProviderIoPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["sharedSourceProviderAsyncPointers"], ["0x180abc300"])
        self.assertEqual(lifecycle["sharedProviderOpenPaths"], ["voice/test.wem"])
        self.assertEqual(lifecycle["sharedDescriptorOpenPaths"], ["voice/test.wem"])
        self.assertIn("do not prove", lifecycle["evidenceBoundary"])
        self.assertIn("nativeKeyLifecycle", bundle["evidenceBoundary"])

    def test_callback_lifecycle_joins_native_context_to_managed_cookie(self):
        events = [
            row("callback-session", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "callback-session", 1, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="registration",
                hookName="AkSoundEngine.ExternalSourceManagerConstructor",
                sourceKind="externalSourceRegistration", rva="0xe1320",
                decodedArguments={"callbackCookie": "0x12340000"},
            ),
            row(
                "callback-session", 2, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="resolver",
                hookName="AkSoundEngine.ExternalSourceResolverCallback",
                sourceKind="externalSourceResolverCallback", rva="0xe19a0",
                memory={"descriptor0": "0x12340000"},
            ),
            row(
                "callback-session", 3, "audio_native_call", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="queue",
                hookName="AkSoundEngine.NativeCallbackQueueAppend",
                sourceKind="externalSourceCallbackQueueAppend", rva="0x3430",
                arguments={"arg0": "0x180abc500"},
                memory={"record0": "0x12340000"},
            ),
            row(
                "callback-session", 4, "audio_native_result", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="detach",
                hookName="AkSoundEngine.NativeCallbackQueueDetach",
                sourceKind="externalSourceCallbackQueueDetach", rva="0x2d10",
                returnValue="0x180abc500",
            ),
            row(
                "callback-session", 5, "audio_native_result", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="getter-cookie",
                hookName="AkSoundEngine.NativeCallbackRecordCookieGetter",
                sourceKind="externalSourceCallbackRecordCookieGetter", rva="0x2e310",
                decodedArgumentsAfter={"record": "0x180abc500"},
                returnValue="0x12340000",
            ),
            row(
                "callback-session", 6, "audio_native_result", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="getter-type",
                hookName="AkSoundEngine.NativeCallbackRecordTypeGetter",
                sourceKind="externalSourceCallbackRecordTypeGetter", rva="0x2e320",
                decodedArgumentsAfter={"record": "0x180abc500"},
                returnValue=0x20,
            ),
            row(
                "callback-session", 7, "audio_native_result", native=True,
                moduleName="AkSoundEngine.dll", nativeCaptureId="getter-payload",
                hookName="AkSoundEngine.NativeCallbackRecordPayloadGetter",
                sourceKind="externalSourceCallbackRecordPayloadGetter", rva="0x2e330",
                decodedArgumentsAfter={"record": "0x180abc500"},
                returnValue="0x180abc518",
            ),
            row(
                "callback-session", 8, "audio_request",
                captureId="unrelated-callback",
                hookName="AudioAdapter._OnExternalSourceEventCallback",
                sourceKind="adapterExternalSourceCallback",
                arguments={"callbackCookie": "0x12340000", "callbackType": 1},
            ),
            row(
                "callback-session", 9, "audio_request",
                captureId="wwise-pump",
                hookName="AkCallbackManager.PostCallbacks",
                sourceKind="wwiseCallbackPump",
                arguments={},
            ),
            row(
                "callback-session", 10, "audio_request",
                captureId="wwise-dispatch",
                parentCaptureId="wwise-pump",
                hookName="AkCallbackManager._ProcessEventCallback",
                sourceKind="wwiseCallbackDispatch",
                arguments={"callbackType": 1, "callbackInfo": "0xabc"},
            ),
            row(
                "callback-session", 11, "audio_request",
                captureId="external-callback",
                parentCaptureId="wwise-dispatch",
                hookName="AudioAdapter._OnExternalSourceEventCallback",
                sourceKind="adapterExternalSourceCallback",
                arguments={"callbackCookie": "0x12340000", "callbackType": 1},
            ),
            native_end("callback-session", 12),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        lifecycle = bundle["nativePairing"]["callbackLifecycle"][0]
        self.assertEqual(lifecycle["managedCallbackCookies"], ["0x12340000"])
        self.assertEqual(lifecycle["nativeRegistrationContexts"], ["0x12340000"])
        self.assertEqual(lifecycle["nativeResolverContexts"], ["0x12340000"])
        self.assertEqual(lifecycle["nativeQueueContexts"], ["0x12340000"])
        self.assertEqual(lifecycle["nativeQueueRecordPointers"], ["0x180abc500"])
        self.assertEqual(lifecycle["nativeQueueDetachHeadPointers"], ["0x180abc500"])
        self.assertEqual(lifecycle["nativeQueueGetterRecordPointers"], ["0x180abc500"])
        self.assertEqual(lifecycle["sharedQueueAppendGetterRecordPointers"], ["0x180abc500"])
        self.assertEqual(lifecycle["sharedQueueAppendDetachHeadPointers"], ["0x180abc500"])
        self.assertEqual(lifecycle["consumedOperation20RecordPointers"], ["0x180abc500"])
        self.assertEqual(
            lifecycle["nativeQueueGetterRecords"],
            [{
                "recordPointer": "0x180abc500",
                "cookies": ["0x12340000"],
                "types": [0x20],
                "payloads": ["0x180abc518"],
            }],
        )
        self.assertEqual(lifecycle["sharedManagedResolverContexts"], ["0x12340000"])
        self.assertEqual(lifecycle["sharedManagedRegistrationContexts"], ["0x12340000"])
        self.assertEqual(lifecycle["sharedManagedQueueContexts"], ["0x12340000"])
        self.assertEqual(lifecycle["managedWwisePumpCaptureCount"], 1)
        self.assertEqual(lifecycle["managedWwiseDispatchCaptureCount"], 1)
        self.assertEqual(lifecycle["managedWwiseDispatchTypes"], [1])
        self.assertEqual(lifecycle["managedExternalCallbackCaptureCount"], 2)
        self.assertEqual(lifecycle["managedExternalCallbackTypes"], [1])
        self.assertEqual(lifecycle["managedExternalCallbackChainCount"], 1)
        self.assertEqual(
            lifecycle["managedExternalCallbackChains"],
            [{
                "externalCallbackCaptureId": "external-callback",
                "dispatchCaptureId": "wwise-dispatch",
                "pumpCaptureId": "wwise-pump",
                "callbackTypes": [1],
            }],
        )
        self.assertIn("does not prove", lifecycle["evidenceBoundary"])
        self.assertIn("managed Wwise", lifecycle["evidenceBoundary"])
        self.assertIn("callbackLifecycle", bundle["evidenceBoundary"])

    def test_managed_external_path_lifecycle_joins_parent_and_native_path_strings(self):
        events = [
            row("path-session", 0, "session_start", gameBuild="fixture", captureTool="fixture"),
            row(
                "path-session", 1, "audio_request",
                captureId="voice-1",
                hookName="VoicePlayer.ExternalSourcePreparation",
                sourceKind="voiceExternalSourcePreparation",
                rva="0x3abef40",
                arguments={
                    "externalSourceKey": "voice/chinese/dialog/fixture.wem",
                    "wwiseEvent": "0x1000",
                    "handleId": 17,
                },
                stackArguments={"codec": 20},
                returnValue=4567,
            ),
            row(
                "path-session", 2, "audio_request",
                captureId="adapter-1",
                parentCaptureId="voice-1",
                hookName="AudioAdapter._PostEventWithExternalSource",
                sourceKind="adapterExternalSourcePostEvent",
                rva="0x3abea70",
                arguments={
                    "eventId": 123,
                    "externalSourceKey": "voice/chinese/dialog/fixture.wem",
                    "externalCookie": 0x24DB9834,
                },
                returnValue=8901,
            ),
            row(
                "path-session", 3, "audio_native_call",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="descriptor",
                hookName="AkSoundEngine.ExternalDescriptorCopy",
                sourceKind="externalDescriptorCopy",
                managedCallStack=[{
                    "captureId": "adapter-1",
                    "hookName": "AudioAdapter._PostEventWithExternalSource",
                    "sourceKind": "adapterExternalSourcePostEvent",
                }],
                memory={"externalFile": "voice/chinese/dialog/fixture.wem"},
            ),
            row(
                "path-session", 4, "audio_native_call",
                native=True,
                moduleName="AkSoundEngine.dll",
                nativeCaptureId="open",
                hookName="AkSoundEngine.DefaultIoOpenDispatch",
                sourceKind="wwiseDefaultIoOpenDispatch",
                managedCallStack=[{
                    "captureId": "adapter-1",
                    "hookName": "AudioAdapter._PostEventWithExternalSource",
                    "sourceKind": "adapterExternalSourcePostEvent",
                }],
                decodedArguments={"filePath": "voice/chinese/dialog/fixture.wem"},
            ),
            native_end("path-session", 5),
        ]
        bundle = importer.build_bundle(events, ["fixture"], Path("missing-index.json"))
        lifecycle = bundle["nativePairing"]["managedExternalPathLifecycle"][0]
        self.assertEqual(lifecycle["voicePreparationPaths"], ["voice/chinese/dialog/fixture.wem"])
        self.assertEqual(lifecycle["adapterExternalPaths"], ["voice/chinese/dialog/fixture.wem"])
        self.assertEqual(lifecycle["voicePreparationReturnValues"], [4567])
        self.assertEqual(lifecycle["voicePreparationHandleIds"], [17])
        self.assertEqual(lifecycle["voicePreparationCodecs"], [20])
        self.assertEqual(lifecycle["adapterExternalPostReturnValues"], [8901])
        self.assertEqual(lifecycle["adapterExternalCookieValues"], [0x24DB9834])
        self.assertEqual(lifecycle["sharedVoiceAdapterPaths"], ["voice/chinese/dialog/fixture.wem"])
        self.assertEqual(lifecycle["sharedVoiceDescriptorPaths"], ["voice/chinese/dialog/fixture.wem"])
        self.assertEqual(lifecycle["sharedVoiceOpenPaths"], ["voice/chinese/dialog/fixture.wem"])
        self.assertEqual(lifecycle["managedParentCorrelationCount"], 1)
        self.assertEqual(lifecycle["managedParentPathMatchCount"], 1)
        self.assertEqual(lifecycle["managedNativeContextCorrelationCount"], 2)
        self.assertEqual(lifecycle["managedNativeContextPathMatchCount"], 2)
        self.assertEqual(
            {row["nativeSourceKind"] for row in lifecycle["managedNativeContextCorrelations"]},
            {"externalDescriptorCopy", "wwiseDefaultIoOpenDispatch"},
        )
        self.assertEqual(
            lifecycle["managedParentCorrelations"][0]["pathEvidenceStatus"],
            "exact_match",
        )
        self.assertIn("managedExternalPathLifecycle", bundle["evidenceBoundary"])

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
