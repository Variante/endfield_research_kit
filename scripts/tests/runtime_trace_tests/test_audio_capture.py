import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import runtime_trace_audio_capture as capture
from scripts.story_recovery import runtime_trace_core as core


class AudioRuntimeCaptureTests(unittest.TestCase):
    def test_current_manifest_is_hash_locked_and_has_carrier_boundaries(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)
        self.assertEqual(manifest["gameBuild"], "endfield-2026-07-11-gameassembly-0c557367")
        self.assertEqual(manifest["nativeModuleName"], "AkSoundEngine.dll")
        self.assertEqual(
            manifest["files"]["akSoundEngine"]["sha256"],
            "b33c3c71e44c305fb1c3903942308f2ab55a7854d68c719fe55e7de323e7dba2",
        )
        native_hooks = {hook["name"]: hook for hook in manifest["nativeHooks"]}
        self.assertEqual(native_hooks["AkSoundEngine.ExternalSourceManagerConstructor"]["rva"], "0xe1320")
        constructor = native_hooks["AkSoundEngine.ExternalSourceManagerConstructor"]
        self.assertEqual(constructor["args"]["callbackFunction"]["index"], 5)
        self.assertEqual(constructor["args"]["callbackCookie"]["index"], 6)
        self.assertEqual(constructor["args"]["operationFlags"]["index"], 7)
        agent_source = capture.DEFAULT_AGENT.read_text(encoding="utf-8")
        self.assertIn("nativeArgumentCount(hook)", agent_source)
        self.assertIn("readNativeArguments(hook, args)", agent_source)
        self.assertEqual(constructor["returnKind"], "u32")
        self.assertEqual(native_hooks["AkSoundEngine.ExternalSourceManagerLookup"]["rva"], "0xe2820")
        self.assertEqual(native_hooks["AkSoundEngine.ExternalSourceManagerLookup"]["returnKind"], "bool")
        sibling = native_hooks["AkSoundEngine.ExternalSourceManagerSiblingLookup"]
        self.assertEqual(sibling["rva"], "0xe28d0")
        self.assertEqual(sibling["args"]["sourceKey"]["index"], 1)
        state_callback = native_hooks["AkSoundEngine.ExternalSourceStateCallback"]
        self.assertEqual(state_callback["rva"], "0x143990")
        self.assertEqual(state_callback["memory"][2]["pointerOffset"], 8)
        self.assertEqual(state_callback["memory"][2]["offset"], 592)
        queue_detach = native_hooks["AkSoundEngine.NativeCallbackQueueDetach"]
        self.assertEqual(queue_detach["rva"], "0x2d10")
        self.assertEqual(queue_detach["returnKind"], "pointer")
        getter = native_hooks["AkSoundEngine.NativeCallbackRecordTypeGetter"]
        self.assertEqual(getter["rva"], "0x2e320")
        self.assertEqual(getter["args"]["record"]["index"], 0)
        self.assertEqual(getter["returnKind"], "u32")
        join = native_hooks["AkSoundEngine.ExternalSourceManagerJoin"]
        self.assertEqual(join["rva"], "0xe2cd0")
        self.assertEqual(join["args"]["sourceKey"]["index"], 1)
        self.assertEqual(join["memory"][0]["offset"], 0)
        self.assertEqual(join["memory"][1]["offset"], 616)
        decoder_registry = native_hooks["AkSoundEngine.SourceKeyDecoderRegistry"]
        self.assertEqual(decoder_registry["rva"], "0x13f440")
        self.assertEqual(decoder_registry["args"]["decoder"]["index"], 2)
        self.assertEqual(decoder_registry["returnKind"], "u32")
        decoder_decode = native_hooks["AkSoundEngine.CodecDecoderDecode"]
        self.assertEqual(decoder_decode["rva"], "0x1c7ec0")
        self.assertEqual(decoder_decode["args"]["decoder"]["index"], 0)
        self.assertEqual(decoder_decode["args"]["floatOutputSlot"]["index"], 1)
        self.assertEqual(decoder_decode["args"]["frameCountSlot"]["index"], 2)
        self.assertEqual(decoder_decode["memory"][1]["pointerOffset"], 24)
        self.assertEqual(decoder_decode["memory"][1]["offset"], 616)
        self.assertEqual(decoder_decode["memory"][2]["offset"], 88)
        self.assertEqual(decoder_decode["memory"][6]["offset"], 0)
        self.assertEqual(decoder_decode["memory"][7]["kind"], "u32")
        self.assertEqual(decoder_decode["returnKind"], "i32")
        source_info_consumer = native_hooks["AkSoundEngine.SourceInfoSelectionConsumer"]
        self.assertEqual(source_info_consumer["rva"], "0xd2ed0")
        self.assertEqual(source_info_consumer["returnKind"], "bool")
        self.assertEqual(source_info_consumer["memory"][1]["pointerOffset"], 648)
        source_info_consumer_memory = {
            item["name"]: item for item in source_info_consumer["memory"]
        }
        self.assertEqual(
            source_info_consumer_memory["sourceObjectSelectedDescriptor"]["offset"],
            824,
        )
        self.assertEqual(
            source_info_consumer_memory["sourceObjectSelectedDescriptorAux"]["offset"],
            832,
        )
        source_state_initializer = native_hooks["AkSoundEngine.SourceStateInitializer"]
        self.assertEqual(source_state_initializer["rva"], "0xd1f90")
        self.assertEqual(source_state_initializer["args"]["sourceState"]["index"], 0)
        self.assertEqual(source_state_initializer["args"]["sourceInfo"]["index"], 3)
        source_state_initializer_memory = {
            item["name"]: item for item in source_state_initializer["memory"]
        }
        self.assertEqual(source_state_initializer_memory["sourceStateKey268"]["offset"], 616)
        self.assertEqual(source_state_initializer_memory["sourceStateSourceInfo"]["offset"], 648)
        self.assertEqual(source_state_initializer_memory["sourceConfigKey34"]["offset"], 52)
        self.assertEqual(source_state_initializer_memory["sourceInfoPath"]["kind"], "utf16")
        source_info_selector = native_hooks["AkSoundEngine.SourceInfoSelector"]
        self.assertEqual(source_info_selector["rva"], "0xf5030")
        self.assertEqual(source_info_selector["args"]["sourceInfoKey"]["index"], 1)
        self.assertEqual(source_info_selector["memory"][1]["pointerOffset"], 0)
        self.assertEqual(source_info_selector["memory"][1]["offset"], 8)
        self.assertEqual(source_info_selector["memory"][3]["offset"], 16)
        self.assertEqual(source_info_selector["memory"][4]["offset"], 24)
        provider_prep = native_hooks["AkSoundEngine.SourceProviderPreparation"]
        self.assertEqual(provider_prep["rva"], "0x1af7a0")
        self.assertEqual(provider_prep["memory"][1]["pointerOffset"], 24)
        self.assertEqual(provider_prep["memory"][2]["pointerOffsets"], [24, 648])
        self.assertEqual(provider_prep["memory"][4]["offset"], 664)
        self.assertEqual(provider_prep["memory"][4]["kind"], "utf16")
        provider_prep_memory = {item["name"]: item for item in provider_prep["memory"]}
        self.assertEqual(
            provider_prep_memory["sourceOwnerSelectedDescriptor"]["offset"],
            824,
        )
        self.assertEqual(
            provider_prep_memory["sourceOwnerSelectedDescriptorAux"]["offset"],
            832,
        )
        self.assertEqual(provider_prep_memory["decoderProvider"]["offset"], 88)
        self.assertEqual(
            native_hooks["AkSoundEngine.ExternalDescriptorPostEvent"]["rva"],
            "0xc38b0",
        )
        descriptor_copy = native_hooks["AkSoundEngine.ExternalDescriptorCopy"]
        self.assertEqual(descriptor_copy["args"]["externalCount"]["kind"], "u32")
        self.assertEqual(descriptor_copy["memory"][0]["name"], "copiedAllocationBase")
        self.assertEqual(descriptor_copy["memory"][0]["offset"], 0)
        self.assertEqual(descriptor_copy["memory"][3]["kind"], "utf16")
        self.assertEqual(descriptor_copy["memory"][3]["offset"], 8)
        self.assertEqual(descriptor_copy["memory"][5]["offset"], 24)
        open_dispatch = native_hooks["AkSoundEngine.DefaultIoOpenDispatch"]
        self.assertEqual(open_dispatch["rva"], "0x5030")
        self.assertEqual(open_dispatch["args"]["filePath"]["kind"], "utf16")
        self.assertEqual(open_dispatch["args"]["openMode"]["kind"], "u32")
        self.assertEqual(open_dispatch["memory"][0]["stackOffset"], 40)
        self.assertEqual(open_dispatch["memory"][0]["name"], "openProviderContext")
        self.assertTrue(open_dispatch["memory"][0]["savePointer"])
        self.assertEqual(open_dispatch["memory"][2]["baseField"], "openProviderContext")
        self.assertEqual(open_dispatch["memory"][2]["offset"], 16)
        self.assertEqual(open_dispatch["memory"][2]["kind"], "u64")
        self.assertEqual(open_dispatch["returnKind"], "u32")
        self.assertNotIn("AkSoundEngine.DefaultIoCreateFile", native_hooks)
        device_dispatch = native_hooks["AkSoundEngine.DeviceQueueDispatch"]
        self.assertEqual(device_dispatch["args"]["requestCount"]["index"], 1)
        self.assertEqual(device_dispatch["memory"][0]["name"], "provider0")
        provider_dispatch = native_hooks["AkSoundEngine.DefaultIoProviderBatchDispatch"]
        self.assertEqual(provider_dispatch["rva"], "0x5430")
        self.assertEqual(provider_dispatch["args"]["providerArray"]["index"], 2)
        codec_stream = native_hooks["AkSoundEngine.CodecStreamRead"]
        self.assertEqual(codec_stream["rva"], "0x1c9fa0")
        self.assertEqual(codec_stream["args"]["requestedBytes"]["kind"], "u64")
        self.assertEqual(codec_stream["memory"][0]["offset"], 0)
        self.assertEqual(codec_stream["memory"][1]["offset"], 32)
        self.assertEqual(codec_stream["memory"][2]["offset"], 72)
        self.assertEqual(codec_stream["memory"][3]["name"], "streamBuffer")
        self.assertEqual(codec_stream["memory"][4]["offset"], 96)
        self.assertEqual(codec_stream["memory"][5]["offset"], 100)
        memory_copy = native_hooks["AkSoundEngine.CodecMemorySourceCopy"]
        self.assertEqual(memory_copy["rva"], "0x1c44d0")
        self.assertEqual(memory_copy["returnKind"], "i32")
        self.assertEqual(memory_copy["memory"][0]["offset"], 96)
        self.assertEqual(memory_copy["memory"][2]["offset"], 108)
        self.assertEqual(memory_copy["memory"][3]["name"], "refillObject")
        self.assertEqual(memory_copy["memory"][3]["offset"], 88)
        async_read = native_hooks["AkSoundEngine.AsyncBatchRead"]
        self.assertEqual(async_read["memory"][4]["name"], "descriptorProviderHandle")
        self.assertEqual(async_read["memory"][4]["pointerOffset"], 0)
        self.assertEqual(async_read["memory"][5]["name"], "descriptorTransferScalar")
        self.assertEqual(async_read["memory"][6]["name"], "descriptorRequestContext")
        completion = native_hooks["AkSoundEngine.AsyncReadCompletion"]
        self.assertEqual(completion["memory"][4]["name"], "completionRequestCallback")
        self.assertEqual(
            native_hooks["AkSoundEngine.ExternalSourceManagerLookup"]["memory"][2]["offset"],
            16,
        )
        hooks = {hook["name"]: hook for hook in manifest["hooks"]}
        self.assertEqual(hooks["AudioAdapter.PostEvent(string)"]["rva"], "0x46d3f80")
        self.assertFalse(hooks["AudioAdapter.PostEvent(string)"].get("instance", False))
        self.assertEqual(hooks["AudioAdapter.PostEvent(string)"]["args"]["eventKey"]["index"], 0)
        self.assertEqual(hooks["AudioAdapter._PostEvent"]["rva"], "0x328a690")
        self.assertEqual(hooks["AudioAdapter._PostEvent"]["token"], "0x0600005f")
        self.assertEqual(
            hooks["AudioAdapter._PostEventWithExternalSource"]["args"]["externalSourceKey"]["kind"],
            "string",
        )
        voice_external = hooks["VoicePlayer.ExternalSourcePreparation"]
        self.assertEqual(voice_external["rva"], "0x3abef40")
        self.assertFalse(voice_external["required"])
        self.assertEqual(voice_external["args"]["externalSourceKey"]["kind"], "string")
        self.assertEqual(voice_external["args"]["wwiseEvent"]["index"], 1)
        self.assertEqual(voice_external["args"]["handleId"]["kind"], "u32")
        self.assertEqual(voice_external["stackArguments"], [{"name": "codec", "offset": 40, "kind": "u32"}])
        self.assertEqual(hooks["AudioAdapter._OnExternalSourceEventCallback"]["rva"], "0x43c7930")
        self.assertEqual(hooks["AkCallbackManager.PostCallbacks"]["methodIndex"], 446952)
        dispatch = hooks["AkCallbackManager._ProcessEventCallback"]
        self.assertEqual(dispatch["args"]["callbackType"]["index"], 0)
        self.assertEqual(dispatch["args"]["callbackInfo"]["index"], 1)
        external_callback = hooks["AudioAdapter._OnExternalSourceEventCallback"]
        self.assertEqual(external_callback["args"]["callbackCookie"]["index"], 0)
        self.assertEqual(external_callback["args"]["callbackType"]["index"], 1)
        self.assertEqual(external_callback["args"]["callbackInfo"]["index"], 2)
        self.assertEqual(
            hooks["AudioAdapter._OnEventPreparedDoPostEvent"]["args"]["preparationResult"]["kind"],
            "u32",
        )
        self.assertEqual(hooks["GameAction.PlayAudio(string, gameObject)"]["rva"], "0x3d40600")
        self.assertEqual(
            hooks["GameAction.PlayAudio(eventId, gameObject)"]["args"]["eventId"]["kind"],
            "u32",
        )
        self.assertEqual(
            hooks["PlaySoundAction._DoPostEvent"]["sourceKind"],
            "playSoundActionObject",
        )
        self.assertEqual(
            hooks["GameAction.PlayAudioAtPosition"]["sourceKind"],
            "levelScriptAudioActionPosition",
        )
        self.assertEqual(
            hooks["AudioDlgEventPlayableBehaviour._DoPlayEvent"]["sourceKind"],
            "timelineAudioPlay",
        )

    def test_manifest_rejects_invalid_hook_mode(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "manifest.json"
        value = {
            "schema": capture.MANIFEST_SCHEMA,
            "gameBuild": "fixture",
            "processName": "Endfield.exe",
            "moduleName": "GameAssembly.dll",
            "files": {"executable": {}, "gameAssembly": {}, "metadata": {}},
            "hooks": [{"name": "bad", "rva": "0x1", "mode": "bad", "sourceKind": "x"}],
            "evidenceBoundary": {},
        }
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(core.CaptureConfigurationError, "mode"):
            capture.load_manifest(path)

    def test_manifest_accepts_stack_memory_and_rejects_ambiguous_memory_base(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "manifest.json"
        base = {
            "schema": capture.MANIFEST_SCHEMA,
            "gameBuild": "fixture",
            "processName": "Endfield.exe",
            "moduleName": "GameAssembly.dll",
            "nativeModuleName": "AkSoundEngine.dll",
            "files": {"executable": {}, "gameAssembly": {}, "metadata": {}, "akSoundEngine": {}},
            "hooks": [{"name": "managed", "rva": "0x1", "sourceKind": "x", "mode": "request"}],
            "nativeHooks": [{
                "name": "native",
                "rva": "0x1",
                "sourceKind": "x",
                "memory": [{"name": "stackValue", "stackOffset": 40, "offset": 16, "kind": "u64"}],
            }],
            "evidenceBoundary": {},
        }
        path.write_text(json.dumps(base), encoding="utf-8")
        loaded = capture.load_manifest(path)
        self.assertEqual(loaded["nativeHooks"][0]["memory"][0]["stackOffset"], 40)
        for memory in (
            {"name": "both", "argIndex": 0, "stackOffset": 40},
            {"name": "neither"},
        ):
            invalid = dict(base)
            invalid["nativeHooks"] = [{**base["nativeHooks"][0], "memory": [memory]}]
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(core.CaptureConfigurationError, "exactly one"):
                capture.load_manifest(path)
        invalid = dict(base)
        invalid["nativeHooks"] = [{
            **base["nativeHooks"][0],
            "memory": [{
                "name": "bothPointerForms",
                "argIndex": 0,
                "pointerOffset": 0,
                "pointerOffsets": [0],
            }],
        }]
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaisesRegex(core.CaptureConfigurationError, "cannot set both"):
            capture.load_manifest(path)

    def test_manifest_validates_managed_stack_argument_contract(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "manifest.json"
        base = {
            "schema": capture.MANIFEST_SCHEMA,
            "gameBuild": "fixture",
            "processName": "Endfield.exe",
            "moduleName": "GameAssembly.dll",
            "files": {"executable": {}, "gameAssembly": {}, "metadata": {}},
            "hooks": [{
                "name": "managed",
                "rva": "0x1",
                "sourceKind": "x",
                "mode": "request",
                "stackArguments": [{"name": "codec", "offset": 40, "kind": "u32"}],
            }],
            "evidenceBoundary": {},
        }
        path.write_text(json.dumps(base), encoding="utf-8")
        self.assertEqual(capture.load_manifest(path)["hooks"][0]["stackArguments"][0]["offset"], 40)
        for stack_arguments, pattern in (
            ({"name": "codec", "offset": 40}, "must be a list"),
            ([{"name": "codec", "offset": -1}], "offset must be non-negative"),
            ([{"name": "codec", "offset": 40, "kind": "bool"}], "unsupported kind"),
            ([{"name": "codec", "offset": 40, "kind": []}], "unsupported kind"),
        ):
            invalid = dict(base)
            invalid["hooks"] = [{**base["hooks"][0], "stackArguments": stack_arguments}]
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(core.CaptureConfigurationError, pattern):
                capture.load_manifest(path)

    def test_manifest_validates_abi_argument_indices_and_return_kinds(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "manifest.json"
        base = {
            "schema": capture.MANIFEST_SCHEMA,
            "gameBuild": "fixture",
            "processName": "Endfield.exe",
            "moduleName": "GameAssembly.dll",
            "files": {"executable": {}, "gameAssembly": {}, "metadata": {}},
            "hooks": [{
                "name": "managed",
                "rva": "0x1",
                "sourceKind": "x",
                "mode": "request",
                "args": {"event": {"index": 0, "kind": "u32"}},
                "returnKind": "void",
            }],
            "evidenceBoundary": {},
        }
        invalids = (
            ({"event": {"index": -1, "kind": "u32"}}, "index must be"),
            ({"event": {"index": 64, "kind": "u32"}}, "index must be"),
            ({"event": {"index": 0, "kind": []}}, "unsupported kind"),
        )
        for args, pattern in invalids:
            invalid = {**base, "hooks": [{**base["hooks"][0], "args": args}]}
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.subTest(args=args), self.assertRaisesRegex(
                core.CaptureConfigurationError, pattern
            ):
                capture.load_manifest(path)
        invalid = {**base, "hooks": [{**base["hooks"][0], "returnKind": "bad"}]}
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaisesRegex(core.CaptureConfigurationError, "returnKind"):
            capture.load_manifest(path)

    def test_manifest_rejects_rva_outside_verified_module(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "GameAssembly.dll"
        module.write_bytes(b"module")
        manifest = {
            "hooks": [{"name": "bad", "rva": "0x6", "sourceKind": "x"}],
        }
        with self.assertRaisesRegex(core.CaptureConfigurationError, "outside"):
            capture.validate_hook_ranges(manifest, module)

    def test_native_hook_range_uses_verified_native_module(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        game_assembly = Path(temporary.name) / "GameAssembly.dll"
        native = Path(temporary.name) / "AkSoundEngine.dll"
        game_assembly.write_bytes(b"g" * 32)
        native.write_bytes(b"n" * 64)
        manifest = {
            "hooks": [{"name": "managed", "rva": "0x1", "sourceKind": "x"}],
            "nativeHooks": [{"name": "native", "rva": "0x20", "sourceKind": "x"}],
        }
        capture.validate_hook_ranges(manifest, game_assembly, native)
        with self.assertRaisesRegex(core.CaptureConfigurationError, "AkSoundEngine"):
            capture.validate_hook_ranges(
                {"hooks": manifest["hooks"], "nativeHooks": [{"name": "native", "rva": "0x40", "sourceKind": "x"}]},
                game_assembly,
                native,
            )

    def test_attached_module_must_match_verified_path_and_size(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "GameAssembly.dll"
        module.write_bytes(b"module")
        ready = {"modulePath": str(module), "moduleSize": module.stat().st_size}
        facts = capture.validate_attached_module(ready, module)
        self.assertTrue(facts["modulePathMatch"])
        self.assertTrue(facts["moduleSizeMatch"])
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            capture.validate_attached_module(
                {"modulePath": str(module), "moduleSize": module.stat().st_size + 1},
                module,
            )
        with self.assertRaisesRegex(RuntimeError, "sha256Match=False"):
            capture.validate_attached_module(
                {"modulePath": str(module), "moduleSize": module.stat().st_size},
                module,
                "0" * 64,
            )

    def test_attached_native_module_must_match_verified_path_and_size(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "AkSoundEngine.dll"
        module.write_bytes(b"native")
        ready = {"nativeModulePath": str(module), "nativeModuleSize": module.stat().st_size}
        facts = capture.validate_attached_native_module(ready, module)
        self.assertTrue(facts["nativeModulePathMatch"])
        self.assertTrue(facts["nativeModuleSizeMatch"])
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            capture.validate_attached_native_module(
                {"nativeModulePath": str(module), "nativeModuleSize": module.stat().st_size + 1},
                module,
            )
        with self.assertRaisesRegex(RuntimeError, "sha256Match=False"):
            capture.validate_attached_native_module(
                {"nativeModulePath": str(module), "nativeModuleSize": module.stat().st_size},
                module,
                "0" * 64,
            )

    def test_agent_placeholder_is_rendered(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "agent.js"
        path.write_text(
            f"const CONFIG = {capture.AUDIO_AGENT_PLACEHOLDER};\n",
            encoding="utf-8",
        )
        manifest = {
            "gameBuild": "fixture",
            "moduleName": "GameAssembly.dll",
            "hooks": [],
            "evidenceBoundary": {"classification": "observed_runtime_request"},
        }
        rendered = capture.render_agent_source(path, manifest)
        self.assertNotIn(capture.AUDIO_AGENT_PLACEHOLDER, rendered)
        config = json.loads(rendered.removeprefix("const CONFIG = ").removesuffix(";\n"))
        self.assertEqual(config["gameBuild"], "fixture")
        self.assertEqual(config["nativeModuleName"], None)
        self.assertEqual(config["nativeHooks"], [])
        self.assertEqual(config["evidenceBoundary"]["classification"], "observed_runtime_request")


if __name__ == "__main__":
    unittest.main()
