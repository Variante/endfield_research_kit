#!/usr/bin/env python3
"""Focused tests for the exact-DXBC live-report validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_diagnostic.py")
SPEC = importlib.util.spec_from_file_location("validate_diagnostic", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def passing_report() -> dict[str, object]:
    return {
        "graphics_device_type": "Direct3D11",
        "keyword": MODULE.KEYWORD,
        "vertex_sha256": MODULE.VERTEX_HASH,
        "pixel_sha256": MODULE.PIXEL_HASH,
        "native_contract_version": 2,
        "production_room_submitted": False,
        "status": "pass",
        "unarmed_callback_count": 0,
        "blocked_callback_count": 0,
        "failure_count": 0,
        "last_hresult": "0x00000000",
        "render_event_count": 2,
        "post_draw_exact_shader_objects_bound": True,
        "shader_resource_mask": "0xffffffe",
        "resource_binding_compatible": True,
        "readback_changed_from_sentinel": True,
        "callback_count": 0,
        "vertex_swap_count": 0,
        "pixel_swap_count": 0,
        "plugin_load_count": 1,
        "configure_event_count": 1,
    }


class LiveReportTests(unittest.TestCase):
    def test_plugin_contract_includes_resource_failure_exports(self) -> None:
        self.assertIn(
            "EndfieldOriginalDxbcGetShaderResourceFailureMask",
            MODULE.EXPECTED_PLUGIN_EXPORTS,
        )
        self.assertIn(
            "EndfieldOriginalDxbcGetShaderResourceFailureResult",
            MODULE.EXPECTED_PLUGIN_EXPORTS,
        )

    def test_plugin_contract_includes_fail_closed_m27_exports(self) -> None:
        for name in (
            "EndfieldOriginalDxbcGetM27MatchCount",
            "EndfieldOriginalDxbcGetM27MismatchCount",
            "EndfieldOriginalDxbcGetM27ObservedShellSha256",
            "EndfieldOriginalDxbcGetM27RegistryReady",
            "EndfieldOriginalDxbcSetM27SubstitutionArmed",
        ):
            self.assertIn(name, MODULE.EXPECTED_PLUGIN_EXPORTS)

    def test_direct_runtime_activation_report_passes_without_compiler_callback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "standalone_validation.json"
            import json

            path.write_text(json.dumps(passing_report()), encoding="utf-8")
            errors: list[str] = []
            report = MODULE.load_live(path, "standalone", errors)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(errors, [])

    def test_exact_binding_failure_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "standalone_validation.json"
            import json

            changed = passing_report()
            changed["post_draw_exact_shader_objects_bound"] = False
            path.write_text(json.dumps(changed), encoding="utf-8")
            errors: list[str] = []
            MODULE.load_live(path, "standalone", errors)
            self.assertTrue(
                any("post_draw_exact_shader_objects_bound" in error for error in errors),
                errors,
            )

    def test_missing_source_srv_mask_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "standalone_validation.json"
            import json

            changed = passing_report()
            changed["shader_resource_mask"] = "0x0"
            path.write_text(json.dumps(changed), encoding="utf-8")
            errors: list[str] = []
            MODULE.load_live(path, "standalone", errors)
            self.assertTrue(
                any("shader_resource_mask" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
