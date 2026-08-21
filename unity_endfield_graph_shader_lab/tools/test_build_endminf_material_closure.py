from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from build_endminf_external_pptr_closure import ClosureError
from build_endminf_material_closure import (
    _artifact,
    _nonnull_refs,
    _target_cab,
    _validate_owner_cab,
    build_report,
)


REPO = Path(__file__).resolve().parents[2]
UNITY = REPO / "unity_endfield_graph_shader_lab"
CLOSURE = UNITY / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/ExternalUiEffects/endminf_external_pptr_closure.json"
MATERIALS = REPO / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
ASSET_MAPS = [
    REPO / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json",
    REPO / "export_full/recovered/AnimeStudio-cli/Persistent/maps/endfield_persistent_assets.json",
]
CAB_MAPS = [
    REPO / "export_full/recovered/AnimeStudio-cli/Maps/endfield_streamingassets_assets.bin",
    REPO / "export_full/recovered/AnimeStudio-cli/Maps/endfield_persistent_assets.bin",
]
SHADERS = REPO / "export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/Shader"
TEXTURES = REPO / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"


class EndminfMaterialClosureTests(unittest.TestCase):
    def test_nonnull_reference_extraction_is_typed(self) -> None:
        value = {
            "m_Shader": {"m_FileID": 1, "m_PathID": -2, "IsNull": False},
            "m_SavedProperties": {"m_TexEnvs": {
                "_MainTex": {"m_Texture": {"m_FileID": 2, "m_PathID": 3, "IsNull": False}},
                "_Null": {"m_Texture": {"m_FileID": 0, "m_PathID": 0, "IsNull": True}},
            }},
        }
        refs = _nonnull_refs(value)
        self.assertEqual([row["targetType"] for row in refs], ["Shader", "Texture2D"])

    def test_local_file_id_targets_hosting_cab(self) -> None:
        self.assertEqual(_target_cab("CAB-host", ["CAB-dependency"], 0, field="m_Shader"), "CAB-host")
        self.assertEqual(_target_cab("CAB-host", ["CAB-dependency"], 1, field="m_Shader"), "CAB-dependency")
        with self.assertRaisesRegex(ClosureError, "FileID 2 is out of range"):
            _target_cab("CAB-host", ["CAB-dependency"], 2, field="m_Shader")

    def test_artifact_validation_rejects_wrong_texture_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "Texture_p0000000000000001.png"
            artifact.write_bytes(b"not-a-png")
            with self.assertRaisesRegex(ClosureError, "invalid header"):
                _artifact(root, "Texture2D", "0000000000000001")

    def test_owner_fake_dependency_is_rejected_against_current_cab_map(self) -> None:
        records = {
            "cab-owner": [{
                "source": r"D:\\game\\StreamingAssets\\VFS\\A\\owner.chk",
                "sourceOffset": 42,
                "dependencies": ["CAB-a", "CAB-b"],
            }]
        }
        with self.assertRaisesRegex(ClosureError, "dependencies differ"):
            _validate_owner_cab(
                "CAB-owner",
                r"D:\\game\\StreamingAssets\\VFS\\A\\owner.chk",
                42,
                ["CAB-a", "CAB-b", "CAB-fake"],
                records,
                material_hex="ABCDEF0123456789",
            )

    def test_owner_dependency_reorder_is_rejected_against_current_cab_map(self) -> None:
        records = {
            "cab-owner": [{
                "source": r"D:\\game\\StreamingAssets\\VFS\\A\\owner.chk",
                "sourceOffset": 42,
                "dependencies": ["CAB-a", "CAB-b"],
            }]
        }
        with self.assertRaisesRegex(ClosureError, "dependencies differ"):
            _validate_owner_cab(
                "CAB-owner",
                r"D:\\game\\StreamingAssets\\VFS\\A\\owner.chk",
                42,
                ["CAB-b", "CAB-a"],
                records,
                material_hex="ABCDEF0123456789",
            )

    def test_owner_multiple_physical_sources_are_rejected(self) -> None:
        records = {
            "cab-owner": [
                {
                    "source": r"D:\\game\\StreamingAssets\\VFS\\A\\owner.chk",
                    "sourceOffset": 42,
                    "dependencies": ["CAB-a"],
                },
                {
                    "source": r"D:\\game\\Persistent\\VFS\\A\\owner.chk",
                    "sourceOffset": 42,
                    "dependencies": ["CAB-a"],
                },
            ]
        }
        with self.assertRaisesRegex(ClosureError, "no unique current source/offset"):
            _validate_owner_cab(
                "CAB-owner",
                r"D:\\game\\StreamingAssets\\VFS\\A\\owner.chk",
                42,
                ["CAB-a"],
                records,
                material_hex="ABCDEF0123456789",
            )

    def test_file_id_out_of_range_fails_before_resolution(self) -> None:
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        material = next(row for row in closure["identities"] if row.get("targetType") == "Material")
        material["cabMapCandidates"][0]["dependencies"] = []
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "closure.json"
            path.write_text(json.dumps(closure), encoding="utf-8")
            with self.assertRaisesRegex(ClosureError, "FileID .* out of range"):
                build_report(path, MATERIALS, ASSET_MAPS, CAB_MAPS, SHADERS, TEXTURES)

    def test_current_exact_closure_preserves_shader_source_ambiguity(self) -> None:
        report = build_report(CLOSURE, MATERIALS, ASSET_MAPS, CAB_MAPS, SHADERS, TEXTURES)
        self.assertEqual(report["summary"], {
            "materialCount": 27,
            "occurrenceCount": 99,
            "identityCount": 37,
            "resolvedCount": 34,
            "ambiguousCount": 3,
            "resolvedShaderCount": 0,
            "resolvedTextureCount": 34,
            "ambiguousShaderCount": 3,
            "ambiguousTextureCount": 0,
        })
        self.assertEqual(report["status"], "incomplete_ambiguous_physical_sources")
        self.assertFalse(report["renderPipelineBoundary"]["renderReady"])


if __name__ == "__main__":
    unittest.main()
