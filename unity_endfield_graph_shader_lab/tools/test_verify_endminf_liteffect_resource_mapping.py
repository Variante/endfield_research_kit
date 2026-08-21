from __future__ import annotations

import importlib.util
import sys
import unittest


HERE = __import__("pathlib").Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_liteffect_resource_mapping.py"
SPEC = importlib.util.spec_from_file_location("verify_endminf_liteffect_resource_mapping", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LitEffectResourceMappingTests(unittest.TestCase):
    def test_representative_contract_is_reflected_without_rdef(self) -> None:
        report = MODULE.build_report()
        self.assertEqual(report["status"], "verified_with_gaps")
        self.assertFalse(report["reflection"]["vertex"]["hasRdef"])
        self.assertFalse(report["reflection"]["fragment"]["hasRdef"])
        self.assertEqual(len(report["vertexInputs"]), 9)
        self.assertEqual(len(report["mrtOutputs"]), 5)
        self.assertEqual([row["semantic"] for row in report["mrtOutputs"]], ["SV_Target"] * 5)

    def test_material_texture_gaps_are_not_filled(self) -> None:
        report = MODULE.build_report()
        for material in report["materials"]:
            rows = {row["property"]: row for row in material["textures"]}
            self.assertEqual(rows["_ParallaxMap"]["status"], "resolved")
            self.assertEqual(rows["_NormalMap"]["status"], "resolved")
            self.assertEqual(rows["_MROMap"]["status"], "resolved")
            self.assertEqual(rows["_BaseColorMap"]["status"], "resolved")
            self.assertEqual(rows["_ParallaxNoiseMap"]["status"], "gap")
            self.assertEqual(rows["_ParallaxMaskMap"]["status"], "gap")

    def test_constant_buffer_sizes_and_known_fields(self) -> None:
        report = MODULE.build_report()
        vertex = {row["register"]: row for row in report["constantBuffers"]["vertex"]}
        fragment = {row["register"]: row for row in report["constantBuffers"]["fragment"]}
        self.assertEqual({register: row["sizeBytes"] for register, row in vertex.items()}, {0: 1312, 1: 320, 2: 176})
        self.assertEqual({register: row["sizeBytes"] for register, row in fragment.items()}, {0: 720, 1: 1696, 2: 80, 3: 496, 4: 16})
        fields = {row["name"]: row for row in report["constantBuffers"]["serializedFields"]}
        self.assertEqual((fields["_NonJitteredViewNoTransProjMatrix"]["register"], fields["_NonJitteredViewNoTransProjMatrix"]["offsetBytes"], fields["_NonJitteredViewNoTransProjMatrix"]["sizeBytes"]), (0, 512, 64))
        self.assertEqual((fields["_GlobalMipBias"]["register"], fields["_GlobalMipBias"]["registerOffsetBytes"]), (2, 96))
        self.assertIsNone(fields["_TerrainSubsurfaceProfileInt"]["register"])

    def test_malformed_dxbc_chunk_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "DXBC chunk table"):
            MODULE._chunks(b"DXBC" + b"\0" * 24 + (99).to_bytes(4, "little"))

    def test_bind_channels_gap_is_explicit(self) -> None:
        report = MODULE.build_report()
        self.assertEqual(report["bindChannels"]["status"], "gap")
        self.assertIn("ParserBindChannels", report["bindChannels"]["reason"])


if __name__ == "__main__":
    unittest.main()
