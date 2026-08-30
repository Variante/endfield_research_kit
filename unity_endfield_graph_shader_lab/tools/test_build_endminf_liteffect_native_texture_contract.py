#!/usr/bin/env python3
"""Focused fail-closed tests for Endminf LitEffect native texture transport."""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "build_endminf_liteffect_native_texture_contract.py"
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_liteffect_native_texture_contract", MODULE_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EndminfLitEffectNativeTextureContractTests(unittest.TestCase):
    def test_exact_payload_guid_and_material_contract(self) -> None:
        imports, payloads, blobs = MODULE.build(write=False)
        self.assertEqual(imports["textureCount"], 4)
        self.assertEqual(payloads["textureCount"], 4)
        self.assertEqual(payloads["generatedCopyCount"], 4)
        self.assertEqual(payloads["logicalPayloadBytes"], 4_216_256)
        self.assertEqual(len(blobs), 4)
        self.assertNotIn("runtimeEvidence", payloads)
        self.assertNotIn("runtimeRegisters", payloads)
        by_property = {row["property"]: row for row in payloads["textures"]}
        self.assertEqual(by_property["_BaseColorMap"]["textureFormat"], 25)
        self.assertEqual(by_property["_BaseColorMap"]["dxgiFormat"], 99)
        self.assertEqual(by_property["_ParallaxMap"]["sourceColorSpace"], 1)
        self.assertEqual(by_property["_MROMap"]["textureFormat"], 27)
        self.assertEqual(by_property["_MROMap"]["dxgiFormat"], 83)
        self.assertEqual(by_property["_MROMap"]["importProfile"]["textureType"], 0)
        self.assertEqual(by_property["_NormalMap"]["textureFormat"], 27)
        self.assertEqual(by_property["_NormalMap"]["importProfile"]["textureType"], 1)
        self.assertEqual(
            {Path(row["assetPath"]).name for row in payloads["materialBindings"]},
            MODULE.EXPECTED_MATERIALS,
        )
        for binding in payloads["materialBindings"]:
            self.assertEqual(
                [row["property"] for row in binding["textureBindings"]],
                MODULE.EXPECTED_PROPERTIES,
            )
            self.assertTrue(all(row["localFileId"] == 2_800_000
                                for row in binding["textureBindings"]))
        self.assertTrue(all(row["generatedCopies"][0]["guid"] for row in payloads["textures"]))
        self.assertEqual(
            hashlib.sha256(MODULE.IMPORT_CONTRACT.read_bytes()).hexdigest().upper(),
            payloads["textureImportContractSha256"],
        )
        self.assertNotIn(b"\r\n", MODULE.IMPORT_CONTRACT.read_bytes())

    def test_source_pathid_attack_fails_closed(self) -> None:
        import copy

        original = MODULE.load_json

        def altered(path: Path):
            value = original(path)
            if path == MODULE.SOURCE_CONTRACT:
                value = copy.deepcopy(value)
                value["material"]["textures"][0]["pathId"] += 1
            return value

        MODULE.load_json = altered
        try:
            with self.assertRaises((KeyError, ValueError)):
                MODULE.build(write=False)
        finally:
            MODULE.load_json = original

    def test_descriptor_layout_attack_fails_closed(self) -> None:
        import copy

        original = MODULE.load_json

        def altered(path: Path):
            value = original(path)
            if path.parent.name == "Texture2D" and value.get("m_Name"):
                value = copy.deepcopy(value)
                value["m_MipsStripped"] = 1
            return value

        MODULE.load_json = altered
        try:
            with self.assertRaisesRegex(ValueError, "stripped mip count drifted"):
                MODULE.build(write=False)
        finally:
            MODULE.load_json = original

    def test_material_property_swap_fails_closed(self) -> None:
        _, payloads, _ = MODULE.build(write=False)
        original_root = MODULE.MATERIAL_ROOT
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for name in MODULE.EXPECTED_MATERIALS:
                shutil.copyfile(original_root / name, temp_root / name)
            target = temp_root / sorted(MODULE.EXPECTED_MATERIALS)[0]
            text = target.read_text(encoding="utf-8-sig")
            by_property = {
                row["property"]: row["generatedCopies"][0]["guid"]
                for row in payloads["textures"]
            }
            mro = by_property["_MROMap"]
            normal = by_property["_NormalMap"]
            text = text.replace(mro, "0" * 32).replace(normal, mro).replace("0" * 32, normal)
            target.write_text(text, encoding="utf-8")
            MODULE.MATERIAL_ROOT = temp_root
            try:
                with self.assertRaisesRegex(ValueError, "material GUID drifted"):
                    MODULE.material_bindings(payloads["textures"])
            finally:
                MODULE.MATERIAL_ROOT = original_root

    def test_unity_transport_preserves_pptr_identity_and_normal_typing(self) -> None:
        postprocessor = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldNativeTexturePayloadPostprocessor.cs"
        ).read_text(encoding="utf-8-sig")
        validator = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldEndminfLitEffectNativeTextureValidator.cs"
        ).read_text(encoding="utf-8-sig")
        for token in (
            "endminf_liteffect_native_texture_payload_contract.json",
            "LoadRawTextureData(payload.Bytes)",
            "importer.textureType = (TextureImporterType)profile.textureType",
            "AssetDatabase.AssetPathToGUID",
            "context.DependsOnSourceAsset(payload.PayloadContractAssetPath)",
            "public override uint GetVersion()",
        ):
            self.assertIn(token, postprocessor)
        for token in (
            "localFileId == 2800000",
            "material.GetTexture(expected.property) == texture",
            "raw.SequenceEqual(payload.Bytes)",
            "importer.textureShape == TextureImporterShape.Texture2D",
            "material source hash drifted",
        ):
            self.assertIn(token, validator)


if __name__ == "__main__":
    unittest.main()
