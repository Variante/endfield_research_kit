#!/usr/bin/env python3
"""Contract tests for the bounded Burst resolver runtime probe."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import burst_resolver_telemetry as telemetry  # noqa: E402


class BurstResolverTelemetryTests(unittest.TestCase):
    def test_manifest_pins_three_native_files_and_exact_modules(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        self.assertEqual(manifest["schema"], "burstResolverTelemetry.hooks.v1")
        self.assertEqual(manifest["moduleName"], "GameAssembly.dll")
        self.assertEqual(manifest["kernel32ModuleName"], "kernel32.dll")
        self.assertEqual(manifest["resolverModuleName"], "lib_burst_generated.dll")
        self.assertEqual(set(manifest["files"]), {"executable", "gameAssembly", "metadata"})
        self.assertEqual(manifest["files"]["gameAssembly"]["sha256"], "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce")
        self.assertEqual(manifest["files"]["metadata"]["sha256"], "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e")

    def test_rendered_agent_is_observation_only_and_has_required_apis(self) -> None:
        rendered = telemetry.render_agent_source(
            telemetry.DEFAULT_AGENT,
            telemetry.load_manifest(telemetry.DEFAULT_MANIFEST),
        )
        self.assertNotIn(telemetry.AGENT_PLACEHOLDER, rendered)
        self.assertIn("LoadLibraryW", rendered)
        self.assertIn("GetProcAddress", rendered)
        self.assertIn("gameAssemblyCallerBacktrace", rendered)
        self.assertIn("readAnsiString", rendered)
        self.assertIn("loadlibrary_path_unterminated", rendered)
        identity = rendered.index('setResolverIdentity(retval, module ? module.path : this.requestedPath, "loadlibraryw")')
        capture_guard = rendered.index("if (!captureEnabled) return;", identity)
        self.assertLess(identity, capture_guard)
        for forbidden in ("writeByteArray", "Memory.patchCode", "NativeFunction", "send({ channel: \"write\""):
            self.assertNotIn(forbidden, rendered)
        self.assertIn("pointer.isNull()", rendered)
        self.assertIn('type: "null"', rendered)

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
                    return_value={"gameAssembly": root / "GameAssembly.dll"},
                ):
                    with patch.object(telemetry.core, "load_frida", side_effect=AssertionError("attach ran")):
                        self.assertEqual(
                            telemetry.main(["--check-only", "--game-root", str(root)]),
                            0,
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
