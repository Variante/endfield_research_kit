#!/usr/bin/env python3
"""Focused tests for the recovered retail punctual-light cap validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_light_cull_cap.py")
SPEC = importlib.util.spec_from_file_location("audit_light_cull_cap", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class LightCullCapAuditTests(unittest.TestCase):
    def write_fixture(
        self,
        root: Path,
        *,
        desktop_cap: int = 256,
        common_cap: int | None = None,
    ) -> None:
        contents = {
            "SettingFiles": "\n".join(AUDIT.EXPECTED_SETTING_FILES) + "\n",
            "HGRenderPipelineSettings": "\n\n".join(
                (
                    "[IncludeSettings]"
                    if route == "Common"
                    else f"[IncludeSettings@{route}]"
                )
                + f"\nincludeSettings = {file_name}"
                for route, file_name in AUDIT.EXPECTED_INCLUDE_ROUTES.items()
            )
            + "\n",
            "CommonSettings": (
                "[Lighting@1000]\n"
                + (
                    f"PunctualLightMaxCount = {common_cap}\n"
                    if common_cap is not None
                    else "OtherValue = 1\n"
                )
            ),
            "DesktopSettings": (
                "[Lighting@1000]\n"
                f"PunctualLightMaxCount = {desktop_cap}\n"
            ),
            "CloudDesktopOverride": "[Streaming@1000]\nchunkLoadRadius = 128\n",
            "ConsoleSettings": "[Lighting@1000]\nPunctualLightMaxCount = 256\n",
            "MobileSettings": "[Lighting@1000]\nPunctualLightMaxCount = 32\n",
            "CinematicSettings": "[Lighting@1000]\nOtherValue = 1\n",
        }
        for logical_name, (file_name, _, _) in AUDIT.TEXT_ASSETS.items():
            (root / file_name).write_text(
                contents[logical_name], encoding="utf-8"
            )

    def test_successful_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root)
            _, caps = AUDIT.validate_settings_payloads(
                root, verify_hashes=False
            )
            self.assertEqual(caps, AUDIT.EXPECTED_CAP_DEFINITIONS)

    def test_wrong_desktop_cap_reports_expected_and_actual(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root, desktop_cap=128)
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=cap_definitions;.*"
                r"DesktopSettings.*128",
            ):
                AUDIT.validate_settings_payloads(root, verify_hashes=False)

    def test_unexpected_common_override_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            self.write_fixture(root, common_cap=64)
            with self.assertRaisesRegex(
                AssertionError,
                r"validator=light_cull_cap; check=cap_definitions;.*"
                r"CommonSettings.*64",
            ):
                AUDIT.validate_settings_payloads(root, verify_hashes=False)


if __name__ == "__main__":
    unittest.main()
