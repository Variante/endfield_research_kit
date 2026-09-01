from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from unity_endfield_graph_shader_lab.tools import prepare_endminf_source_rebuild as preflight


REPO = Path(__file__).resolve().parents[2]
LAB = REPO / "unity_endfield_graph_shader_lab"
SETUP = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldCharacterRecoverySetup.cs"
)
MANIFEST_SETUP = SETUP.with_name("EndfieldManifestCharacterSetup.cs")
BATCH = LAB / "build_all_character_recovery.bat"


def method_body(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unterminated method: {signature}")


class EndminfSourceRebuildPreflightTests(unittest.TestCase):
    def test_batch_prepares_acl_and_coordinates_project_before_unity(self) -> None:
        raw = BATCH.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        batch = BATCH.read_text(encoding="utf-8")
        self.assertIn("prepare_endminf_source_rebuild.py", batch)
        self.assertIn("ENDFIELD_RECOVERED_ACL_IMPORT_JOB", batch)
        self.assertIn('set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY=1"', batch)
        self.assertIn('set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"', batch)
        unity = batch.index('"%UNITY_EXE%" -batchmode')
        for token in (
            "Temp\\UnityLockfile",
            'IMAGENAME eq Unity.exe',
            'IMAGENAME eq UnityHub.exe',
            'IMAGENAME eq Endfield.exe',
        ):
            self.assertLess(batch.index(token), unity)
        self.assertNotIn('del "%PROJECT_DIR%Temp\\UnityLockfile"', batch)
        self.assertNotIn('erase "%PROJECT_DIR%Temp\\UnityLockfile"', batch)

    def test_editor_entry_rebuilds_endminf_before_cached_all_character_viewer(self) -> None:
        source = SETUP.read_text(encoding="utf-8")
        body = method_body(source, "public static void BuildAllCharacters()")
        ordered = (
            "EndfieldManifestCharacterSetup.RebuildEndminfSourceRecovery();",
            "EndfieldManifestCharacterSetup.BuildAllCharacterModelViewer();",
            "EndfieldPlayableCharInfoProfileBuilder.VerifyPortraitOrientation();",
        )
        offsets = [body.index(token) for token in ordered]
        self.assertEqual(offsets, sorted(offsets))

    def test_source_rebuild_dependency_order_is_fail_closed(self) -> None:
        source = MANIFEST_SETUP.read_text(encoding="utf-8")
        body = method_body(source, "public static void RebuildEndminfSourceRecovery()")
        ordered = (
            "RecoveredAclClipDataImporter.ImportConfigured();",
            "BuildActor(",
            "ValidateEndminfBodyRecovery(actor.Root);",
            "EndfieldEndminfOverviewEffectImporter.BuildAndValidate();",
            "EndfieldEndminfLitEffectCompatibilityBindingBuilder.BuildAndValidate();",
            "EndfieldEndminfOverviewEffectBindingBuilder.BuildAndValidate();",
            "EndfieldSecondaryDynamicsBindingBuilder.VerifyGeneratedEndminfBinding();",
        )
        offsets = [body.index(token) for token in ordered]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("clearGeneratedAssets: false", body)
        self.assertNotIn("BuildCharacter(endminf)", body)

    def test_targeted_outline_rebuild_preserves_and_validates_acl_assets(self) -> None:
        source = MANIFEST_SETUP.read_text(encoding="utf-8")
        body = method_body(
            source,
            "public static void RebuildEndminfPrefabForOutlineRecovery()",
        )
        self.assertIn("BuildActor(", body)
        self.assertIn("clearGeneratedAssets: false", body)
        self.assertIn("ValidateEndminfBodyRecovery(root);", body)
        self.assertNotIn("BuildCharacter(endminf)", body)

    def test_acl_jobs_are_rebuilt_from_clip_sample_and_manifest_sources(self) -> None:
        source = Path(preflight.__file__).read_text(encoding="utf-8")
        for token in (
            "build_contract(clip_path, sample_path, MANIFEST)",
            'sample.get("source_json")',
            '"contractJson": str(contract_path.resolve())',
            '"Animations/ACL"',
        ):
            self.assertIn(token, source)
        self.assertNotIn("Animations/ACL/A_actor_endminf", source)

    def test_profile_preflight_reports_hash_drift_before_unity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            portrait = temp / "portrait.png"
            portrait.write_bytes(b"source portrait")
            payload = {
                "schema": "endfield.playable-charinfo-presentation-profiles.v1",
                "validation": {"ok": True},
                "character_count": 1,
                "characters": [
                    {
                        "root_name": "Endminf",
                        "actor_token": "endminf",
                        "portrait": {
                            "texture_png": {
                                "path": str(portrait),
                                "sha256": hashlib.sha256(
                                    portrait.read_bytes()
                                ).hexdigest(),
                            }
                        },
                    }
                ],
            }
            manifest = temp / "profiles.json"
            render_parameters = temp / "render_parameters.json"
            operator_lights = temp / "operator_lights.json"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            render_parameters.write_text(
                json.dumps(
                    {
                        "schema": "endfield.original-character-render-parameters.v1",
                        "validation": {"ok": True},
                        "characters": {
                            "endminf": {
                                "modifier_serialized_parameters": {
                                    str(index): index for index in range(30)
                                },
                                "post_use_data_on_volume": {"source": True},
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            operator_lights.write_text(
                json.dumps(
                    {
                        "schema": "endfield.original-operator-lights.v1",
                        "validation": {"ok": True},
                        "actors": {"endminf": {"lights": [{"source": True}]}},
                    }
                ),
                encoding="utf-8",
            )
            patches = (
                mock.patch.object(preflight, "PROFILE_SOURCE", manifest),
                mock.patch.object(
                    preflight,
                    "CHARACTER_RENDER_PARAMETERS",
                    render_parameters,
                ),
                mock.patch.object(preflight, "OPERATOR_LIGHTS", operator_lights),
            )
            with patches[0], patches[1], patches[2]:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "expected 31, declared 1, found 1",
                ):
                    preflight.validate_profile_inputs()
                with mock.patch.object(preflight, "EXPECTED_PROFILE_COUNT", 1):
                    self.assertEqual(preflight.validate_profile_inputs(), 1)
                    payload["characters"][0]["actor_token"] = ""
                    manifest.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "actor/root identities are empty or duplicated",
                    ):
                        preflight.validate_profile_inputs()
                    payload["characters"][0]["actor_token"] = "endminf"
                    payload["characters"][0]["portrait"]["texture_png"]["sha256"] = "0" * 64
                    manifest.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "portrait PNG hash drifted"):
                        preflight.validate_profile_inputs()


if __name__ == "__main__":
    unittest.main()
