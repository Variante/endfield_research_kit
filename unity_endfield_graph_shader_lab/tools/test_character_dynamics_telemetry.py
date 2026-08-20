#!/usr/bin/env python3
"""Contract tests for the read-only retail character telemetry probe."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import character_dynamics_telemetry as telemetry  # noqa: E402


class CharacterDynamicsTelemetryTests(unittest.TestCase):
    def test_manifest_is_pinned_and_contains_priority_targets(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        self.assertEqual(manifest["schema"], "characterDynamicsTelemetry.hooks.v1")
        self.assertEqual(manifest["gameBuild"], "endfield-2026-07-11-gameassembly-0c557367")
        self.assertEqual(manifest["files"]["gameAssembly"]["sha256"], "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce")
        self.assertEqual(manifest["files"]["metadata"]["sha256"], "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e")
        self.assertEqual(set(("endminf-overview", "pelica-overview", "chen-overview")), set(manifest["targets"]))
        self.assertEqual(manifest["targets"]["endminf-overview"]["identityStatus"], "unresolved_endminf_alias")
        self.assertEqual(manifest["targets"]["chen-overview"]["loopStartSeconds"], 204.55)

    def test_all_native_hooks_have_rva_and_expected_bytes(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        expected = {
            "clothUpdate": ("0x2f918a0", "488bc448894808535657415441554156"),
            "transformWriteback": ("0x672641c", "488bc448895808488970104889781855"),
            "transformRead": ("0x3b127d0", "48895c2410488974241848897c242055"),
            "animatorBufferWriteback": ("0x6726158", "488bc44889580848897010488978184c"),
            "charUiAnimatorMove": ("0x6c2abd0", "48895c2408574883ec60488bfa0f2974"),
            "charUiTick": ("0x6c29344", "40534883ec30488bd90f29742420b901"),
        }
        for name, (rva, bytes_hex) in expected.items():
            self.assertEqual(manifest["hooks"][name]["rva"], rva)
            self.assertEqual(manifest["hooks"][name]["expectedBytes"], bytes_hex)

    def test_rendered_agent_has_no_placeholder_or_game_write_api(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        rendered = telemetry.render_agent_source(telemetry.DEFAULT_AGENT, manifest)
        self.assertNotIn(telemetry.AGENT_PLACEHOLDER, rendered)
        self.assertIn("Interceptor.attach", rendered)
        self.assertIn("readByteArray", rendered)
        for forbidden in ("writeByteArray", "Memory.patchCode", "NativeFunction", "send({ channel: \"write\""):
            self.assertNotIn(forbidden, rendered)

    def test_unknown_target_is_rejected_before_attach(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(telemetry.core, "verify_game_files", return_value={}):
                result = telemetry.main(["--target", "missing", "--check-only", "--game-root", str(root)])
        self.assertEqual(result, 1)

    def test_check_only_does_not_load_frida_or_attach(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(telemetry.core, "verify_game_files", return_value={"gameAssembly": Path(temp) / "GameAssembly.dll"}):
                with patch.object(telemetry.core, "load_frida", side_effect=AssertionError("check-only attached")):
                    self.assertEqual(
                        telemetry.main(["--target", "chen-overview", "--check-only", "--game-root", temp]),
                        0,
                    )

    def test_capture_config_is_bounded(self) -> None:
        manifest = telemetry.load_manifest(telemetry.DEFAULT_MANIFEST)
        capture = manifest["capture"]
        self.assertLessEqual(capture["maxEvents"], 50000)
        self.assertLessEqual(capture["readBytesPerPointer"], 16)
        self.assertLessEqual(capture["maxPointerReadsPerEvent"], 2)
        self.assertEqual(capture["snapshotRegisters"], ["rcx", "r8"])
        self.assertTrue(manifest["evidenceBoundary"]["nonClaims"])


if __name__ == "__main__":
    unittest.main()
