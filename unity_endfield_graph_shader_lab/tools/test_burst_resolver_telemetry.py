#!/usr/bin/env python3
"""Contract tests for the bounded Burst resolver runtime probe."""
from __future__ import annotations

import sys
import tempfile
import unittest
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import burst_resolver_telemetry as telemetry  # noqa: E402


class BurstResolverTelemetryTests(unittest.TestCase):
    def test_manifest_pins_four_hash_pinned_files_and_exact_modules(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        self.assertEqual(manifest["schema"], "burstResolverTelemetry.hooks.v1")
        self.assertEqual(manifest["moduleName"], "GameAssembly.dll")
        self.assertEqual(manifest["kernel32ModuleName"], "kernel32.dll")
        self.assertEqual(manifest["resolverModuleName"], "lib_burst_generated.dll")
        self.assertEqual(set(manifest["files"]), {"executable", "gameAssembly", "metadata", "resolver"})
        self.assertEqual(manifest["files"]["gameAssembly"]["sha256"], "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce")
        self.assertEqual(manifest["files"]["metadata"]["sha256"], "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e")
        self.assertEqual(manifest["files"]["resolver"]["sha256"], "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99")
        self.assertEqual({target["id"] for target in manifest["targets"]}, telemetry.TARGET_IDS)
        self.assertEqual(len(manifest["targets"]), 5)
        by_id = {target["id"]: target for target in manifest["targets"]}
        self.assertEqual(by_id["collider_start_simulation_step_range_kernel"]["methodIndex"], 385394)
        self.assertEqual(by_id["collider_end_simulation_step_range_kernel"]["methodIndex"], 385295)
        self.assertEqual(by_id["collider_start_simulation_step_range_kernel"]["windows"][-1], {
            "role": "invoke", "methodIndex": 385416,
            "startOffset": "0x6762cc0", "endOffsetExclusive": "0x6762edc",
        })
        self.assertEqual(by_id["collider_end_simulation_step_range_kernel"]["windows"][-1], {
            "role": "invoke", "methodIndex": 385317,
            "startOffset": "0x675b0cc", "endOffsetExclusive": "0x675b1d4",
        })
        for target in manifest["targets"]:
            self.assertEqual(
                {window["role"] for window in target["windows"]},
                telemetry.TARGET_WINDOW_ROLES,
            )
            self.assertEqual(
                target["callTargetProbe"]["getFunctionPointerOffset"],
                next(window for window in target["windows"] if window["role"] == "get_function_pointer")["startOffset"],
            )

    def test_rendered_agent_is_observation_only_and_has_required_apis(self) -> None:
        rendered = telemetry.render_agent_source(
            telemetry.DEFAULT_AGENT,
            telemetry.load_manifest(telemetry.DEFAULT_MANIFEST),
        )
        self.assertNotIn(telemetry.AGENT_PLACEHOLDER, rendered)
        self.assertIn("LoadLibraryW", rendered)
        self.assertIn("GetProcAddress", rendered)
        self.assertIn("gameAssemblyCallerBacktrace", rendered)
        self.assertIn("callerBacktrace", rendered)
        self.assertIn("targetWindowMatches", rendered)
        self.assertIn("resolvedExportName", rendered)
        self.assertIn("burst_function_pointer", rendered)
        self.assertIn("callTargetHooks", rendered)
        self.assertIn("getFunctionPointerOffset", rendered)
        self.assertIn("readAnsiString", rendered)
        self.assertIn("loadlibrary_path_unterminated", rendered)
        identity = rendered.index('setResolverIdentity(retval, module ? module.path : this.requestedPath, "loadlibraryw")')
        capture_guard = rendered.index("if (!captureEnabled) return;", identity)
        self.assertLess(identity, capture_guard)
        for forbidden in ("writeByteArray", "Memory.patchCode", "NativeFunction", "send({ channel: \"write\""):
            self.assertNotIn(forbidden, rendered)
        self.assertIn("pointer.isNull()", rendered)
        self.assertIn('type: "null"', rendered)

    def test_manifest_rejects_target_window_drift(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        manifest["targets"][-1]["windows"][-1]["endOffsetExclusive"] = "0x675b1d5"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(telemetry.CaptureConfigurationError, "target windows drifted"):
                telemetry.load_manifest(path)

    def test_check_only_does_not_load_frida_or_attach(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            native = SimpleNamespace(
                validated=True,
                status="validated",
                detail="",
                gameassembly=root / "GameAssembly.dll",
                metadata=root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
            )
            with patch.object(telemetry, "check_installed_native_inputs", return_value=native):
                with patch.object(
                    telemetry.core,
                    "verify_game_files",
                    return_value={
                        "gameAssembly": root / "GameAssembly.dll",
                        "resolver": root / "Endfield_Data/Plugins/x86_64/lib_burst_generated.dll",
                    },
                ):
                    with patch.object(telemetry, "verify_call_target_probes") as probe_gate:
                        with patch.object(telemetry.core, "load_frida", side_effect=AssertionError("attach ran")):
                            self.assertEqual(
                                telemetry.main(["--check-only", "--game-root", str(root)]),
                                0,
                            )
                    probe_gate.assert_called_once()

    def test_resolver_handshake_rejects_path_or_size_drift(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        expected = Path("D:/Program Files/Endfield Game/Endfield_Data/Plugins/x86_64/lib_burst_generated.dll")
        identity = {
            "status": "already_loaded",
            "name": expected.name,
            "path": str(expected),
            "size": manifest["files"]["resolver"]["bytes"],
            "base": "0x5000",
            "moduleBase": "0x5000",
        }
        telemetry.validate_resolver_handshake(
            {"resolverModuleIdentity": identity, "resolverExportMap": []},
            expected,
            manifest["files"]["resolver"]["bytes"],
            {"hashedCount": 0, "canonicalNameRvaSha256": hashlib.sha256(b"\n").hexdigest()},
        )
        identity["path"] = "D:/other/lib_burst_generated.dll"
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            telemetry.validate_resolver_handshake(
                {"resolverModuleIdentity": identity, "resolverExportMap": []},
                expected,
                manifest["files"]["resolver"]["bytes"],
                {"hashedCount": 0, "canonicalNameRvaSha256": hashlib.sha256(b"\n").hexdigest()},
            )

    def test_native_gate_mismatch_refuses_before_executable_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            native = SimpleNamespace(
                validated=False,
                status="mismatched",
                detail="GameAssembly.dll is a different build",
                gameassembly=Path(temp) / "GameAssembly.dll",
                metadata=Path(temp) / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
            )
            with patch.object(telemetry, "check_installed_native_inputs", return_value=native):
                with patch.object(telemetry.core, "verify_game_files", side_effect=AssertionError("wrong gate order")):
                    self.assertEqual(
                        telemetry.main(["--check-only", "--game-root", temp]),
                        1,
                    )


if __name__ == "__main__":
    unittest.main()
