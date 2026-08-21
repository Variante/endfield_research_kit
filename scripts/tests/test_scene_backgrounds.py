from __future__ import annotations

import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.audio_semantics import identifiers, scene_backgrounds


def object_row(
    script_name: str,
    scalars: list[list[object]],
    *,
    path_id: int,
    name: str,
    scene_context: dict | None = None,
) -> dict:
    row = {
        "recordType": "object",
        "object": {
            "serializedFile": "CAB-fixture",
            "source": "VFS/fixture.chk",
            "sourceOffset": path_id * 10,
            "pathId": path_id,
        },
        "name": name,
        "script": {"fullName": script_name, "assembly": "Gameplay.Beyond.dll"},
        "scalars": scalars,
    }
    if scene_context is not None:
        row["sceneContext"] = scene_context
    return row


class SceneBackgroundCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.room_tone_hash = 0x7AC43E5E
        self.ambient_name = "au_amb_fixture_loop"
        self.ambient_hash = identifiers.audio_hash_generator_compute(self.ambient_name)
        self.audio_index = {
            "wwiseEventInventory": [
                {
                    "eventHash": self.room_tone_hash,
                    "eventId": "hashed-event:0x7ac43e5e",
                    "eventIdentityStatus": "wwiseObjectWithoutRecoveredTriggerName",
                    "traversalStatus": "complete",
                    "mediaIds": [593335165],
                    "mediaRelationTypes": ["layerChild"],
                },
                {
                    "eventHash": self.ambient_hash,
                    "eventId": self.ambient_name,
                    "eventIdentityStatus": "recoveredAuthoredName",
                    "traversalStatus": "complete",
                    "mediaIds": [42],
                },
            ],
            "entries": [
                {"id": "593335165", "src": "/room.flac", "duration": 22.442667},
                {"id": 42, "src": "/ambient.flac", "duration": 3.5},
            ],
        }

    @staticmethod
    def _containment(
        identity: dict,
        *,
        scene_id: str = "map01_lv001",
        source_name: str = "map01_lv001",
        source_path: str = "Assets/Scenes/map01_lv001.unity",
        containment_type: str = "SceneAsset",
    ) -> dict:
        return {
            "identity": dict(identity),
            "sceneId": scene_id,
            "sourceName": source_name,
            "sourcePath": source_path,
            "containmentType": containment_type,
        }

    @staticmethod
    def _asset_map_payload(entry: dict) -> str:
        return json.dumps({
            "GameType": "Endfield",
            "AssetEntries": [entry],
        })

    def test_audio_map_keeps_event_aux_bus_and_scene_index_distinct(self) -> None:
        audio_map = object_row(
            scene_backgrounds.AUDIO_MAP_DATA_TYPE,
            [
                ["$.m_Name", "s", "map01_audio"],
                ["$.levelGlobalEvents._sceneNames[0]", "s", "map01_lv001"],
                ["$.levelGlobalEvents._sceneStateCount[0]", "i", 1],
                ["$.levelGlobalEvents._states[0]", "i", 7],
                [
                    "$.levelGlobalEvents._events[0].outdoorRoomToneEvent",
                    "i",
                    self.room_tone_hash,
                ],
                [
                    "$.levelGlobalEvents._events[0].outdoorRoomAuxBusId",
                    "i",
                    0x12345678,
                ],
                ["$.levelGlobalEvents._events[0].outdoorRoomToneRtpc", "f", 0.5],
            ],
            path_id=1,
            name="map01_audio",
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [audio_map]}, self.audio_index
        )

        self.assertEqual(result["counts"]["exactNamedScenes"], 1)
        definition = result["scenes"][0]["definitions"][0]
        self.assertEqual(definition["sceneId"], "map01_lv001")
        self.assertEqual(len(definition["events"]), 1)
        self.assertEqual(definition["events"][0]["eventHash"], self.room_tone_hash)
        self.assertEqual(definition["events"][0]["possibleMedia"][0]["id"], 593335165)
        self.assertEqual(
            definition["roomToneParameters"][0]["role"], "outdoorRoomAuxBus"
        )
        self.assertEqual(definition["states"][0]["scalars"][0]["value"], 7)
        context_key = identifiers.event_hash_context_key(self.room_tone_hash)
        self.assertEqual(result["eventContexts"][context_key][0]["sceneId"], "map01_lv001")

    def test_missing_scene_name_is_not_inferred_from_asset_name(self) -> None:
        audio_map = object_row(
            scene_backgrounds.AUDIO_MAP_DATA_TYPE,
            [[
                "$.levelGlobalEvents._events[0].outdoorRoomToneEvent",
                "i",
                self.room_tone_hash,
            ]],
            path_id=2,
            name="map99_lv999_audio",
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [audio_map]}, self.audio_index
        )

        self.assertEqual(result["scenes"], [])
        unresolved = result["unresolvedSceneDefinitions"][0]
        self.assertIsNone(unresolved["sceneId"])
        self.assertEqual(
            unresolved["sceneMappingStatus"],
            "unresolvedEventIndexWithoutSceneName",
        )

    def test_scene_emitter_keeps_exact_position_and_possible_media(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=3,
            name="EffectSetting",
            scene_context={
                "gameObjectName": "Emitter",
                "hierarchyPath": ["Level", "Emitter"],
                "worldPositionStatus": "exact_transform_hierarchy",
                "worldPosition": {"x": 1.0, "y": 2.0, "z": 3.0},
            },
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]}, self.audio_index
        )

        request = result["sceneEmitters"][0]["eventRequests"][0]
        self.assertEqual(request["semanticRole"], "authoredAmbientEmitterCandidate")
        self.assertEqual(request["possibleMedia"][0]["id"], 42)
        self.assertEqual(
            result["sceneEmitters"][0]["placement"]["worldPosition"],
            {"x": 1.0, "y": 2.0, "z": 3.0},
        )
        self.assertEqual(
            result["sceneEmitters"][0]["sceneOwnershipStatus"],
            "objectIndexSceneContextWithoutSceneAssetJoin",
        )

    def test_non_exact_position_is_not_promoted(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.Audio.AudioSceneObject",
            [["$._onEnableLoopAudioEvent._id", "i", self.room_tone_hash]],
            path_id=4,
            name="AudioSceneObject",
            scene_context={
                "gameObjectName": "PrefabEmitter",
                "hierarchyPath": ["PrefabEmitter"],
                "worldPositionStatus": "prefab_local_transform",
                "worldPosition": {"x": 0.0, "y": 0.0, "z": 0.0},
            },
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]}, self.audio_index
        )

        placement = result["sceneEmitters"][0]["placement"]
        self.assertEqual(placement["worldPositionStatus"], "prefab_local_transform")
        self.assertNotIn("worldPosition", placement)

    def test_exact_identity_containment_projects_scene_fields_and_keeps_emitter_kind(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=10,
            name="ExactEmitter",
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]},
            self.audio_index,
            scene_containment_index=[self._containment(emitter["object"])],
        )

        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"],
            "exactSceneAssetLevelContainment",
        )
        self.assertEqual(recovered["sceneId"], "map01_lv001")
        self.assertEqual(recovered["sourceName"], "map01_lv001")
        self.assertEqual(
            recovered["sceneContainmentEvidence"]["containmentType"],
            "SceneAsset",
        )
        context_key = identifiers.event_hash_context_key(self.ambient_hash)
        context = result["eventContexts"][context_key][0]
        self.assertEqual(context["kind"], "sceneEmitterAudioEvent")
        self.assertEqual(context["sceneId"], "map01_lv001")

    def test_missing_identity_containment_stays_unresolved_without_scene_fields(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.Audio.AudioSceneObject",
            [["$._onEnableLoopAudioEvent._id", "i", self.room_tone_hash]],
            path_id=11,
            name="MissingEmitter",
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]},
            self.audio_index,
            scene_containment_index=[],
        )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"],
            "missingSceneAssetLevelContainment",
        )
        for key in ("sceneId", "sourceName", "sourcePath"):
            self.assertNotIn(key, recovered)
        self.assertLessEqual(
            len(recovered["sceneContainmentDiagnostics"]),
            scene_backgrounds.SCENE_CONTAINMENT_DIAGNOSTIC_LIMIT,
        )
        context_key = identifiers.event_hash_context_key(self.room_tone_hash)
        context = result["eventContexts"][context_key][0]
        self.assertEqual(context["kind"], "sceneEmitterAudioEvent")
        self.assertNotIn("sceneId", context)

    def test_two_explicit_identity_candidates_are_ambiguous(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=12,
            name="AmbiguousEmitter",
            scene_context={
                "gameObject": {
                    "serializedFile": "CAB-fixture",
                    "source": "VFS/fixture.chk",
                    "sourceOffset": 130,
                    "pathId": 13,
                },
            },
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]},
            self.audio_index,
            scene_containment_index=[
                self._containment(emitter["object"]),
                self._containment(
                    emitter["sceneContext"]["gameObject"],
                    scene_id="map02_lv002",
                    source_name="map02_lv002",
                    source_path="Assets/Scenes/map02_lv002.unity",
                ),
            ],
        )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"],
            "ambiguousSceneAssetLevelContainment",
        )
        self.assertNotIn("sceneId", recovered)

    def test_duplicate_identity_conflict_fails_closed(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=14,
            name="ConflictingEmitter",
        )
        first = self._containment(emitter["object"])
        second = self._containment(
            emitter["object"],
            source_path="Assets/Scenes/other.unity",
        )
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]},
            self.audio_index,
            scene_containment_index=[first, second],
        )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"],
            "conflictingSceneAssetLevelContainment",
        )
        self.assertNotIn("sceneId", recovered)

    def test_mixed_scene_and_other_container_families_fail_closed(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=141,
            name="MixedContainerEmitter",
        )
        scene_entry = self._containment(emitter["object"])
        other_entry = {
            "identity": dict(emitter["object"]),
            "containmentType": "AssetContainer",
            "sourceAssetPath": "assets/other/container.asset",
        }
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]},
            self.audio_index,
            scene_containment_index=[scene_entry, other_entry],
        )
        recovered = result["sceneEmitters"][0]
        self.assertIn(
            recovered["sceneOwnershipStatus"],
            {
                "ambiguousSceneAssetLevelContainment",
                "conflictingSceneAssetLevelContainment",
            },
        )
        self.assertNotIn("sceneId", recovered)

    def test_explicit_prefab_asset_is_not_scene_contained(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=15,
            name="PrefabEmitter",
        )
        prefab = {
            "identity": dict(emitter["object"]),
            "containmentType": "Prefab",
            "sourceAssetPath": "Assets/Prefabs/fx_common.prefab",
        }
        result = scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": [emitter]},
            self.audio_index,
            scene_containment_index=[prefab],
        )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"], "prefabLocalNotSceneContained"
        )
        self.assertNotIn("sceneId", recovered)

    def test_scene_rows_are_iterated_once_when_resolving_containment(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=16,
            name="SinglePassEmitter",
        )

        class OnePassRows:
            def __init__(self, rows: list[dict]) -> None:
                self.rows = rows
                self.iterations = 0

            def __iter__(self):
                self.iterations += 1
                if self.iterations > 1:
                    raise AssertionError("object index was scanned more than once")
                yield from self.rows

        rows = OnePassRows([emitter])
        scene_backgrounds.build_scene_background_catalog(
            {"StreamingAssets": rows},
            self.audio_index,
            scene_containment_index=[self._containment(emitter["object"])],
        )
        self.assertEqual(rows.iterations, 1)

    def test_asset_map_provider_streams_source_path_id_and_marks_prefab_local(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=17,
            name="MappedPrefabEmitter",
        )
        emitter["object"]["source"] = "VFS/root/fixture.chk"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(
                self._asset_map_payload({
                    "Name": "MonoBehaviour",
                    "Container": "assets/{nested}/effects/fx.prefab",
                    "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/fixture.chk",
                    "PathID": 17,
                    "Type": "MonoBehaviour",
                }) + "\n",
                encoding="utf-8",
            )
            result = scene_backgrounds.build_scene_background_catalog(
                {"StreamingAssets": [emitter]},
                self.audio_index,
                scene_containment_provider=(
                    lambda identities: scene_backgrounds._asset_map_containment_provider(
                        root, identities
                    )
                ),
            )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"], "prefabLocalNotSceneContained"
        )
        self.assertEqual(
            recovered["sceneContainmentDiagnostics"][0]["candidates"][0][
                "sourceAssetPath"
            ],
            "assets/{nested}/effects/fx.prefab",
        )

    def test_asset_map_unity_container_needs_authoritative_scene_id(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=18,
            name="MappedSceneContainerEmitter",
        )
        emitter["object"]["source"] = "VFS/root/fixture.chk"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(
                self._asset_map_payload({
                    "Name": "MonoBehaviour",
                    "Container": "assets/beyond/scenes/map01/map01_lv001.unity",
                    "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/fixture.chk",
                    "PathID": 18,
                    "Type": "MonoBehaviour",
                }) + "\n",
                encoding="utf-8",
            )
            result = scene_backgrounds.build_scene_background_catalog(
                {"StreamingAssets": [emitter]},
                self.audio_index,
                scene_containment_provider=(
                    lambda identities: scene_backgrounds._asset_map_containment_provider(
                        root, identities
                    )
                ),
            )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"],
            "sceneAssetContainerWithoutAuthoritativeSceneId",
        )
        self.assertNotIn("sceneId", recovered)

    def test_asset_map_source_token_rejects_other_vfs_prefix_and_basename_collision(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=19,
            name="CollisionEmitter",
        )
        emitter["object"]["source"] = "VFS/root_a/shared.chk"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(
                self._asset_map_payload({
                    "Name": "MonoBehaviour",
                    "Container": "assets/effects/shared.prefab",
                    "Source": "D:/Other/VFS/root_b/shared.chk",
                    "PathID": 19,
                    "Type": "MonoBehaviour",
                }) + "\n",
                encoding="utf-8",
            )
            provided = scene_backgrounds._asset_map_containment_provider(
                root, [emitter["object"]]
            )
        self.assertEqual(provided["entries"], [])
        self.assertEqual(provided["diagnostics"], [])
        self.assertTrue(any(
            row.get("status") == "assetMapScanned"
            for row in provided["scanEvidence"]
        ))

    def test_malformed_asset_map_discards_partial_matches_with_actionable_diagnostic(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=20,
            name="MalformedMapEmitter",
        )
        emitter["object"]["source"] = "VFS/root/fixture.chk"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(
                '{"GameType":"Endfield","AssetEntries":[' + json.dumps({
                    "Name": "MonoBehaviour",
                    "Container": "assets/effects/fx.prefab",
                    "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/fixture.chk",
                    "PathID": 20,
                    "Type": "MonoBehaviour",
                }) + ",\n",
                encoding="utf-8",
            )
            result = scene_backgrounds.build_scene_background_catalog(
                {"StreamingAssets": [emitter]},
                self.audio_index,
                scene_containment_provider=(
                    lambda identities: scene_backgrounds._asset_map_containment_provider(
                        root, identities
                    )
                ),
            )
        recovered = result["sceneEmitters"][0]
        self.assertEqual(
            recovered["sceneOwnershipStatus"],
            "missingSceneAssetLevelContainment",
        )
        self.assertTrue(any(
            row.get("status") in {"assetMapMalformed", "assetMapRejected"}
            for row in recovered["sceneContainmentDiagnostics"]
        ))

    def test_unreadable_asset_map_reports_utf8_and_missing_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_bytes(b"[\xff")
            diagnostics: list[dict] = []
            self.assertEqual(
                list(scene_backgrounds._iter_asset_map_entries(path, diagnostics)),
                [],
            )
            self.assertEqual(diagnostics[0]["status"], "assetMapUnreadable")
            self.assertEqual(diagnostics[0]["reason"], "invalidUtf8")
            missing: list[dict] = []
            self.assertEqual(
                list(scene_backgrounds._iter_asset_map_entries(
                    Path(temporary) / "missing.json", missing
                )),
                [],
            )
            self.assertEqual(missing[0]["status"], "assetMapUnavailable")

    def test_production_asset_map_requires_object_asset_entries_root(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=21,
            name="RootShapeEmitter",
        )
        emitter["object"]["source"] = "VFS/root/fixture.chk"
        roots = [
            (
                "[{}]",
                "rootIsNotObject",
            ),
            (
                '{"GameType":"Endfield","Other":{}}',
                "missingAssetEntries",
            ),
            (
                '{"GameType":"Endfield","AssetEntries":[],"AssetEntries":[]}',
                "duplicateAssetEntries",
            ),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            for payload, reason in roots:
                map_path.write_text(payload, encoding="utf-8")
                provided = scene_backgrounds._asset_map_containment_provider(
                    root, [emitter["object"]]
                )
                self.assertEqual(provided["entries"], [])
                self.assertTrue(any(
                    row.get("reason") == reason
                    for row in provided["diagnostics"]
                ))

    def test_persistent_asset_map_uses_persistent_vfs_prefix_only(self) -> None:
        emitter = object_row(
            "Beyond.Gameplay.EffectSetting",
            [["$.references.RefIds[0].data.soundName", "s", self.ambient_name]],
            path_id=22,
            name="PersistentMappedEmitter",
        )
        emitter["object"]["source"] = "VFS/root/persistent.chk"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "Persistent"
                / "maps" / "endfield_persistent_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(self._asset_map_payload({
                "Name": "MonoBehaviour",
                "Container": "assets/persistent/fx.prefab",
                "Source": "D:/Game/Endfield_Data/Persistent/VFS/root/persistent.chk",
                "PathID": 22,
                "Type": "MonoBehaviour",
            }), encoding="utf-8")
            provided = scene_backgrounds._asset_map_containment_provider(
                root, [emitter["object"]]
            )
            map_path.write_text(self._asset_map_payload({
                "Name": "MonoBehaviour",
                "Container": "assets/persistent/fx.prefab",
                "Source": "D:/Other/VFS/root/persistent.chk",
                "PathID": 22,
                "Type": "MonoBehaviour",
            }), encoding="utf-8")
            negative = scene_backgrounds._asset_map_containment_provider(
                root, [emitter["object"]]
            )
        self.assertEqual(len(provided["entries"]), 1)
        self.assertFalse(any(
            row.get("status") in {"assetMapMalformed", "assetMapUnreadable"}
            for row in provided["diagnostics"]
        ))
        self.assertEqual(negative["entries"], [])
        self.assertEqual(negative["diagnostics"], [])


