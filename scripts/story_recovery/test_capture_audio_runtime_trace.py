import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import capture_audio_runtime_trace as capture


class AudioRuntimeCaptureTests(unittest.TestCase):
    def test_current_manifest_is_hash_locked_and_has_carrier_boundaries(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)
        self.assertEqual(manifest["gameBuild"], "endfield-2026-07-11-gameassembly-0c557367")
        hooks = {hook["name"]: hook for hook in manifest["hooks"]}
        self.assertEqual(hooks["AudioAdapter.PostEvent(string)"]["rva"], "0x46d3f80")
        self.assertFalse(hooks["AudioAdapter.PostEvent(string)"].get("instance", False))
        self.assertEqual(hooks["AudioAdapter.PostEvent(string)"]["args"]["eventKey"]["index"], 0)
        self.assertEqual(hooks["AudioAdapter._PostEvent"]["rva"], "0x328a690")
        self.assertEqual(hooks["AudioAdapter._PostEvent"]["token"], "0x0600005f")
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
        with self.assertRaisesRegex(capture.support.CaptureConfigurationError, "mode"):
            capture.load_manifest(path)

    def test_manifest_rejects_rva_outside_verified_module(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        module = Path(temporary.name) / "GameAssembly.dll"
        module.write_bytes(b"module")
        manifest = {
            "hooks": [{"name": "bad", "rva": "0x6", "sourceKind": "x"}],
        }
        with self.assertRaisesRegex(capture.support.CaptureConfigurationError, "outside"):
            capture.validate_hook_ranges(manifest, module)

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
        self.assertEqual(config["evidenceBoundary"]["classification"], "observed_runtime_request")


if __name__ == "__main__":
    unittest.main()
