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
        self.assertFalse(published["secondaryDynamicsVerified"])
        self.assertFalse(published["solverImplemented"])
        self.assertFalse(published["retailEquivalent"])

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
