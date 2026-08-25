#!/usr/bin/env python3
"""Tests for Collider Start native/source golden vectors."""

from __future__ import annotations

import json
import unittest

import build_secondary_dynamics_collider_start_golden_vectors as target


class ColliderStartGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = target.build_contract()

    def test_native_source_outputs_are_bit_exact(self) -> None:
        self.assertEqual(self.payload["status"], "native_source_bit_exact")
        self.assertEqual(len(self.payload["vectors"]), len(target.CASES))
        for vector in self.payload["vectors"]:
            self.assertTrue(all(vector["nativeSourceBitExact"].values()), vector["name"])
            for name, size in target.OUTPUT_SIZES.items():
                self.assertEqual(len(bytes.fromhex(vector["outputs"][name])), size)

    def test_identity_and_physical_abi_are_pinned(self) -> None:
        identity = self.payload["identity"]
        self.assertEqual(identity["exportName"], target.EXPORT_NAME)
        self.assertEqual(identity["coreRva"], "0x243810")
        self.assertEqual(identity["coreSha256"], target.CORE_SHA256)
        self.assertEqual(identity["physicalAbi"]["pointerArguments"], 16)
        self.assertTrue(identity["physicalAbi"]["rangeIndexByValue"])
        self.assertEqual(identity["physicalAbi"]["transformPositionStrideBytes"], 12)
        self.assertEqual(identity["physicalAbi"]["workDataStrideBytes"], 184)

    def test_required_capsule_branches_are_covered(self) -> None:
        coverage = self.payload["coverage"]
        self.assertTrue(coverage["disabledBypass"])
        self.assertTrue(coverage["staticCapsule"])
        self.assertTrue(coverage["translatedMovingCapsule"])
        self.assertTrue(coverage["rotatedMovingCapsule"])
        self.assertTrue(coverage["scaledMovingCapsule"])
        self.assertEqual(coverage["directionBranches"], ["x", "y", "z"])
        self.assertTrue(coverage["reverseDirection"])
        self.assertEqual(coverage["alignedBranches"], ["centered", "one_sided"])
        self.assertEqual(coverage["radiusSeparationBranches"], ["positive", "clamped_zero"])

    def test_endminf_serialized_scope_is_bounded(self) -> None:
        scope = self.payload["endminfScope"]
        self.assertGreater(scope["capsuleCount"], 0)
        self.assertEqual(scope["directions"], [0, 2])
        self.assertEqual(scope["reverseDirections"], [0])
        self.assertEqual(scope["radiusSeparations"], [0.0, 1.0])
        self.assertEqual(scope["alignedOnCenter"], [1])

    def test_source_port_has_no_native_call_edge(self) -> None:
        names = set(target.source_port.__code__.co_names)
        self.assertNotIn("_run_native", names)
        self.assertNotIn("ctypes", names)
        self.assertFalse(self.payload["verification"]["sourceInvokesNativeHelpers"])

    def test_unity_inputs_preserve_binary32_bits(self) -> None:
        for vector in self.payload["vectors"]:
            unity = vector["unityInputs"]
            self.assertEqual(unity["flag"], vector["inputs"]["flag"])
            self.assertEqual(len(unity["sizeBits"]), 3)
            self.assertEqual(len(unity["frameRotationBits"]), 4)
            self.assertEqual(len(unity["oldRotationBits"]), 4)
            for name, values in unity.items():
                if name == "flag":
                    continue
                for bits in values if isinstance(values, list) else [values]:
                    self.assertEqual(len(bits), 8, (vector["name"], name))

    def test_work_data_layout_is_complete_and_typed(self) -> None:
        layout = self.payload["workDataLayout"]
        self.assertEqual(layout["logicalBytes"], 184)
        self.assertFalse(layout["rawBlobApi"])
        fields = layout["typedFields"]
        self.assertEqual(fields["aabbMin"], {"offset": 0, "type": "double3", "bytes": 24})
        self.assertEqual(fields["rotation"], {"offset": 168, "type": "float4", "bytes": 16})
        covered = set()
        for field in fields.values():
            covered.update(range(field["offset"], field["offset"] + field["bytes"]))
        self.assertEqual(covered, set(range(184)))

    def test_unity_port_domain_is_fail_closed(self) -> None:
        verification = self.payload["verification"]
        self.assertTrue(verification["unityPortExecuted"])
        self.assertIn("branches 2-6", verification["unityPortDomain"])
        self.assertIn("sphere/plane fail closed", verification["unityPortDomain"])

    def test_checked_in_json_matches(self) -> None:
        expected = json.dumps(self.payload, indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