class PublishedObjectIndexGateTests(unittest.TestCase):
    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_audio_level_and_mission_scene_refs_join_exact_scene(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            index_dir = root / "index"
            index_dir.mkdir()
            objects_path = index_dir / "objects.jsonl.gz"
            with gzip.open(objects_path, "wt", encoding="utf-8") as stream:
                stream.write(json.dumps(object_row(
                    scene_backgrounds.AUDIO_MAP_DATA_TYPE,
                    [["$.levelGlobalEvents._sceneNames[0]", "s", "map01_lv001"]],
                    path_id=6,
                    name="map01_audio",
                )) + "\n")
            summary = {
                "complete": True,
                "counts": {"objects": 1},
                "outputs": {"objects": {"path": objects_path.name, "sha256": "fixture"}},
                "stageSignature": {"sha256": "stage"},
            }
            level_payload = {
                "map01_lv001": {
                    "battleMusicTriggerEvent": 0x7AC43E5E,
                    "customMusicModeBaseState": 4,
                    "levelInitEvent": [-1],
                }
            }
            mission_payload = {
                "missionId": "c35m3",
                "acceptMode": {"mode": 2, "levelId": "map01_lv001"},
            }
            for source in ("Persistent", "StreamingAssets"):
                self._write_json(
                    root / "structured" / source / "Table/AudioLevel.json",
                    level_payload,
                )
                self._write_json(
                    root / "structured" / source
                    / "Data/Json/MissionRuntimeAsset/c35m3_meta.json",
                    mission_payload,
                )
            audio_index = {
                "wwiseEventInventory": [{
                    "eventHash": 0x7AC43E5E,
                    "eventId": "hashed-event:0x7ac43e5e",
                    "traversalStatus": "complete",
                    "mediaIds": [],
                }],
                "entries": [],
            }
            with (
                patch.object(
                    scene_backgrounds,
                    "load_animestudio_object_index_summary",
                    return_value=summary,
                ),
                patch.object(
                    scene_backgrounds,
                    "animestudio_object_index_dir",
                    return_value=index_dir,
                ),
            ):
                result = scene_backgrounds.collect_scene_background_semantics(
                    root, audio_index, sources=("StreamingAssets",)
                )

            scene = next(row for row in result["scenes"] if row["sceneId"] == "map01_lv001")
            self.assertEqual(scene["audioLevel"]["customMusicModeBaseState"], 4)
            self.assertEqual(
                [row["role"] for row in scene["audioLevel"]["events"]],
                ["levelInitEvent", "battleMusicTriggerEvent"],
            )
            self.assertEqual(scene["missionRefs"][0]["missionId"], "c35m3")
            self.assertEqual(
                scene["missionRefs"][0]["mappingStatus"],
                "exactMissionAcceptModeLevelId",
            )
            self.assertEqual(result["counts"]["missionSceneRefs"], 1)
            self.assertEqual(result["counts"]["audioLevelEventOccurrences"], 2)

    def test_conflicting_audio_level_mirrors_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source, value in (("Persistent", 1), ("StreamingAssets", 2)):
                self._write_json(
                    root / "structured" / source / "Table/AudioLevel.json",
                    {"map01_lv001": {"levelInitEvent": [value]}},
                )
            with self.assertRaisesRegex(
                scene_backgrounds.SceneBackgroundError,
                "conflicting mirrored Table/AudioLevel.json",
            ):
                scene_backgrounds._collect_audio_level_semantics(root, {}, {})

    def test_published_object_count_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            index_dir = root / "index"
            index_dir.mkdir()
            objects_path = index_dir / "objects.jsonl.gz"
            with gzip.open(objects_path, "wt", encoding="utf-8") as stream:
                stream.write(json.dumps(object_row(
                    scene_backgrounds.AUDIO_MAP_DATA_TYPE,
                    [],
                    path_id=5,
                    name="fixture_audio",
                )) + "\n")
            summary = {
                "complete": True,
                "counts": {"objects": 2},
                "outputs": {"objects": {"path": objects_path.name, "sha256": "fixture"}},
                "stageSignature": {"sha256": "stage"},
            }
            with (
                patch.object(
                    scene_backgrounds,
                    "load_animestudio_object_index_summary",
                    return_value=summary,
                ),
                patch.object(
                    scene_backgrounds,
                    "animestudio_object_index_dir",
                    return_value=index_dir,
                ),
            ):
                with self.assertRaisesRegex(
                    scene_backgrounds.SceneBackgroundError,
                    "merged object count mismatch",
                ):
                    scene_backgrounds.collect_scene_background_semantics(
                        root, {}, sources=("StreamingAssets",)
                    )


if __name__ == "__main__":
    unittest.main()
