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
        self.assertEqual(native_hooks["AkSoundEngine.ExternalSourceManagerLookup"]["rva"], "0xe2820")
        self.assertEqual(native_hooks["AkSoundEngine.ExternalSourceManagerLookup"]["returnKind"], "bool")
        join = native_hooks["AkSoundEngine.ExternalSourceManagerJoin"]
        self.assertEqual(join["rva"], "0xe2cd0")
        self.assertEqual(join["args"]["sourceKey"]["index"], 1)
        self.assertEqual(join["memory"][0]["offset"], 0)
        self.assertEqual(join["memory"][1]["offset"], 616)
        decoder_registry = native_hooks["AkSoundEngine.SourceKeyDecoderRegistry"]
        self.assertEqual(decoder_registry["rva"], "0x13f440")
        self.assertEqual(decoder_registry["args"]["decoder"]["index"], 2)
        self.assertEqual(decoder_registry["returnKind"], "u32")
        provider_prep = native_hooks["AkSoundEngine.SourceProviderPreparation"]
        self.assertEqual(provider_prep["rva"], "0x1af7a0")
        self.assertEqual(provider_prep["memory"][1]["pointerOffset"], 24)
        self.assertEqual(provider_prep["memory"][3]["offset"], 664)
        self.assertEqual(provider_prep["memory"][3]["kind"], "utf16")
        self.assertEqual(
            native_hooks["AkSoundEngine.ExternalDescriptorPostEvent"]["rva"],
            "0xc38b0",
        )
        descriptor_copy = native_hooks["AkSoundEngine.ExternalDescriptorCopy"]
        self.assertEqual(descriptor_copy["args"]["externalCount"]["kind"], "u32")
        self.assertEqual(descriptor_copy["memory"][2]["kind"], "utf16")
        self.assertEqual(descriptor_copy["memory"][2]["offset"], 8)
        self.assertEqual(descriptor_copy["memory"][4]["offset"], 24)
        open_dispatch = native_hooks["AkSoundEngine.DefaultIoOpenDispatch"]
        self.assertEqual(open_dispatch["rva"], "0x5030")
        self.assertEqual(open_dispatch["args"]["filePath"]["kind"], "utf16")
        self.assertEqual(open_dispatch["args"]["openMode"]["kind"], "u32")
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
        self.assertEqual(async_read["memory"][5]["name"], "descriptorRequestContext")
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
        self.assertEqual(hooks["AudioAdapter._OnExternalSourceEventCallback"]["rva"], "0x43c7930")
        self.assertEqual(hooks["AkCallbackManager.PostCallbacks"]["methodIndex"], 446952)
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
