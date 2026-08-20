from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.extraction import (  # noqa: E402
    EXPLICIT_EXTERNAL_UI_EFFECT_CLIP_EVIDENCE,
    EXTERNAL_UI_EFFECT_TYPES,
    CharacterImportError,
    _assert_scoped_output,
    _fingerprint,
    _find_material_json,
    _material_dependency_ids,
    collect_hierarchy_asset_ids,
    extract_external_ui_effect_stage,
    select_external_ui_effect_entries,
    validate_external_ui_effect_export,
    validate_object_index_jsonl_summary,
    select_character_mesh_entries,
)


def _effect_row(
    name: str,
    entry_type: str,
    container: str,
    path_id: int,
    offset: int,
    source: Path,
) -> dict:
    return {
        "Name": name,
        "Container": container,
        "Source": str(source),
        "PathID": path_id,
        "Type": entry_type,
        "Hash": f"hash-{path_id}",
        "Offset": offset,
        "_asset_root": "StreamingAssets",
    }


def _write_effect_map(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"AssetEntries": entries}, indent=2) + "\n", encoding="utf-8")


class ExtractionTests(unittest.TestCase):
    def _external_effect_fixture(self, root: Path) -> tuple[dict, Path, list[dict], Path]:
        source = root / "VFS" / "effect.chk"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"exact external effect source")
        container = (
            "assets/beyond/dynamicassets/gameplay/effects/prefabs/"
            "p_fxui_endminm003_overview_01.prefab"
        )
        root_entry = _effect_row(
            "P_fxui_endminm003_overview_01", "Animator", container, 101, 1001, source
        )
        clip_entry = _effect_row(
            "A_fx_endminf_ui_overview_02", "AnimationClip", container, 102, 1002, source
        )
        clip_entry["_ownership_evidence"] = EXPLICIT_EXTERNAL_UI_EFFECT_CLIP_EVIDENCE
        carrier_entry = _effect_row("MonoBehaviour", "MonoBehaviour", container, 103, 1003, source)
        entries = [root_entry, clip_entry, carrier_entry]
        map_path = root / "StreamingAssets" / "maps" / "assets.json"
        _write_effect_map(map_path, entries)
        character = {
            "character_id": "chr_0003_endminf",
            "actor_token": "endminf",
            "ui_animation": {
                "external_ui_effect_prefab_entries": [root_entry],
                "external_ui_effect_entries": [clip_entry],
            },
        }
        return character, map_path, entries, source

    def _write_external_validation_fixture(
        self,
        output: Path,
        selection: dict,
        entries: list[dict],
        *,
        path_id_delta: int = 0,
        wrong_internal_name: bool = False,
        duplicate: bool = False,
    ) -> Path:
        output.mkdir(parents=True, exist_ok=True)
        index = output / "object_index.jsonl"
        index.write_text(
            json.dumps(
                {
                    "recordType": "summary",
                    "schemaVersion": 1,
                    "complete": True,
                    "counts": {
                        "objects": 0,
                        "schemas": 0,
                        "monoScripts": 0,
                        "scalars": 0,
                        "pptrs": 0,
                        "objectsWithTruncatedScalars": 0,
                        "errors": 0,
                        "suppressedErrors": 0,
                    },
                    "errors": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        for entry in entries[:2]:
            path_id = int(entry["PathID"]) + path_id_delta
            filename = f"{entry['Name']}_p{path_id & ((1 << 64) - 1):X}.json"
            path = output / entry["Type"] / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            internal_name = "wrong" if wrong_internal_name and entry is entries[1] else entry["Name"]
            path.write_text(json.dumps({"m_Name": internal_name}), encoding="utf-8")
            if duplicate and entry is entries[0]:
                duplicate_path = output / entry["Type"] / "duplicate" / filename
                duplicate_path.parent.mkdir(parents=True, exist_ok=True)
                duplicate_path.write_text(json.dumps({"Name": entry["Name"]}), encoding="utf-8")
        (output / ".character_import_stage.json").write_text(
            json.dumps(
                {
                    "fingerprint": _fingerprint(
                        selection["entries"],
                        EXTERNAL_UI_EFFECT_TYPES,
                        object_index_jsonl=True,
                    ),
                    "entry_count": selection["entry_count"],
                    "types": list(EXTERNAL_UI_EFFECT_TYPES),
                    "object_index_jsonl": True,
                }
            ),
            encoding="utf-8",
        )
        return index

    def test_external_effect_selector_expands_exact_container_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, entries, _source = self._external_effect_fixture(Path(temporary))

            selection = select_external_ui_effect_entries(character, [map_path])

            self.assertEqual(selection["entry_count"], 3)
            self.assertEqual(len(selection["prefabs"]), 1)
            self.assertEqual(
                {entry["Type"] for entry in selection["entries"]},
                {"Animator", "AnimationClip", "MonoBehaviour"},
            )
            self.assertEqual(len(selection["expected_root_identities"]), 1)
            self.assertEqual(len(selection["expected_clip_identities"]), 1)
            self.assertEqual(selection["entries"][0]["_asset_root"], "StreamingAssets")

    def test_external_effect_selector_fails_when_catalogued_clip_is_not_exactly_in_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, entries, _source = self._external_effect_fixture(Path(temporary))
            _write_effect_map(map_path, [entries[0], entries[2]])

            with self.assertRaisesRegex(CharacterImportError, "exact root/clip identities"):
                select_external_ui_effect_entries(character, [map_path])

    def test_external_effect_selector_rejects_explicit_wrong_container(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, entries, _source = self._external_effect_fixture(Path(temporary))
            character["ui_animation"]["external_ui_effect_entries"][0]["Container"] = (
                "assets/beyond/dynamicassets/gameplay/effects/prefabs/"
                "p_fxui_endminm003_overview_02.prefab"
            )

            with self.assertRaisesRegex(CharacterImportError, "outside the selected"):
                select_external_ui_effect_entries(character, [map_path])

    def test_external_effect_selector_rejects_explicit_wrong_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, _entries, _source = self._external_effect_fixture(Path(temporary))
            character["ui_animation"]["external_ui_effect_entries"][0]["Type"] = "MonoBehaviour"

            with self.assertRaisesRegex(CharacterImportError, "not an AnimationClip"):
                select_external_ui_effect_entries(character, [map_path])

    def test_external_effect_selector_rejects_explicit_wrong_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, _entries, _source = self._external_effect_fixture(Path(temporary))
            character["ui_animation"]["external_ui_effect_entries"][0]["Name"] = (
                "A_actor_endminf_ui_overview_02"
            )

            with self.assertRaisesRegex(CharacterImportError, "not A_fx_endminf_ui"):
                select_external_ui_effect_entries(character, [map_path])

    def test_external_effect_selector_ignores_legacy_unmarked_actor_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, entries, _source = self._external_effect_fixture(Path(temporary))
            legacy = dict(entries[1])
            legacy.pop("_ownership_evidence", None)
            legacy["Name"] = "A_actor_endminf_ui_overview_02"
            legacy["Container"] = (
                "assets/beyond/arts/effects/commonassets/arts/sk_model/"
                "sk_fx_endminf_01_ui.fbx"
            )
            character["ui_animation"]["external_ui_effect_entries"].append(legacy)

            selection = select_external_ui_effect_entries(character, [map_path])

            self.assertEqual(len(selection["expected_clip_identities"]), 1)

    def test_external_effect_selector_rejects_unmarked_legacy_actor_inside_selected_container(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, entries, _source = self._external_effect_fixture(Path(temporary))
            legacy = dict(entries[1])
            legacy.pop("_ownership_evidence", None)
            legacy["Name"] = "A_actor_endminf_ui_overview_02"
            legacy["Container"] = entries[1]["Container"]
            character["ui_animation"]["external_ui_effect_entries"].append(legacy)

            with self.assertRaisesRegex(CharacterImportError, "unmarked legacy row inside"):
                select_external_ui_effect_entries(character, [map_path])

    def test_external_effect_selector_rejects_unmarked_new_fx_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            character, map_path, _entries, _source = self._external_effect_fixture(Path(temporary))
            character["ui_animation"]["external_ui_effect_entries"][0].pop(
                "_ownership_evidence"
            )

            with self.assertRaisesRegex(CharacterImportError, "lacks explicit"):
                select_external_ui_effect_entries(character, [map_path])

    def test_external_effect_stage_dry_run_uses_reviewed_types_and_object_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            character, map_path, _entries, _source = self._external_effect_fixture(root)
            output = root / "unity" / "scratch" / "external_ui_effects"
            commands: list[list[str]] = []

            def capture(command: list[str], *, dry_run: bool = False) -> None:
                self.assertTrue(dry_run)
                commands.append(command)

            with patch("character_import.extraction._run", side_effect=capture):
                report = extract_external_ui_effect_stage(
                    character,
                    [map_path],
                    output=output,
                    allowed_root=root / "unity" / "scratch",
                    dry_run=True,
                )

            self.assertEqual(report["status"], "planned")
            self.assertEqual(report["entry_count"], 3)
            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0][commands[0].index("--types") + 1 : commands[0].index("--export_type")], list(EXTERNAL_UI_EFFECT_TYPES))
            self.assertIn("--object_index_jsonl", commands[0])
            self.assertFalse(output.exists())

    def test_object_index_summary_and_export_identity_are_terminal_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            character, map_path, entries, _source = self._external_effect_fixture(root)
            selection = select_external_ui_effect_entries(character, [map_path])
            output = root / "output"
            index = self._write_external_validation_fixture(output, selection, entries)

            summary = validate_object_index_jsonl_summary(index)
            validated = validate_external_ui_effect_export(output, selection, [index])

            self.assertTrue(summary["complete"])
            self.assertEqual(validated["root_clip_count"], 2)

    def test_external_effect_export_rejects_wrong_path_id_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            character, map_path, entries, _source = self._external_effect_fixture(root)
            selection = select_external_ui_effect_entries(character, [map_path])
            output = root / "output"
            index = self._write_external_validation_fixture(
                output, selection, entries, path_id_delta=1
            )

            with self.assertRaisesRegex(CharacterImportError, "missing exact type-directory"):
                validate_external_ui_effect_export(output, selection, [index])

    def test_external_effect_export_rejects_wrong_internal_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            character, map_path, entries, _source = self._external_effect_fixture(root)
            selection = select_external_ui_effect_entries(character, [map_path])
            output = root / "output"
            index = self._write_external_validation_fixture(
                output, selection, entries, wrong_internal_name=True
            )

            with self.assertRaisesRegex(CharacterImportError, "internal Name/m_Name"):
                validate_external_ui_effect_export(output, selection, [index])

    def test_external_effect_export_rejects_duplicate_exact_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            character, map_path, entries, _source = self._external_effect_fixture(root)
            selection = select_external_ui_effect_entries(character, [map_path])
            output = root / "output"
            index = self._write_external_validation_fixture(
                output, selection, entries, duplicate=True
            )

            with self.assertRaisesRegex(CharacterImportError, "duplicate exact"):
                validate_external_ui_effect_export(output, selection, [index])

    def test_object_index_summary_rejects_nonempty_errors_and_inconsistent_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "object_index.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "recordType": "summary",
                        "schemaVersion": 1,
                        "complete": False,
                        "counts": {
                            "objects": 0,
                            "schemas": 0,
                            "monoScripts": 0,
                            "scalars": 0,
                            "pptrs": 0,
                            "objectsWithTruncatedScalars": 0,
                            "errors": 1,
                            "suppressedErrors": 0,
                        },
                        "errors": [{"code": "asset_export_incomplete", "message": "failed"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CharacterImportError, "contains export errors"):
                validate_object_index_jsonl_summary(path)

            path.write_text(
                json.dumps(
                    {
                        "recordType": "summary",
                        "schemaVersion": 1,
                        "complete": True,
                        "counts": {
                            "objects": 0,
                            "schemas": 0,
                            "monoScripts": 0,
                            "scalars": 0,
                            "pptrs": 0,
                            "objectsWithTruncatedScalars": 0,
                            "errors": 1,
                            "suppressedErrors": 0,
                        },
                        "errors": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CharacterImportError, "error counts are inconsistent"):
                validate_object_index_jsonl_summary(path)

            path.write_text(
                json.dumps(
                    {
                        "recordType": "summary",
                        "schemaVersion": 1,
                        "complete": False,
                        "counts": {
                            "objects": 0,
                            "schemas": 0,
                            "monoScripts": 0,
                            "scalars": 0,
                            "pptrs": 0,
                            "objectsWithTruncatedScalars": 0,
                            "errors": 1,
                            "suppressedErrors": 0,
                        },
                        "errors": [{"message": "missing code"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CharacterImportError, "malformed error"):
                validate_object_index_jsonl_summary(path)

    def test_material_json_falls_back_to_path_id_when_asset_name_is_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            export_root = Path(temporary)
            folder = export_root / "StreamingAssets/json_by_type/Material"
            folder.mkdir(parents=True)
            expected = folder / "M_eyeshadow_common_05_p65D54F510D76590E.json"
            expected.write_text("{}", encoding="utf-8")

            found = _find_material_json(
                export_root,
                {
                    "Name": "ac153a0ab9ff2f01",
                    "PathID": 7337858377406896398,
                    "_asset_root": "StreamingAssets",
                },
            )

            self.assertEqual(found, expected)

    def test_material_dependency_ids_accept_force_text_single_key_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "material.json"
            path.write_text(
                json.dumps(
                    {
                        "m_Shader": {"m_PathID": 301},
                        "m_SavedProperties": {
                            "m_TexEnvs": [
                                {"_BaseColorMap": {"m_Texture": {"m_PathID": 401}}},
                                {"_NormalTex": {"m_Texture": {"m_PathID": 402}}},
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            dependencies = _material_dependency_ids(path)

            self.assertEqual(dependencies["Shader"], {301})
            self.assertEqual(dependencies["Texture2D"], {401, 402})

    def test_hierarchy_asset_ids_come_from_original_renderer_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game_objects = root / "GameObject"
            game_objects.mkdir()
            (game_objects / "body.json").write_text(
                json.dumps(
                    {
                        "m_SkinnedMeshRenderer": {
                            "m_Mesh": {"m_PathID": 101},
                            "m_Materials": [
                                {"m_PathID": 201},
                                {"m_PathID": 202},
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )
            (game_objects / "bone.json").write_text(
                json.dumps({"m_SkinnedMeshRenderer": None}),
                encoding="utf-8",
            )
            ids = collect_hierarchy_asset_ids(root)
            self.assertEqual(ids["Mesh"], {101})
            self.assertEqual(ids["Material"], {201, 202})

    def test_recursive_cleanup_guard_is_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "work"
            root.mkdir()
            _assert_scoped_output(root / "characters" / "chr_0001_test", root)
            with self.assertRaises(CharacterImportError):
                _assert_scoped_output(root, root)
            with self.assertRaises(CharacterImportError):
                _assert_scoped_output(root.parent / "outside", root)

    def test_mesh_selection_prefers_an_installed_duplicate_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installed = root / "StreamingAssets" / "mesh.chk"
            installed.parent.mkdir()
            installed.write_bytes(b"original game chunk")
            missing = root / "Persistent" / "stale.chk"
            common = {
                "Name": "S_actor_test_body_lod0",
                "Container": "assets/beyond/arts/entity/actor/test/body.mesh",
                "PathID": 101,
                "Type": "Mesh",
                "Offset": 10,
            }
            selected = select_character_mesh_entries(
                {"character_id": "chr_test", "actor_token": "test"},
                {"Mesh": {101}},
                {
                    ("Mesh", 101): [
                        {**common, "Source": str(missing), "_asset_root": "Persistent"},
                        {**common, "Source": str(installed), "_asset_root": "StreamingAssets"},
                    ]
                },
            )
            self.assertEqual(selected[0]["Source"], str(installed))

    def test_mesh_selection_does_not_trade_actor_identity_for_availability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unrelated = root / "StreamingAssets" / "unrelated.chk"
            unrelated.parent.mkdir()
            unrelated.write_bytes(b"different actor")
            missing_actor_source = root / "Persistent" / "mifu.chk"
            common = {
                "PathID": 101,
                "Type": "Mesh",
                "Offset": 10,
            }
            selected = select_character_mesh_entries(
                {"character_id": "chr_0031_mifu", "actor_token": "mifu"},
                {"Mesh": {101}},
                {
                    ("Mesh", 101): [
                        {
                            **common,
                            "Name": "S_actor_other_body_lod0",
                            "Container": "assets/beyond/arts/entity/actor/other/body.mesh",
                            "Source": str(unrelated),
                            "_asset_root": "StreamingAssets",
                        },
                        {
                            **common,
                            "Name": "S_actor_mifu_body_lod0",
                            "Container": "assets/beyond/arts/entity/actor/mifu/body.mesh",
                            "Source": str(missing_actor_source),
                            "_asset_root": "Persistent",
                        },
                    ]
                },
            )
            self.assertEqual(selected[0]["Name"], "S_actor_mifu_body_lod0")


if __name__ == "__main__":
    unittest.main()
