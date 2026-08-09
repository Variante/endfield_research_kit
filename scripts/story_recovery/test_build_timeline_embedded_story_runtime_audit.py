from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.story_recovery import build_timeline_embedded_story_runtime_audit as audit


def type_row(name: str, fields: list[str]) -> dict:
    return {
        "fullName": name,
        "fields": [{"name": field} for field in fields],
        "methods": [{"name": "CreatePlayable"}, {"name": "_GetText"}],
    }


def body_row(type_name: str, method: str, targets: list[tuple[str, str]]) -> dict:
    return {
        "type": type_name,
        "method": method,
        "methodIndex": 10 if method == "CreatePlayable" else 11,
        "mappingStatus": "mapped",
        "methodPointerVa": "0x1000" if method == "CreatePlayable" else "0x1100",
        "directCalls": [{
            "resolved": [
                {"type": target_type, "method": target_method}
                for target_type, target_method in targets
            ]
        }],
    }


class TimelineEmbeddedStoryRuntimeAuditTests(unittest.TestCase):
    def test_nested_director_recovery_uses_exact_reference_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            extract = Path(temporary) / "timeline_extract"
            chunk = extract / "CHUNK-GENERAL"
            mono = chunk / "MonoBehaviour"
            directors = chunk / "PlayableDirector"
            mono.mkdir(parents=True)
            directors.mkdir(parents=True)

            def object_path(folder: Path, name: str, path_id: int) -> Path:
                return folder / f"{name}_p{path_id & 0xFFFFFFFFFFFFFFFF:016X}.json"

            def write_object(
                folder: Path,
                name: str,
                source_file: str,
                path_id: int,
                payload: dict,
                pointers: list[dict],
                source_offset: int,
            ) -> None:
                object_path(folder, name, path_id).write_text(json.dumps({
                    "$animestudio": {
                        "pathId": path_id,
                        "sourceFile": source_file,
                        "sourceOffset": source_offset,
                        "pptrReferences": pointers,
                    },
                    **payload,
                }), encoding="utf-8")

            def pointer(path: str, source_file: str, path_id: int) -> dict:
                return {
                    "path": path,
                    "resolutionStatus": "resolved",
                    "targetSourceFile": source_file,
                    "targetPathId": path_id,
                }

            write_object(
                directors, "ChildDirector", "CAB-host", 200,
                {
                    "m_GameObject": {"m_FileID": 0, "m_PathID": 300},
                    "m_PlayableAsset": {"m_FileID": 1, "m_PathID": 100},
                    "m_ExposedReferences": {"m_References": []},
                },
                [
                    pointer("$.m_GameObject", "CAB-host", 300),
                    pointer("$.m_PlayableAsset", "CAB-story", 100),
                ],
                77,
            )
            write_object(
                directors, "ParentDirector", "CAB-host", 400,
                {
                    "m_GameObject": {"m_FileID": 0, "m_PathID": 500},
                    "m_PlayableAsset": {"m_FileID": 1, "m_PathID": 600},
                    "m_ExposedReferences": {"m_References": [{
                        "Key": "general-key",
                        "Value": {"m_FileID": 0, "m_PathID": 300},
                    }]},
                },
                [
                    pointer("$.m_GameObject", "CAB-host", 500),
                    pointer("$.m_PlayableAsset", "CAB-parent", 600),
                    pointer(
                        "$.m_ExposedReferences.m_References[0].second",
                        "CAB-host", 300,
                    ),
                ],
                77,
            )
            write_object(
                mono, "ParentTimeline", "CAB-parent", 600,
                {"m_Tracks": [{"m_FileID": 0, "m_PathID": 700}]},
                [pointer("$.m_Tracks[0]", "CAB-parent", 700)],
                88,
            )
            write_object(
                mono, "ControlTrack", "CAB-parent", 700,
                {"m_Clips": [{
                    "m_Start": 1.5,
                    "m_Duration": 4.0,
                    "optionIndex": 2,
                    "m_Asset": {"m_FileID": 0, "m_PathID": 800},
                }]},
                [pointer("$.m_Clips[0].m_Asset", "CAB-parent", 800)],
                88,
            )
            write_object(
                mono, "ControlAsset", "CAB-parent", 800,
                {
                    "sourceGameObject": {"exposedName": "general-key"},
                    "updateDirector": 1,
                    "useAutoBinding": 1,
                    "autoBindingPath": "Actor",
                    "active": 1,
                },
                [],
                88,
            )
            write_object(
                mono, "RootComponent", "CAB-host", 900,
                {
                    "_timelineName": "timeline_general",
                    "_director": {"m_FileID": 0, "m_PathID": 400},
                },
                [pointer("$._director", "CAB-host", 400)],
                77,
            )
            (chunk / "filter_data.json").write_text(json.dumps([
                {"Type": "MonoBehaviour", "Offset": 77, "PathID": 900},
            ]), encoding="utf-8")

            with patch.object(
                audit,
                "original_file_record",
                side_effect=lambda path, role: {"path": path, "role": role},
            ):
                result = audit.recover_director_hosts([{
                    "sourceFile": "CAB-story",
                    "rootPathId": "100",
                    "key": "story_general",
                }], extract)

        self.assertEqual(1, result["counts"]["directorInstances"])
        self.assertEqual(1, result["counts"]["controlChains"])
        host = result["rows"][0]
        self.assertEqual(
            "exposed_reference_controlled_director_playback",
            host["relation"],
        )
        chain = host["controlChains"][0]
        self.assertEqual("general-key", chain["exposedReferenceKey"])
        self.assertEqual("400", chain["parentDirectorIdentity"]["pathId"])
        self.assertEqual("timeline_general", chain["cutsceneRoots"][0]["timelineName"])
        self.assertFalse(chain["missionOwnership"])

    def test_mapper_includes_generic_instantiations_for_playable_extensions(self) -> None:
        args = SimpleNamespace(
            gameassembly=Path("gameassembly"),
            code_registration="0x1",
        )
        mapped = audit.mapper_args(args, Path("metadata"), Path("catalog"))
        self.assertTrue(mapped.include_generic_instantiations)

    def test_original_path_ids_are_published_as_exact_decimal_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            path.write_text(json.dumps({
                "$animestudio": {
                    "pathId": 8802604764156822905,
                    "sourceFile": "CAB-general",
                    "rawDataSha256": "a" * 64,
                }
            }), encoding="utf-8")
            record = audit.original_file_record(str(path), "playable")
        self.assertEqual("8802604764156822905", record["pathId"])

        row = {
            "assetPath": "asset.json", "trackPath": "track.json", "rootPath": "root.json",
            "assetPathId": 8802604764156822905,
            "trackPathId": -3795682753767897735,
            "rootPathId": -110317566135728775,
        }
        with patch.object(audit, "original_file_record", return_value={}):
            enriched = audit.enrich_rows([row])[0]
        self.assertEqual("8802604764156822905", enriched["assetPathId"])
        self.assertEqual("-3795682753767897735", enriched["trackPathId"])
        self.assertEqual("-110317566135728775", enriched["rootPathId"])

    def test_runtime_contract_is_discovered_from_common_shape(self) -> None:
        type_name = "Beyond.Gameplay.Core.AnyTextPlayableAsset"
        catalog = {"matchedTypes": [type_row(type_name, ["_textId_1", "_textId_2"])]}
        body_map = {"bodyTargets": [
            body_row(type_name, "CreatePlayable", [
                ("Beyond.Gameplay.Core.AnyTextPlayableBehaviour", "InitAnyText"),
            ]),
            body_row(type_name, "_GetText", [
                ("Beyond.I18n.I18nUtils", "TryGetText"),
                ("Beyond.Gameplay.GameplayUIUtils", "ResolveOriginalText"),
            ]),
        ]}

        result = audit.analyze_runtime_contract(catalog, body_map)

        self.assertEqual("validated", result["validation"]["status"])
        self.assertEqual("AnyTextPlayableAsset", result["families"][0]["serializedAssetType"])
        self.assertEqual(["_textId_1", "_textId_2"], result["families"][0]["textIdFields"])

    def test_runtime_contract_failure_names_gate_and_actual_calls(self) -> None:
        type_name = "Beyond.Gameplay.Core.AnyTextPlayableAsset"
        catalog = {"matchedTypes": [type_row(type_name, ["_textId"])]}
        body_map = {"bodyTargets": [
            body_row(type_name, "CreatePlayable", [
                ("Beyond.Gameplay.Core.AnyTextPlayableBehaviour", "InitAnyText"),
            ]),
            body_row(type_name, "_GetText", [
                ("Beyond.I18n.I18nUtils", "TryGetText"),
            ]),
        ]}

        result = audit.analyze_runtime_contract(catalog, body_map)

        self.assertEqual("failed", result["validation"]["status"])
        failure = result["validation"]["failures"][0]
        self.assertEqual("timeline_embedded_story_runtime", failure["validator"])
        self.assertEqual("localized_text_resolution", failure["gate"])
        self.assertEqual(type_name, failure["sourceFile"])
        self.assertIn("Beyond.I18n.I18nUtils::TryGetText", failure["actual"])

    def test_control_runtime_contract_is_discovered_from_shape_and_calls(self) -> None:
        control_type = "UnityEngine.Timeline.GeneralControlPlayableAsset"
        root_type = "Beyond.Gameplay.View.GeneralCutsceneRootComponent"
        control_methods = [
            "CreatePlayable", "ResolveSourceGameObject", "GetControllableDirectors",
            "SearchHierarchyAndConnectDirector", "ConnectPlayablesToMixer",
            "ConnectMixerAndPlayable", "CreateActivationPlayable",
        ]
        catalog = {"matchedTypes": [
            {
                "fullName": control_type,
                "fields": [{"name": value} for value in (
                    "sourceGameObject", "prefabGameObject", "updateDirector",
                    "directorControlPath",
                )],
                "methods": [{"name": value} for value in control_methods],
            },
            {
                "fullName": root_type,
                "fields": [{"name": "_director"}, {"name": "_timelineName"}],
                "methods": [{"name": "get_topDirector"}],
            },
        ]}
        targets = {
            "CreatePlayable": [
                (control_type, "ResolveSourceGameObject"),
                (control_type, "GetControllableDirectors"),
                (control_type, "SearchHierarchyAndConnectDirector"),
                (control_type, "ConnectPlayablesToMixer"),
            ],
            "SearchHierarchyAndConnectDirector": [
                ("UnityEngine.Timeline.DirectorControlPlayable", "Create"),
            ],
            "ConnectPlayablesToMixer": [(control_type, "ConnectMixerAndPlayable")],
            "ConnectMixerAndPlayable": [
                ("UnityEngine.Playables.PlayableExtensions", "SetInputWeight"),
            ],
        }
        rows = [
            body_row(control_type, method, targets.get(method, []))
            for method in control_methods
        ]
        top = body_row(root_type, "get_topDirector", [])
        top["methodBodySummary"] = {
            "finalRegisterOrigins": {"rax": "this+0x20"},
        }
        rows.append(top)

        result = audit.analyze_control_runtime_contract(
            catalog, {"bodyTargets": rows}
        )

        self.assertEqual("validated", result["validation"]["status"])
        self.assertEqual(control_type, result["controlPlayableAsset"]["type"])
        self.assertEqual("this+0x20", result["cutsceneRoot"]["directorFieldOrigin"])

    def test_control_runtime_contract_reports_missing_generic_helper(self) -> None:
        control_type = "UnityEngine.Timeline.GeneralControlPlayableAsset"
        root_type = "Beyond.Gameplay.View.GeneralCutsceneRootComponent"
        control_methods = [
            "CreatePlayable", "ResolveSourceGameObject", "GetControllableDirectors",
            "SearchHierarchyAndConnectDirector", "ConnectPlayablesToMixer",
            "ConnectMixerAndPlayable", "CreateActivationPlayable",
        ]
        catalog = {"matchedTypes": [
            {
                "fullName": control_type,
                "fields": [{"name": value} for value in (
                    "sourceGameObject", "prefabGameObject", "updateDirector",
                    "directorControlPath",
                )],
                "methods": [{"name": value} for value in control_methods],
            },
            {
                "fullName": root_type,
                "fields": [{"name": "_director"}, {"name": "_timelineName"}],
                "methods": [{"name": "get_topDirector"}],
            },
        ]}
        targets = {
            "CreatePlayable": [
                (control_type, "ResolveSourceGameObject"),
                (control_type, "GetControllableDirectors"),
                (control_type, "SearchHierarchyAndConnectDirector"),
                (control_type, "ConnectPlayablesToMixer"),
            ],
            "SearchHierarchyAndConnectDirector": [
                ("UnityEngine.Timeline.DirectorControlPlayable", "Create"),
            ],
            "ConnectPlayablesToMixer": [(control_type, "ConnectMixerAndPlayable")],
            # Deliberately omit generic PlayableExtensions.SetInputWeight.
            "ConnectMixerAndPlayable": [],
        }
        rows = [
            body_row(control_type, method, targets.get(method, []))
            for method in control_methods
        ]
        top = body_row(root_type, "get_topDirector", [])
        top["methodBodySummary"] = {
            "finalRegisterOrigins": {"rax": "this+0x20"},
        }
        rows.append(top)

        result = audit.analyze_control_runtime_contract(
            catalog, {"bodyTargets": rows}
        )

        self.assertEqual("failed", result["validation"]["status"])
        failure = result["validation"]["failures"][0]
        self.assertEqual("control_playable_helper_chain", failure["gate"])
        self.assertIn("SetInputWeight", " ".join(failure["expected"]))
        self.assertEqual(
            f"{control_type}::ConnectMixerAndPlayable",
            failure["sourceFile"],
        )

    def test_local_order_uses_time_not_clip_or_filename_order(self) -> None:
        common = {
            "sourceFile": "CAB-general",
            "timeline": "dlgtl_general_sub_1",
            "trackPathId": 10,
            "clipOptionIndex": 2,
        }
        rows = [
            {**common, "key": "black_second", "textId": "black_second_001",
             "clipIndex": 0, "clipStart": 8.0, "clipDuration": 1.0},
            {**common, "key": "black_first", "textId": "black_first_001",
             "clipIndex": 9, "clipStart": 1.0, "clipDuration": 2.0},
        ]

        edges = audit.local_order_edges(rows)

        self.assertEqual(1, len(edges))
        self.assertEqual(("black_first", "black_second"), (edges[0]["from"], edges[0]["to"]))
        self.assertFalse(edges[0]["missionOrder"])
        self.assertEqual(2, edges[0]["optionIndex"])

    def test_overlapping_clips_do_not_create_order(self) -> None:
        rows = [
            {"sourceFile": "CAB", "timeline": "tl", "trackPathId": 1,
             "clipOptionIndex": 0, "key": "a", "textId": "a_1",
             "clipIndex": 0, "clipStart": 1.0, "clipDuration": 5.0},
            {"sourceFile": "CAB", "timeline": "tl", "trackPathId": 1,
             "clipOptionIndex": 0, "key": "b", "textId": "b_1",
             "clipIndex": 1, "clipStart": 3.0, "clipDuration": 1.0},
        ]
        self.assertEqual([], audit.local_order_edges(rows))

    def test_parent_dialog_activation_join_is_shape_driven(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gameassembly = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            levelscript = root / "level_general" / "70001.json"
            leveldata = root / "level_general_lv_data_sub_mission_general.json"
            mission_root = root / "MissionRuntimeAsset"
            mission = mission_root / "mission_general.json"
            levelscript.parent.mkdir()
            mission_root.mkdir()
            for path, data in (
                (gameassembly, b"binary"),
                (metadata, b"metadata"),
                (levelscript, b"levelscript"),
                (leveldata, b"leveldata"),
                (mission, b"{}"),
            ):
                path.write_bytes(data)

            timeline_rows = [{
                "key": "black_general",
                "dialogKey": "dlg_general_parent",
                "missionOwnership": False,
            }]
            mapping_id = "runtime-indexed-general"
            header_report = {
                "summary": {"runtimeSlotMappingId": mapping_id},
                "headerRows": [{
                    "levelId": "level_general",
                    "sourceScript": "70001",
                    "file": str(levelscript),
                    "header": {
                        "localId": 5,
                        "offset": "0x60",
                        "opcode": "0x1000/0x00",
                    },
                    "headerName": "ScriptEvent_OnGeneralEvent",
                    "targetSource": "actionHeader.nextId",
                    "targetLocalId": 6,
                    "runtimeSlotStatus": "active-final-serialized-slot",
                    "runtimeSlotMappingId": mapping_id,
                    "targetStatus": "action-list",
                    "chainStatus": "complete",
                    "playActions": [{
                        "localId": 6,
                        "offset": "0x10",
                        "opcode": "0x2000/0x00",
                        "class": "play_dialog",
                        "texts": ["dlg_general_parent"],
                    }],
                    "sceneTexts": ["dlg_general_parent"],
                    "chain": [{
                        "localId": 6,
                        "class": "play_dialog",
                        "texts": ["dlg_general_parent"],
                    }],
                }],
            }
            mission_hosts = {("level_general", "70001"): {
                "status": "unique",
                "hostMissionIds": ["mission_general"],
                "hosts": [{
                    "missionId": "mission_general",
                    "levelDataFile": str(leveldata),
                    "byteOffsets": [24],
                    "entryEndOffsets": [72],
                    "encoding": "leveldata_member22_levelscriptbriefdata",
                    "nativeSchema": "LevelData.member22",
                    "briefData": [{
                        "scriptId": "70001",
                        "keyOffset": 24,
                        "endOffset": 72,
                        "dictionaryCountOffset": 20,
                        "dictionaryEntryCount": 1,
                    }],
                }],
            }}

            result = audit.join_parent_dialog_activation_routes(
                timeline_rows,
                header_report,
                mission_hosts,
                {},
                gameassembly=gameassembly,
                metadata=metadata,
                mission_runtime_root=mission_root,
            )

        self.assertEqual("validated", result["validation"]["status"])
        self.assertEqual(1, result["counts"]["exactActivationRoutes"])
        route = result["routes"][0]
        self.assertEqual("dlg_general_parent", route["dialogKey"])
        self.assertEqual(["mission_general"], route["missionShellIds"])
        self.assertTrue(route["missionShellOwnership"])
        self.assertFalse(route["questActivation"])
        self.assertEqual([route["id"]], timeline_rows[0]["parentDialogActivationRouteIds"])
        self.assertTrue(timeline_rows[0]["missionOwnership"])
        roles = {row["role"] for row in route["relatedOriginalFiles"]}
        self.assertIn("levelscript_event_action_source", roles)
        self.assertIn("mission_leveldata_script_host", roles)
        self.assertIn("original_game_binary", roles)

    def test_parent_dialog_activation_failure_names_exact_gate(self) -> None:
        rows = [{"key": "black_general", "dialogKey": "dlg_general"}]
        result = audit.join_parent_dialog_activation_routes(
            rows,
            {
                "summary": {"runtimeSlotMappingId": "mapping"},
                "headerRows": [{
                    "levelId": "level_general",
                    "sourceScript": "1",
                    "file": "missing.json",
                    "header": {"localId": 2},
                    "headerName": "ScriptEvent_OnGeneralEvent",
                    "runtimeSlotStatus": "active-final-serialized-slot",
                    "runtimeSlotMappingId": "mapping",
                    "targetStatus": "action-list",
                    "chainStatus": "truncated",
                    "playActions": [],
                    "sceneTexts": ["dlg_general"],
                }],
            },
            {},
            {},
            gameassembly=Path("unused"),
            metadata=Path("unused"),
            mission_runtime_root=Path("unused"),
        )
        self.assertEqual("failed", result["validation"]["status"])
        failure = result["validation"]["failures"][0]
        self.assertEqual("parent_dialog_event_action_path", failure["gate"])
        self.assertEqual("truncated", failure["actual"]["chainStatus"])
        self.assertEqual("missing.json", failure["sourceFile"])

    def test_candidate_level_discovery_uses_dialog_bytes_not_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wanted = root / "level_alpha" / "90001.json"
            unrelated = root / "level_beta" / "dlg_general.json"
            wanted.parent.mkdir()
            unrelated.parent.mkdir()
            wanted.write_bytes(b"prefix dlg_general_parent suffix")
            unrelated.write_bytes(b"no matching serialized value")
            levels = audit.discover_parent_dialog_candidate_levels(
                {"dlg_general_parent"}, root
            )
        self.assertEqual(["level_alpha"], levels)


if __name__ == "__main__":
    unittest.main()
