import contextlib
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from scripts.story_recovery import runtime_trace_audio_native_capture as launcher


class AudioNativeCaptureLauncherTests(unittest.TestCase):
    @staticmethod
    def _pe_x64() -> bytes:
        image = bytearray(0x100)
        image[:2] = b"MZ"
        image[0x3C:0x40] = (0x80).to_bytes(4, "little")
        image[0x80:0x84] = b"PE\0\0"
        image[0x84:0x86] = (0x8664).to_bytes(2, "little")
        image[0x98:0x9A] = (0x20B).to_bytes(2, "little")
        return bytes(image)

    def _plan(self, root: Path) -> launcher.NativeCapturePlan:
        manifest_path = root / "hooks.json"
        manifest_path.write_text("{}", encoding="utf-8")
        game_assembly = root / "GameAssembly.dll"
        metadata = root / "global-metadata.dat"
        native = root / "AkSoundEngine.dll"
        for path in (game_assembly, metadata, native):
            path.write_bytes(path.name.encode("ascii"))
        manifest = {
            "gameBuild": "fixture-build",
            "processName": "Endfield.exe",
            "moduleName": "GameAssembly.dll",
            "nativeModuleName": "AkSoundEngine.dll",
            "language": "CN",
            "files": {
                "gameAssembly": {
                    "relativePath": game_assembly.name,
                    "bytes": game_assembly.stat().st_size,
                    "sha256": launcher._sha256(game_assembly),
                },
                "metadata": {
                    "relativePath": metadata.name,
                    "bytes": metadata.stat().st_size,
                    "sha256": launcher._sha256(metadata),
                },
                "akSoundEngine": {
                    "relativePath": native.name,
                    "bytes": native.stat().st_size,
                    "sha256": launcher._sha256(native),
                },
            },
            "nativeCaptureProfiles": {
                "audio_chain_v1": {
                    "enabled": list(launcher.HOOK_PROFILE_FIELDS),
                    "deferred": {
                        "AkSoundEngine.ExternalDescriptorPostEvent": "native ABI not yet recovered"
                    },
                }
            },
            "hooks": [
                {"name": "AudioAdapter._PostEventWithExternalSource", "rva": "0x1000"}
            ],
            "nativeHooks": [
                {"name": "AkSoundEngine.SourceMediaLookup", "rva": "0x2000"},
                {"name": "AkSoundEngine.DefaultIoOpenDispatch", "rva": "0x3000"},
            ],
            "evidenceBoundary": {},
        }
        return launcher.NativeCapturePlan(
            game_root=root,
            manifest_path=manifest_path,
            manifest=manifest,
            verified={"gameAssembly": game_assembly, "metadata": metadata, "akSoundEngine": native},
            manifest_sha256=launcher._sha256(manifest_path),
            agent_sha256="a" * 64,
        )

    def test_check_only_has_no_staging_or_injection_side_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self._plan(root)
            args = launcher.parse_args(["--check-only", "--package-dir", str(root / "package")])
            with mock.patch.object(launcher, "prepare_plan", return_value=plan), mock.patch.object(
                launcher, "inject_once", side_effect=AssertionError("injection attempted")
            ), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(launcher.run(args), 0)
            self.assertIn("no process, pyinjector, package, or session access", output.getvalue())
            self.assertFalse((root / "package").exists())

    def test_package_and_session_records_are_hash_bound_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self._plan(root)
            payload = root / "payload.dll"
            payload.write_bytes(self._pe_x64())
            plan = launcher.NativeCapturePlan(**{**plan.__dict__, "payload": payload, "payload_sha256": launcher._sha256(payload)})
            package = launcher.stage_package(plan, root / "package", session_id="fixture-session", pid=1234)
            session = launcher.stage_session(
                plan,
                root / "session",
                session_id="fixture-session",
                pid=1234,
            )
            self.assertEqual(
                launcher.stage_session(
                    plan,
                    root / "session",
                    session_id="fixture-session",
                    pid=1234,
                ),
                session,
            )
            self.assertTrue(package.with_name(launcher.STAGED_PAYLOAD_NAME).is_file())
            session_record = json.loads(package.read_text(encoding="utf-8"))
            self.assertEqual(launcher.SESSION_SCHEMA, "audioRuntimeTrace.session.v1")
            self.assertEqual(session_record["schema"], "audioRuntimeTrace.session.v1")
            self.assertEqual(session_record["session_id"], "fixture-session")
            self.assertEqual(session_record["expected_process_name"], "Endfield.exe")
            self.assertEqual(session_record["native_module_name"], "AkSoundEngine.dll")
            self.assertEqual(session_record["hook_profile"], "audio_chain_v1")
            self.assertEqual(session_record["managed_external_source_rva"], 0x1000)
            self.assertEqual(session_record["source_media_lookup_rva"], 0x2000)
            self.assertEqual(session_record["default_io_open_rva"], 0x3000)
            self.assertNotIn("sessionId", session_record)
            self.assertEqual(json.loads(session.read_text(encoding="utf-8"))["session_id"], "fixture-session")

    def test_staging_refuses_different_existing_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self._plan(root)
            payload = root / "payload.dll"
            payload.write_bytes(self._pe_x64())
            plan = launcher.NativeCapturePlan(**{**plan.__dict__, "payload": payload, "payload_sha256": launcher._sha256(payload)})
            package = launcher.stage_package(plan, root / "package", session_id="fixture-session")
            package.write_text('{"schema":"other"}\n', encoding="utf-8")
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "different staged"):
                launcher.stage_package(plan, root / "package", session_id="fixture-session")

    def test_manifest_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self._plan(root)
            plan.manifest["files"]["metadata"]["relativePath"] = "..\\outside.dat"
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "escapes"):
                launcher._validate_manifest_containment(root, plan.manifest)

    def test_handshake_success_and_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "events.jsonl"
            row = {
                "schema": "audioRuntimeTrace.event.v1",
                "sessionId": "fixture-session",
                "seq": 0,
                "monotonicMs": 0,
                "kind": "session_start",
                "gameBuild": "fixture",
                "captureTool": "fixture",
                "processNameMatch": True,
                "modulePathMatch": True,
                "moduleSizeMatch": True,
                "moduleSha256Match": True,
                "nativeModulePathMatch": True,
                "nativeModuleSizeMatch": True,
                "nativeModuleSha256Match": True,
                "selectedGameRoot": "C:/game",
                "processName": "Endfield.exe",
                "expectedModulePath": "C:/game/GameAssembly.dll",
                "expectedModuleSize": 10,
                "expectedModuleSha256": "a" * 64,
                "expectedNativeModulePath": "C:/game/AkSoundEngine.dll",
                "expectedNativeModuleSize": 20,
                "expectedNativeModuleSha256": "b" * 64,
            }
            expected_session = {
                "game_build": "fixture",
                "selected_game_root": "C:/game",
                "expected_process_name": "Endfield.exe",
                "expected_module_path": "C:/game/GameAssembly.dll",
                "expected_module_size": 10,
                "expected_module_sha256": "a" * 64,
                "expected_native_module_path": "C:/game/AkSoundEngine.dll",
                "expected_native_module_size": 20,
                "expected_native_module_sha256": "b" * 64,
            }
            output.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.assertEqual(
                launcher.wait_for_session_start(
                    output,
                    "fixture-session",
                    100,
                    expected_game_build="fixture",
                    expected_session=expected_session,
                )["kind"],
                "session_start",
            )
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "different session"):
                launcher.wait_for_session_start(output, "other", 20, poll_ms=5, expected_game_build="fixture")
            row["moduleSha256Match"] = False
            output.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "did not emit"):
                launcher.wait_for_session_start(
                    output,
                    "fixture-session",
                    20,
                    poll_ms=5,
                    expected_game_build="fixture",
                    expected_session=expected_session,
                )

            row["expectedModuleSize"] = 11
            output.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "did not emit"):
                launcher.wait_for_session_start(
                    output,
                    "fixture-session",
                    20,
                    poll_ms=5,
                    expected_game_build="fixture",
                    expected_session=expected_session,
                )

    def test_staging_rejects_bounds_and_missing_language(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self._plan(root)
            payload = root / "payload.dll"
            payload.write_bytes(self._pe_x64())
            plan = launcher.NativeCapturePlan(
                **{**plan.__dict__, "payload": payload, "payload_sha256": launcher._sha256(payload)}
            )
            for kwargs, expected in (
                ({"heartbeat_ms": 99}, "heartbeat_ms"),
                ({"heartbeat_ms": 60001}, "heartbeat_ms"),
                ({"wait_timeout_ms": 0}, "wait_timeout_ms"),
                ({"wait_timeout_ms": 3_600_001}, "wait_timeout_ms"),
            ):
                with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                    launcher.NativeCaptureConfigurationError, expected
                ):
                    launcher.stage_session(plan, root / "bounds", **kwargs)
            plan.manifest["language"] = ""
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "language"):
                launcher.stage_session(plan, root / "language")

    def test_inject_once_is_one_call_and_stops_on_denial(self):
        payload = Path(tempfile.gettempdir()) / "fixture-capture.dll"
        payload.write_bytes(self._pe_x64())
        self.addCleanup(payload.unlink)
        calls = []

        def denied_inject(pid, path):
            calls.append((pid, path))
            raise PermissionError("access is denied")

        fake = types.SimpleNamespace(inject=denied_inject)
        with mock.patch.dict("sys.modules", {"pyinjector": fake}):
            with self.assertRaisesRegex(launcher.NativeCaptureConfigurationError, "stopped without retry"):
                launcher.inject_once(77, payload)
        self.assertEqual(calls, [(77, str(payload))])


if __name__ == "__main__":
    unittest.main()
