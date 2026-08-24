#!/usr/bin/env python3
"""Focused tests for the secondary-dynamics proxy-array layout contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_proxy_layout_contract as builder


class SecondaryDynamicsProxyLayoutTests(unittest.TestCase):
    def test_published_contract_reconstructs(self) -> None:
        observed = builder.build_contract()
        published = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(observed, published)
        self.assertEqual(published["serializedSlotCount"], 35)
        self.assertEqual(published["nestedTransformSlotCount"], 3)
        self.assertFalse(published["secondaryDynamicsVerified"])
        self.assertFalse(published["solverImplemented"])
        self.assertFalse(published["retailEquivalent"])

    def test_serializer_methods_use_authoritative_pointer_spans(self) -> None:
        methods = builder.build_contract()["serializerMethods"]
        self.assertEqual(
            (methods["serialize"]["va"], methods["serialize"]["endVa"],
             methods["serialize"]["spanBytes"], methods["serialize"]["bodySha256"]),
            ("0x1866be154", "0x1866beb44", 0x9F0,
             "fb553ce505afefa75eb06817016c5f1c244d1af4eb9d4fde8ef7d041f67fd166"),
        )
        self.assertEqual(
            (methods["deserialize"]["va"], methods["deserialize"]["endVa"],
             methods["deserialize"]["spanBytes"], methods["deserialize"]["bodySha256"]),
            ("0x183e8fe60", "0x183e90a00", 0xBA0,
             "283daa75da452fdda631e2608af23a7b1e1f143c9eadb128ae30257ebfa8eeae"),
        )
        self.assertEqual(methods["serialize"]["ifixBoundary"]["patchId"], "0x555")
        self.assertEqual(methods["deserialize"]["ifixBoundary"]["patchId"], "0x60")
        self.assertEqual(
            methods["deserialize"]["ifixBoundary"]["status"],
            "patch_activity_and_target_unproven",
        )
        transform_methods = builder.build_contract()["transformSerializerMethods"]
        self.assertEqual(
            (transform_methods["serialize"]["spanBytes"],
             transform_methods["deserialize"]["spanBytes"]),
            (0x1B4, 0x3E0),
        )
        self.assertEqual(transform_methods["serialize"]["ifixBoundary"]["patchId"], "0x49a")
        self.assertEqual(transform_methods["deserialize"]["ifixBoundary"]["patchId"], "0x61")

    def test_all_slots_have_exact_unpatched_bidirectional_assignments(self) -> None:
        layouts = builder.build_contract()["serializedLayouts"]
        self.assertEqual(len(layouts), 35)
        self.assertTrue(all(
            row["mappingEvidence"]["classification"] ==
            "exact_unpatched_native_assignment"
            for row in layouts.values()
        ))
        self.assertEqual(
            layouts["referenceIndices"]["mappingEvidence"]["operation"],
            "ExSimpleNativeArray.Serialize/Deserialize",
        )
        self.assertEqual(
            layouts["vertexBindPosePositions"]["mappingEvidence"]["operation"],
            "NativeArrayExtensions.MC2ToRawBytes/MC2FromRawBytes",
        )
        self.assertEqual(
            layouts["edgeToTrianglesKeys"]["mappingEvidence"]["operation"],
            "NativeMultiHashMapExtensions.MC2Serialize/MC2Deserialize",
        )
        self.assertEqual(
            layouts["centerFixedList"]["mappingEvidence"]["operation"],
            "DataUtility.ArrayCopy",
        )
        self.assertEqual(
            (layouts["edgeToTrianglesKeys"]["runtimeFieldOffset"],
             layouts["edgeToTrianglesKeys"]["serializedFieldOffset"],
             layouts["edgeToTrianglesValues"]["serializedFieldOffset"]),
            ("0x1e0", "0x198", "0x1a0"),
        )

    def test_nested_transform_arrays_have_exact_native_layouts_and_assignments(self) -> None:
        layouts = builder.build_contract()["nestedTransformLayouts"]
        self.assertEqual(
            {
                name: (row["elementType"], row["strideBytes"], row["serializedEncoding"])
                for name, row in layouts.items()
            },
            {
                "transformData.flagArray":
                    ("BeyondDynamicBone.ExBitFlag8", 1, "serialization_data"),
                "transformData.initLocalPositionArray":
                    ("Unity.Mathematics.float3", 12, "serialization_data"),
                "transformData.initLocalRotationArray":
                    ("Unity.Mathematics.quaternion", 16, "serialization_data"),
            },
        )
        self.assertTrue(all(
            row["mappingEvidence"]["classification"] ==
            "exact_unpatched_native_assignment"
            for row in layouts.values()
        ))

    def test_high_value_layouts_are_native_proven(self) -> None:
        layouts = builder.build_contract()["serializedLayouts"]
        expected = {
            "vertexToTriangles": ("Unity.Collections.FixedList32Bytes`1<System.UInt32>", 32, "opaque"),
            "vertexToVertexIndexArray": ("System.UInt32", 4, "uint32"),
            "vertexToVertexDataArray": ("System.UInt16", 2, "uint16"),
            "edges": ("Unity.Mathematics.int2", 8, "int2"),
            "vertexBindPosePositions": ("Unity.Mathematics.float3", 12, "float3"),
            "vertexBindPoseRotations": ("Unity.Mathematics.quaternion", 16, "float4"),
            "customSkinningBoneIndices": ("System.Int32", 4, "int32"),
            "centerFixedList": ("System.UInt16", 2, "uint16"),
        }
        for name, row in expected.items():
            self.assertEqual(
                (layouts[name]["elementType"], layouts[name]["strideBytes"], layouts[name]["decodeKind"]),
                row,
            )

    def test_hash_map_storage_split_uses_key_and_value_arguments(self) -> None:
        layouts = builder.build_contract()["serializedLayouts"]
        keys = layouts["edgeToTrianglesKeys"]
        values = layouts["edgeToTrianglesValues"]
        self.assertEqual(keys["field"], "edgeToTrianglesKeys")
        self.assertEqual(values["field"], "edgeToTrianglesValues")
        self.assertEqual(keys["runtimeField"], "edgeToTriangles")
        self.assertEqual(values["runtimeField"], "edgeToTriangles")
        self.assertEqual((keys["elementType"], keys["strideBytes"]),
                         ("Unity.Mathematics.int2", 8))
        self.assertEqual((values["elementType"], values["strideBytes"]),
                         ("System.UInt16", 2))
        self.assertEqual(keys["serializedEncoding"], "element_value_list")
        self.assertEqual(values["serializedEncoding"], "element_value_list")
        self.assertEqual(layouts["centerFixedList"]["serializedEncoding"],
                         "element_value_list")
        self.assertEqual(layouts["vertexToTriangles"]["serializedEncoding"],
                         "raw_byte_list")
        fixed = layouts["vertexToTriangles"]["strideEvidence"]
        self.assertEqual(fixed["basis"], "fixed_list_structural_fields")
        self.assertEqual(
            [(row["type"], row["nativeSizeBytes"]) for row in fixed["fields"]],
            [("System.UInt16", 2), ("Unity.Collections.FixedBytes30", 30)],
        )

    def test_declaration_drift_fails_closed(self) -> None:
        drifted = list(builder.LAYOUT_SPECS)
        row = list(drifted[0])
        row[2] = -1
        drifted[0] = tuple(row)
        with patch.object(builder, "LAYOUT_SPECS", tuple(drifted)):
            with self.assertRaisesRegex(builder.ContractError, "type drift"):
                builder.build_contract()


if __name__ == "__main__":
    unittest.main()
