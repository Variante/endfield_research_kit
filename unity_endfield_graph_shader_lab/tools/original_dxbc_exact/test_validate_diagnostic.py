#!/usr/bin/env python3
"""Focused tests for the exact-DXBC live-report validator."""

from __future__ import annotations

import ctypes
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_diagnostic.py")
SPEC = importlib.util.spec_from_file_location("validate_diagnostic", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PLUGIN_DLL = Path(__file__).with_name("build") / "OriginalDxbcSwapPlugin.dll"
RETAINED_RESOURCE_COUNT = 26 + 9 + 2
CALLBACK = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)


class FakeUnknown(ctypes.Structure):
    pass


QUERY_INTERFACE = CALLBACK(
    ctypes.c_long, ctypes.POINTER(FakeUnknown), ctypes.c_void_p, ctypes.c_void_p
)
ADD_REF = CALLBACK(ctypes.c_ulong, ctypes.POINTER(FakeUnknown))
RELEASE = CALLBACK(ctypes.c_ulong, ctypes.POINTER(FakeUnknown))


class FakeUnknownVTable(ctypes.Structure):
    _fields_ = [
        ("query_interface", QUERY_INTERFACE),
        ("add_ref", ADD_REF),
        ("release", RELEASE),
    ]


FakeUnknown._fields_ = [
    ("vtable", ctypes.POINTER(FakeUnknownVTable)),
    ("references", ctypes.c_ulong),
    ("add_ref_calls", ctypes.c_ulong),
    ("release_calls", ctypes.c_ulong),
]


@QUERY_INTERFACE
def query_interface(_instance, _interface_id, _destination):
    return -2147467262  # E_NOINTERFACE


@ADD_REF
def add_ref(instance):
    instance.contents.references += 1
    instance.contents.add_ref_calls += 1
    return instance.contents.references


@RELEASE
def release(instance):
    instance.contents.references -= 1
    instance.contents.release_calls += 1
    return instance.contents.references


FAKE_UNKNOWN_VTABLE = FakeUnknownVTable(query_interface, add_ref, release)


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
        "shader_resource_mask": "0x3fffffe",
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

    def test_plugin_contract_includes_submission_lifetime_exports(self) -> None:
        for name in (
            "EndfieldOriginalDxbcBeginDiagnosticSubmission",
            "EndfieldOriginalDxbcCancelDiagnosticSubmission",
            "EndfieldOriginalDxbcGetCompletedDiagnosticSubmissionSerial",
        ):
            self.assertIn(name, MODULE.EXPECTED_PLUGIN_EXPORTS)


@unittest.skipUnless(
    os.name == "nt" and PLUGIN_DLL.is_file(),
    "tool-only plugin build absent",
)
class DiagnosticSubmissionAbiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = ctypes.WinDLL(str(PLUGIN_DLL))
        self.plugin.EndfieldOriginalDxbcBeginDiagnosticSubmission.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_uint32,
        ]
        self.plugin.EndfieldOriginalDxbcBeginDiagnosticSubmission.restype = (
            ctypes.c_uint64
        )
        self.plugin.EndfieldOriginalDxbcCancelDiagnosticSubmission.argtypes = [
            ctypes.c_uint64
        ]
        self.plugin.EndfieldOriginalDxbcCancelDiagnosticSubmission.restype = (
            ctypes.c_uint32
        )
        self.plugin.EndfieldOriginalDxbcGetCompletedDiagnosticSubmissionSerial.restype = (
            ctypes.c_uint64
        )
        self.plugin.EndfieldOriginalDxbcGetDiagnosticArmed.restype = ctypes.c_uint32
        self.plugin.EndfieldOriginalDxbcGetRenderEventFunc.restype = ctypes.c_void_p

        self.resource = FakeUnknown(
            ctypes.pointer(FAKE_UNKNOWN_VTABLE), 1, 0, 0
        )
        pointer = ctypes.addressof(self.resource)
        self.textures = (ctypes.c_uint64 * 26)(*([pointer] * 26))
        self.retained = (ctypes.c_uint64 * RETAINED_RESOURCE_COUNT)(
            *([pointer] * RETAINED_RESOURCE_COUNT)
        )

    def begin(self) -> int:
        return int(
            self.plugin.EndfieldOriginalDxbcBeginDiagnosticSubmission(
                self.textures, 26, self.retained, RETAINED_RESOURCE_COUNT
            )
        )

    def test_pre_arm_zero_is_not_mistaken_for_completion(self) -> None:
        serial = self.begin()
        self.assertGreater(serial, 0)
        self.assertEqual(self.resource.add_ref_calls, RETAINED_RESOURCE_COUNT)
        self.assertEqual(self.plugin.EndfieldOriginalDxbcGetDiagnosticArmed(), 0)
        self.assertLess(
            self.plugin.EndfieldOriginalDxbcGetCompletedDiagnosticSubmissionSerial(),
            serial,
        )
        self.assertEqual(self.begin(), 0, "pending pointer table must not be overwritten")

        callback_address = self.plugin.EndfieldOriginalDxbcGetRenderEventFunc()
        self.assertTrue(callback_address)
        callback = CALLBACK(None, ctypes.c_int)(callback_address)
        callback(3)
        self.assertEqual(self.plugin.EndfieldOriginalDxbcGetDiagnosticArmed(), 1)
        callback(2)

        self.assertEqual(
            self.plugin.EndfieldOriginalDxbcGetCompletedDiagnosticSubmissionSerial(),
            serial,
        )
        self.assertEqual(self.plugin.EndfieldOriginalDxbcGetDiagnosticArmed(), 0)
        self.assertEqual(self.resource.release_calls, RETAINED_RESOURCE_COUNT)
        self.assertEqual(self.resource.references, 1)

    def test_retained_resource_count_must_be_exact(self) -> None:
        for count in (RETAINED_RESOURCE_COUNT - 1, RETAINED_RESOURCE_COUNT + 1):
            with self.subTest(count=count):
                self.assertEqual(
                    self.plugin.EndfieldOriginalDxbcBeginDiagnosticSubmission(
                        self.textures, 26, self.retained, count
                    ),
                    0,
                )
        self.assertEqual(self.resource.add_ref_calls, 0)
        self.assertEqual(self.resource.release_calls, 0)
        self.assertEqual(self.resource.references, 1)

    def test_unqueued_submission_cancel_releases_and_serials_increase(self) -> None:
        first = self.begin()
        self.assertEqual(
            self.plugin.EndfieldOriginalDxbcCancelDiagnosticSubmission(first), 1
        )
        second = self.begin()
        self.assertGreater(second, first)
        self.assertEqual(
            self.plugin.EndfieldOriginalDxbcCancelDiagnosticSubmission(second), 1
        )
        self.assertEqual(
            self.plugin.EndfieldOriginalDxbcGetCompletedDiagnosticSubmissionSerial(),
            second,
        )
        self.assertEqual(
            self.resource.add_ref_calls, RETAINED_RESOURCE_COUNT * 2
        )
        self.assertEqual(
            self.resource.release_calls, RETAINED_RESOURCE_COUNT * 2
        )
        self.assertEqual(self.resource.references, 1)


class LiveReportValidationTests(unittest.TestCase):

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
