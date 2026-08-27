#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).with_name(
    "audit_endminf_uber_radial_chromatic_parameters.py"
)
SPEC = importlib.util.spec_from_file_location(
    "audit_endminf_uber_radial_chromatic_parameters", MODULE_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AuditEndminfUberRadialChromaticParametersTests(unittest.TestCase):
    def test_both_active_blends_power_and_selects_mode6(self) -> None:
        c0, c25 = MODULE.evaluate_active_lanes(
            radial_active=True,
            chromatic_active=True,
            radial_intensity=0.1,
            radial_power=2.5,
            chromatic_intensity=0.2,
            radial_average_steps=True,
            chromatic_average_step=False,
            center=(0.25, 0.75),
        )
        self.assertEqual(c0, (0.25, 0.75, 0.1, 1.75))
        self.assertEqual(c25, (6.0, 0.2, 1.0, 0.0))

    def test_mode_threshold_is_strict(self) -> None:
        _c0, c25 = MODULE.evaluate_active_lanes(
            radial_active=True,
            chromatic_active=True,
            radial_intensity=0.01,
            radial_power=3.0,
            chromatic_intensity=0.5,
            radial_average_steps=False,
            chromatic_average_step=True,
        )
        self.assertEqual(c25[0], 3.0)

    def test_single_effect_paths_keep_unscaled_intensities(self) -> None:
        radial_c0, radial_c25 = MODULE.evaluate_active_lanes(
            radial_active=True,
            chromatic_active=False,
            radial_intensity=0.4,
            radial_power=2.0,
            chromatic_intensity=0.0,
            radial_average_steps=True,
            chromatic_average_step=True,
        )
        self.assertEqual(radial_c0[2:], (0.4, 2.0))
        self.assertEqual(radial_c25, (3.0, 0.0, 1.0, 0.0))
        chroma_c0, chroma_c25 = MODULE.evaluate_active_lanes(
            radial_active=False,
            chromatic_active=True,
            radial_intensity=0.0,
            radial_power=9.0,
            chromatic_intensity=0.3,
            radial_average_steps=True,
            chromatic_average_step=True,
        )
        self.assertEqual(chroma_c0[2:], (0.0, 1.0))
        self.assertEqual(chroma_c25, (3.0, 0.3, 0.0, 1.0))

    def test_both_inactive_has_no_native_output_write(self) -> None:
        with self.assertRaisesRegex(MODULE.AuditError, "does not write"):
            MODULE.evaluate_active_lanes(
                radial_active=False,
                chromatic_active=False,
                radial_intensity=0.0,
                radial_power=1.0,
                chromatic_intensity=0.0,
                radial_average_steps=False,
                chromatic_average_step=False,
            )

    def test_instruction_landmark_fails_closed(self) -> None:
        body = bytes.fromhex("488b5340")
        MODULE.require_bytes(body, 0, bytes.fromhex("488b5340"), "field read")
        with self.assertRaisesRegex(MODULE.AuditError, "instruction drifted"):
            MODULE.require_bytes(body, 0, bytes.fromhex("488b5348"), "field read")

    def test_whole_body_hash_fails_closed_before_decoding(self) -> None:
        body = bytes(MODULE.METHOD_SIZE)
        with self.assertRaisesRegex(MODULE.AuditError, "body SHA-256 drifted"):
            MODULE.decode_body_contract(body, lambda _va, count: bytes(count))

    def test_native_input_gate_fails_closed(self) -> None:
        gate = SimpleNamespace(validated=False, detail="hash mismatch")
        with self.assertRaisesRegex(MODULE.AuditError, "pinned native input gate"):
            MODULE.build(gate)

    def test_rip_scalar_decoder_uses_signed_displacement(self) -> None:
        method_va = 0x1000
        prefix = bytes.fromhex("f30f100d")
        target = 0x0FF0
        size = len(prefix) + 4
        displacement = target - (method_va + size)
        body = prefix + struct.pack("<i", displacement)

        def read_va(va: int, count: int) -> bytes:
            self.assertEqual((va, count), (target, 4))
            return struct.pack("<f", 2.0)

        value, source = MODULE.decode_rip_scalar(
            body, method_va, 0, prefix, "<f", read_va, "test"
        )
        self.assertEqual(value, 2.0)
        self.assertEqual(source, target)


if __name__ == "__main__":
    unittest.main()
