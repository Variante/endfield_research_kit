from __future__ import annotations

import importlib.util
import json
import copy
import sys
import tempfile
import unittest
from pathlib import Path


HERE = __import__("pathlib").Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_liteffect_resource_mapping.py"
SPEC = importlib.util.spec_from_file_location("verify_endminf_liteffect_resource_mapping", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LitEffectResourceMappingTests(unittest.TestCase):
    def test_mesh_probe_evidence_is_pinned_and_fail_closed(self) -> None:
        probe = HERE / "verify_endminf_liteffect_mesh_probe.py"
        spec = importlib.util.spec_from_file_location("mesh_probe", probe)
        assert spec and spec.loader
        mesh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mesh)
        report = HERE.parent / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "ExternalUiEffects" / "endminf_liteffect_mesh_probe_evidence.json"
        evidence = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(evidence["mesh"]["sha256"], mesh.EXPECTED["sha256"])
        self.assertIsNone(evidence["channels"]["COLOR"])
        with self.assertRaises(RuntimeError):
            mesh.verify(HERE / "does-not-exist.json")
        report = HERE.parent / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "ExternalUiEffects" / "endminf_liteffect_mesh_probe_evidence.json"
        base = json.loads(report.read_text(encoding="utf-8"))
        for section, key, value in (("mesh", "name", "wrong"), ("mesh", "pathID", 1), ("mesh", "containerOffset", 1), ("mesh", "sha256", "00"), ("mesh", "vertexCount", 1), ("channels", "POSITION3", 1), ("channels", "UV2_UV7", []), ("source", "offset", 1), ("source", "pathID", 1)):
            mutated = copy.deepcopy(base); mutated[section][key] = value
            with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
                json.dump(mutated, f); name = f.name
            try:
                with self.assertRaises(RuntimeError): mesh.verify_report(Path(name))
            finally:
                Path(name).unlink()
        for wording in ("One exact Mesh in the LitEffect material closure; proves complete shader BindChannels.", "One exact Mesh in the LitEffect material closure."):
            mutated = copy.deepcopy(base); mutated["scope"] = wording
            with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
                json.dump(mutated, f); name = f.name
            try:
                with self.assertRaises(RuntimeError): mesh.verify_report(Path(name))
            finally:
                Path(name).unlink()

    def test_representative_contract_is_reflected_without_rdef(self) -> None:
        report = MODULE.build_report()
        self.assertEqual(
            report["status"],
            "verified_with_selected_variant_material_offsets_and_consumer_gaps",
        )
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
        self.assertEqual(vertex[2]["logicalName"], "UnityPerDraw")
        self.assertEqual(fragment[3]["logicalName"], "UnityPerMaterial")
        self.assertEqual(fragment[4]["logicalName"], "_TerrainSubsurfaceConstants")
        fields = {row["name"]: row for row in report["constantBuffers"]["serializedFields"]}
        self.assertEqual((fields["_NonJitteredViewNoTransProjMatrix"]["register"], fields["_NonJitteredViewNoTransProjMatrix"]["offsetBytes"], fields["_NonJitteredViewNoTransProjMatrix"]["sizeBytes"]), (0, 512, 64))
        self.assertEqual((fields["_GlobalMipBias"]["register"], fields["_GlobalMipBias"]["registerOffsetBytes"]), (None, None))
        self.assertIsNone(fields["_TerrainSubsurfaceProfileInt"]["register"])

    def test_selected_variant_material_offsets_are_exact_and_bounded(self) -> None:
        report = MODULE.build_report()
        rows = {
            row["property"]: row
            for row in report["constantBuffers"]["materialConstantBufferFields"]
        }
        for name, (offset, size) in MODULE.EXPECTED_SELECTED_PARALLAX_FIELDS.items():
            self.assertEqual(rows[name]["register"], 3)
            self.assertEqual(rows[name]["offsetBytes"], offset)
            self.assertEqual(rows[name]["sizeBytes"], size)
            self.assertEqual(rows[name]["status"], "resolved_selected_variant_offset")
            self.assertLessEqual(offset + size, 496)
        self.assertEqual(
            rows["_EnableParallaxMap"]["status"],
            "selected_variant_offset_absent",
        )
        self.assertIsNone(rows["_EnableParallaxMap"]["offsetBytes"])

    def test_selected_variant_material_offset_attack_fails_closed(self) -> None:
        original = MODULE._compact_metadata

        def altered(path: Path):
            value = original(path)
            if path.name.startswith("0115_"):
                table = next(
                    row for row in value["constantBuffers"]
                    if row["Name"] == "UnityPerMaterial"
                )
                field = next(
                    row for row in table["VectorParameters"]
                    if row["Name"] == "_ParallaxColor"
                )
                field["Index"] = 448
            return value

        MODULE._compact_metadata = altered
        try:
            with self.assertRaisesRegex(
                MODULE.VerificationError, "parallax field map drifted"
            ):
                MODULE.build_report()
        finally:
            MODULE._compact_metadata = original

    def test_malformed_dxbc_chunk_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "DXBC chunk table"):
            MODULE._chunks(b"DXBC" + b"\0" * 24 + (99).to_bytes(4, "little"))

    def test_bind_channels_gap_is_explicit(self) -> None:
        report = MODULE.build_report()
        self.assertEqual(report["bindChannels"]["status"], "gap")
        self.assertIn("ParserBindChannels", report["bindChannels"]["reason"])

    def test_texture_register_attack_fails_closed(self) -> None:
        original = MODULE._ruri_declarations
        def altered(path: Path):
            value = original(path)
            if path.name == "parallax_hgbuffer_fragment.hlsl":
                value["resources"][0]["register"] = 6
            return value
        MODULE._ruri_declarations = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "texture registers"):
                MODULE.build_report()
        finally:
            MODULE._ruri_declarations = original

    def test_sampler_declaration_attack_fails_closed(self) -> None:
        original = MODULE._ruri_declarations
        def altered(path: Path):
            value = original(path)
            if path.name == "parallax_hgbuffer_fragment.hlsl":
                value["samplers"][0]["name"] = "sampler_Tampered"
            return value
        MODULE._ruri_declarations = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "sampler declarations"):
                MODULE.build_report()
        finally:
            MODULE._ruri_declarations = original

    def test_descriptor_name_attack_fails_closed(self) -> None:
        original = MODULE._compact_metadata
        def altered(path: Path):
            value = original(path)
            if path.name.startswith("0115_"):
                value["descriptorSets"][1]["Bindings"][8]["Name"] = "_TamperedMap"
            return value
        MODULE._compact_metadata = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "PerMaterial descriptor"):
                MODULE.build_report()
        finally:
            MODULE._compact_metadata = original

    def test_ruri_hash_attack_fails_closed(self) -> None:
        original = MODULE._sha256
        def altered(path: Path):
            return "0" * 64 if path.suffix == ".hlsl" else original(path)
        MODULE._sha256 = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "Ruri output hash"):
                MODULE.build_report()
        finally:
            MODULE._sha256 = original

    def test_default_verify_rejects_stale_durable_report(self) -> None:
        original = MODULE.REPORT_PATH
        with tempfile.TemporaryDirectory() as temp:
            MODULE.REPORT_PATH = Path(temp) / "report.json"
            MODULE.REPORT_PATH.write_text(json.dumps({"schema": "stale"}), encoding="utf-8")
            try:
                with self.assertRaisesRegex(MODULE.VerificationError, "durable report is stale"):
                    MODULE.verify()
            finally:
                MODULE.REPORT_PATH = original

    def test_material_closure_fileid_attack_fails_closed(self) -> None:
        original = MODULE._texture_identity_map
        def altered():
            value = original()
            value[-2770956563882859728] = copy.deepcopy(value[-2770956563882859728])
            value[-2770956563882859728]["occurrences"][0]["fileId"] = 99
            return value
        MODULE._texture_identity_map = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "closure material artifact/PathID/fileId"):
                MODULE.build_report()
        finally:
            MODULE._texture_identity_map = original

    def test_representative_stage_attack_fails_closed(self) -> None:
        original = MODULE._read_json
        def altered(path: Path):
            value = original(path)
            if path == MODULE.EVIDENCE_PATH:
                value = copy.deepcopy(value)
                value["target"]["representatives"][1]["stage"] = "vertex"
            return value
        MODULE._read_json = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "stage/decodedStage"):
                MODULE.build_report()
        finally:
            MODULE._read_json = original

    def test_swapped_metadata_attack_fails_closed(self) -> None:
        original = MODULE._compact_metadata
        def altered(path: Path):
            value = original(path)
            if path.name.startswith("0115_"):
                value["decodedStage"] = "vertex"
            return value
        MODULE._compact_metadata = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "metadata decodedStage"):
                MODULE.build_report()
        finally:
            MODULE._compact_metadata = original

    def test_ruri_wrong_resource_name_attack_fails_closed(self) -> None:
        original = MODULE._ruri_declarations
        def altered(path: Path):
            value = original(path)
            if path.name == "parallax_hgbuffer_fragment.hlsl":
                value["resources"][0]["name"] = "WRONG_RESOURCE"
            return value
        MODULE._ruri_declarations = altered
        try:
            with self.assertRaisesRegex(MODULE.VerificationError, "resource name mismatch"):
                MODULE.build_report()
        finally:
            MODULE._ruri_declarations = original


if __name__ == "__main__":
    unittest.main()
