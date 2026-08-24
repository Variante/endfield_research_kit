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

    def test_asset_map_collected_index_is_reused_without_second_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(json.dumps({
                "GameType": "Endfield",
                "AssetEntries": [
                    {
                        "Name": "GameObject",
                        "Container": "assets/effects/wind.prefab",
                        "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/prefab.chk",
                        "PathID": 99,
                        "Type": "GameObject",
                    },
                    {
                        "Name": "Other",
                        "Container": "assets/effects/other.prefab",
                        "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/other.chk",
                        "PathID": 100,
                        "Type": "GameObject",
                    },
                ],
            }), encoding="utf-8")
            original = scene_backgrounds._iter_asset_map_entries
            with patch.object(
                scene_backgrounds, "_iter_asset_map_entries", wraps=original
            ) as iterator:
                collected = scene_backgrounds._collect_asset_map_containment_index(
                    root, {("assetMap", "root/prefab.chk", 99)}
                )
                first = scene_backgrounds._asset_map_containment_provider(
                    root, [{"source": "VFS/root/prefab.chk", "pathId": 99}],
                    collected_index=collected,
                )
                second = scene_backgrounds._asset_map_containment_provider(
                    root, [{"source": "VFS/root/prefab.chk", "pathId": 99}],
                    collected_index=collected,
                )
        self.assertEqual(iterator.call_count, 1)
        self.assertEqual(len(collected["entries"]), 1)
        self.assertNotIn("other.chk", json.dumps(collected["entries"]))
        self.assertEqual(first["entries"], second["entries"])
        self.assertEqual(first["entries"][0]["sourceAssetPath"], "assets/effects/wind.prefab")

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

    def test_streaming_sidecar_without_prefab_identity_stays_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sidecar = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "map_streaming_instances" / "map01_lv001.json"
            )
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text(json.dumps({
                "schemaVersion": 2,
                "levelId": "map01_lv001",
                "prefabIdentityContract": {
                    "status": "unavailable",
                    "requiredFields": ["source", "pathId"],
                },
                "instances": [{
                    "entityId": 7,
                    "name": "P_not_an_identity",
                    "prefabIdentity": {
                        "status": "exact",
                        "source": "VFS/root/prefab.chk",
                        "pathId": 99,
                    },
                }],
            }), encoding="utf-8")
            result = scene_backgrounds._load_streaming_instance_identity_catalog(root)

        self.assertEqual(result["status"], "unavailablePrefabIdentity")
        self.assertEqual(result["counts"]["instances"], 1)
        self.assertEqual(result["counts"]["exactPrefabIdentityInstances"], 0)
        self.assertEqual(result["entries"], [])
        self.assertTrue(any(
            row["reason"] == "sidecarLacksPrefabIdentityContract"
            for row in result["diagnostics"]
        ))

    def test_streaming_sidecar_accepts_only_explicit_numeric_prefab_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sidecar = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "map_streaming_instances" / "map01_lv001.json"
            )
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text(json.dumps({
                "schemaVersion": 2,
                "levelId": "map01_lv001",
                "prefabIdentityContract": {"status": "exact"},
                "instances": [
                    {
                        "entityId": 7,
                        "prefabIdentity": {
                            "status": "exact",
                            "source": "VFS/root/prefab.chk",
                            "pathId": 99,
                        },
                    },
                    {
                        "entityId": 8,
                        "prefabIdentity": {
                            "status": "exact",
                            "source": "D:/Other/VFS/prefab.chk",
                            "pathId": 100,
                        },
                    },
                ],
            }), encoding="utf-8")
            result = scene_backgrounds._load_streaming_instance_identity_catalog(root)

        self.assertEqual(result["counts"]["exactPrefabIdentityInstances"], 0)
        self.assertEqual(result["counts"]["candidateExactPrefabIdentityInstances"], 1)
        self.assertEqual(result["entries"], [])
        self.assertTrue(any(
            row["reason"] == "exactIdentityMissingSourcePathId"
            for row in result["diagnostics"]
        ))

    def test_streaming_sidecar_schema_mismatch_rejects_exact_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sidecar = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "map_streaming_instances" / "map01_lv001.json"
            )
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text(json.dumps({
                "schemaVersion": 1,
                "levelId": "map01_lv001",
                "prefabIdentityContract": {"status": "exact"},
                "instances": [{
                    "entityId": 7,
                    "prefabIdentity": {
                        "status": "exact",
                        "source": "VFS/root/prefab.chk",
                        "pathId": 99,
                    },
                }],
            }), encoding="utf-8")
            result = scene_backgrounds._load_streaming_instance_identity_catalog(root)
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["counts"]["exactPrefabIdentityInstances"], 0)
        self.assertTrue(any(
            row["reason"] == "sidecarLacksPrefabIdentityContract"
            for row in result["diagnostics"]
        ))

    def test_streaming_valid_exact_sidecar_plus_bad_sibling_blocks_catalog_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sidecar_root = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "map_streaming_instances"
            )
            sidecar_root.mkdir(parents=True)
            valid = {
                "schemaVersion": 2,
                "levelId": "map01_lv001",
                "prefabIdentityContract": {"status": "exact"},
                "instances": [{
                    "entityId": 7,
                    "prefabIdentity": {
                        "status": "exact",
                        "source": "VFS/root/prefab.chk",
                        "pathId": 99,
                    },
                }],
            }
            (sidecar_root / "map01_lv001.json").write_text(
                json.dumps(valid), encoding="utf-8"
            )
            (sidecar_root / "map01_lv002.json").write_text(
                "{not-json", encoding="utf-8"
            )
            result = scene_backgrounds._load_streaming_instance_identity_catalog(root)
        self.assertEqual(result["status"], "unavailablePrefabIdentity")
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["counts"]["exactPrefabIdentityInstances"], 0)
        self.assertEqual(result["counts"]["candidateExactPrefabIdentityInstances"], 1)
        self.assertTrue(any(
            row["status"] == "streamingInstanceSidecarUnreadable"
            for row in result["diagnostics"]
        ))

    def test_streaming_prefab_entry_needs_explicit_emitter_component_identity(self) -> None:
        owner = {
            "serializedFile": "CAB-fixture",
            "source": "VFS/root/emitter.chk",
            "sourceOffset": 10,
            "pathId": 11,
        }
        catalog = {
            "status": "exactPrefabIdentityEntries",
            "authoritativeContractStatus": "validatedAuthoritative",
            "schemaVersion": scene_backgrounds.STREAMING_INSTANCE_CONTRACT_VERSION,
            "sources": [{
                "path": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
                "levelId": "map01_lv001",
                "schemaVersion": 2,
                "prefabIdentityContractStatus": "exact",
            }],
            "counts": {
                "exactPrefabIdentityInstances": 1,
                "malformedInstances": 0,
            },
            "entries": [{
                "levelId": "map01_lv001",
                "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
                "prefabIdentity": {"source": "VFS/root/prefab.chk", "pathId": 99},
                "identityKey": ["assetMap", "root/prefab.chk", 99],
            }],
            "diagnostics": [],
        }
        unresolved = scene_backgrounds._streaming_instance_emitter_projection(owner, catalog)
        self.assertEqual(
            unresolved["status"],
            "unresolvedPrefabEntriesLackEmitterIdentityJoin",
        )
        catalog["entries"][0]["componentIdentity"] = dict(owner)
        exact = scene_backgrounds._streaming_instance_emitter_projection(owner, catalog)
        self.assertEqual(exact["status"], "exactPrefabInstanceToLevel")
        self.assertEqual(exact["levelId"], "map01_lv001")

    def test_streaming_prefab_path_can_join_without_component_identity_only_when_unique(self) -> None:
        owner = {
            "serializedFile": "CAB-fixture",
            "source": "VFS/root/emitter.chk",
            "sourceOffset": 10,
            "pathId": 11,
        }
        catalog = {
            "status": "exactPrefabIdentityEntries",
            "authoritativeContractStatus": "validatedAuthoritative",
            "schemaVersion": scene_backgrounds.STREAMING_INSTANCE_CONTRACT_VERSION,
            "sources": [{
                "path": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
                "levelId": "map01_lv001",
                "schemaVersion": 2,
                "prefabIdentityContractStatus": "exact",
            }],
            "counts": {
                "exactPrefabIdentityInstances": 1,
                "malformedInstances": 0,
            },
            "entries": [{
                "levelId": "map01_lv001",
                "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
                "prefabSourceAssetPath": "assets/effects/wind.prefab",
                "prefabAssetPathStatus": "exactUniqueAssetMapContainer",
                "prefabIdentity": {"source": "VFS/root/prefab.chk", "pathId": 99},
                "identityKey": ["assetMap", "root/prefab.chk", 99],
            }],
            "diagnostics": [],
        }
        exact = scene_backgrounds._streaming_instance_emitter_projection(
            owner, catalog, ["assets/effects/wind.prefab"]
        )
        self.assertEqual(exact["status"], "exactPrefabInstanceToLevel")
        self.assertEqual(exact["levelId"], "map01_lv001")
        catalog["entries"].append({
            "levelId": "map02_lv001",
            "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
            "prefabSourceAssetPath": "assets/effects/wind.prefab",
            "prefabAssetPathStatus": "exactUniqueAssetMapContainer",
            "prefabIdentity": {"source": "VFS/root/prefab2.chk", "pathId": 100},
            "identityKey": ["assetMap", "root/prefab2.chk", 100],
        })
        catalog["counts"]["exactPrefabIdentityInstances"] = 2
        ambiguous = scene_backgrounds._streaming_instance_emitter_projection(
            owner, catalog, ["assets/effects/wind.prefab"]
        )
        self.assertEqual(ambiguous["status"], "unavailablePrefabIdentity")

    def test_streaming_component_and_prefab_path_routes_must_agree(self) -> None:
        owner = {
            "serializedFile": "CAB-fixture",
            "source": "VFS/root/emitter.chk",
            "sourceOffset": 10,
            "pathId": 11,
        }
        catalog = {
            "status": "exactPrefabIdentityEntries",
            "authoritativeContractStatus": "validatedAuthoritative",
            "schemaVersion": scene_backgrounds.STREAMING_INSTANCE_CONTRACT_VERSION,
            "sources": [{
                "path": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
                "levelId": "map01_lv001",
                "schemaVersion": 2,
                "prefabIdentityContractStatus": "exact",
            }, {
                "path": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture2.json",
                "levelId": "map02_lv001",
                "schemaVersion": 2,
                "prefabIdentityContractStatus": "exact",
            }],
            "counts": {"exactPrefabIdentityInstances": 2, "malformedInstances": 0},
            "entries": [
                {
                    "levelId": "map01_lv001",
                    "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture.json",
                    "prefabSourceAssetPath": "assets/effects/wind.prefab",
                    "prefabAssetPathStatus": "exactUniqueAssetMapContainer",
                    "componentIdentity": dict(owner),
                    "prefabIdentity": {"source": "VFS/root/prefab.chk", "pathId": 99},
                    "identityKey": ["assetMap", "root/prefab.chk", 99],
                },
                {
                    "levelId": "map02_lv001",
                    "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/fixture2.json",
                    "prefabSourceAssetPath": "assets/effects/wind.prefab",
                    "prefabAssetPathStatus": "exactUniqueAssetMapContainer",
                    "prefabIdentity": {"source": "VFS/root/prefab2.chk", "pathId": 100},
                    "identityKey": ["assetMap", "root/prefab2.chk", 100],
                },
            ],
            "diagnostics": [],
        }
        result = scene_backgrounds._streaming_instance_emitter_projection(
            owner, catalog, ["assets/effects/wind.prefab"]
        )
        self.assertEqual(result["status"], "conflictingPrefabInstanceIdentityJoins")
        self.assertTrue(any(
            row["reason"] == "componentAndPrefabPathIdentityRoutesDisagree"
            for row in result["diagnostics"]
        ))

    def test_streaming_loader_and_asset_enrichment_produce_authoritative_exact_join(self) -> None:
        owner = {
            "serializedFile": "CAB-fixture",
            "source": "VFS/root/emitter.chk",
            "sourceOffset": 10,
            "pathId": 11,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sidecar = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "map_streaming_instances" / "map01_lv001.json"
            )
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text(json.dumps({
                "schemaVersion": 2,
                "levelId": "map01_lv001",
                "prefabIdentityContract": {"status": "exact"},
                "instances": [{
                    "entityId": 7,
                    "prefabIdentity": {
                        "status": "exact",
                        "source": "VFS/root/prefab.chk",
                        "pathId": 99,
                    },
                }],
            }), encoding="utf-8")
            asset_map = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "fixture_assets.json"
            )
            asset_map.parent.mkdir(parents=True)
            asset_map.write_text(self._asset_map_payload({
                "Name": "GameObject",
                "Container": "assets/effects/wind.prefab",
                "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/prefab.chk",
                "PathID": 99,
                "Type": "GameObject",
            }), encoding="utf-8")
            catalog = scene_backgrounds._load_streaming_instance_identity_catalog(root)
            enriched = scene_backgrounds._enrich_streaming_instance_asset_paths(
                root, catalog
            )
            projection = scene_backgrounds._streaming_instance_emitter_projection(
                owner, enriched, ["assets/effects/wind.prefab"]
            )
            compact = scene_backgrounds.project_scene_emitter_compact_attribution(
                [{
                    "kind": "sceneEmitterAudioEvent",
                    "semanticRole": "authoredAmbientEmitterCandidate",
                    "owner": dict(owner),
                    "eventHash": 123,
                    "confidence": "direct",
                    "sceneContainmentStatus": "missingSceneAssetLevelContainment",
                    "streamingPrefabInstanceStatus": projection["status"],
                    "streamingPrefabInstanceLevelId": projection["levelId"],
                    "streamingPrefabInstanceEvidence": projection["entries"],
                }],
                {
                    "status": "validatedPublishedObjectIndex",
                    "scenes": [{"sceneId": "map01_lv001"}],
                },
                enriched,
            )
        self.assertEqual(
            enriched["authoritativeContractStatus"],
            scene_backgrounds.STREAMING_INSTANCE_AUTHORITATIVE_STATUS,
        )
        self.assertEqual(projection["status"], "exactPrefabInstanceToLevel")
        self.assertEqual(projection["levelId"], "map01_lv001")
        self.assertEqual(compact["sceneEmitterAttributionStatus"], "exactSceneAttribution")
        self.assertEqual(compact["sceneEmitterSceneIds"], ["map01_lv001"])

    def test_unavailable_streaming_provider_rejects_exact_looking_entries(self) -> None:
        owner = {
            "serializedFile": "CAB-fixture",
            "source": "VFS/root/emitter.chk",
            "sourceOffset": 10,
            "pathId": 11,
        }
        catalog = {
            "schemaVersion": scene_backgrounds.STREAMING_INSTANCE_CONTRACT_VERSION,
            "status": "unavailablePrefabIdentity",
            "authoritativeContractStatus": "validatedAuthoritative",
            "sources": [{
                "path": "fixture.json",
                "levelId": "map01_lv001",
                "schemaVersion": 2,
                "prefabIdentityContractStatus": "exact",
            }],
            "counts": {
                "exactPrefabIdentityInstances": 1,
                "malformedInstances": 0,
            },
            "entries": [{
                "levelId": "map01_lv001",
                "prefabSourceAssetPath": "assets/effects/wind.prefab",
                "prefabAssetPathStatus": "exactUniqueAssetMapContainer",
                "prefabIdentity": {
                    "source": "VFS/root/prefab.chk",
                    "pathId": 99,
                },
                "identityKey": ["assetMap", "root/prefab.chk", 99],
            }],
            "diagnostics": [],
        }
        catalog["status"] = "unavailablePrefabIdentity"
        projection = scene_backgrounds._streaming_instance_emitter_projection(
            owner, catalog, ["assets/effects/wind.prefab"]
        )
        self.assertEqual(projection["status"], "unavailablePrefabIdentity")
        self.assertTrue(any(
            row.get("reason") == "providerContractNotValidatedAuthoritative"
            for row in projection["diagnostics"]
        ))

    def test_streaming_prefab_identity_resolves_full_asset_map_container_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            map_path.write_text(self._asset_map_payload({
                "Name": "GameObject",
                "Container": "assets/effects/wind.prefab",
                "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/prefab.chk",
                "PathID": 99,
                "Type": "GameObject",
            }), encoding="utf-8")
            catalog = {
                "status": "exactPrefabIdentityEntries",
                "authoritativeContractStatus": "validatedAuthoritative",
                "schemaVersion": scene_backgrounds.STREAMING_INSTANCE_CONTRACT_VERSION,
                "sources": [{
                    "path": "fixture.json",
                    "levelId": "map01_lv001",
                    "schemaVersion": 2,
                    "prefabIdentityContractStatus": "exact",
                }],
                "counts": {
                    "exactPrefabIdentityInstances": 1,
                    "malformedInstances": 0,
                },
                "entries": [{
                    "levelId": "map01_lv001",
                    "prefabIdentity": {
                        "status": "exact",
                        "source": "VFS/root/prefab.chk",
                        "pathId": 99,
                    },
                    "identityKey": ["assetMap", "root/prefab.chk", 99],
                }],
                "diagnostics": [],
            }
            enriched = scene_backgrounds._enrich_streaming_instance_asset_paths(root, catalog)

        self.assertEqual(
            enriched["entries"][0]["prefabSourceAssetPath"],
            "assets/effects/wind.prefab",
        )
        self.assertEqual(
            enriched["entries"][0]["prefabAssetPathStatus"],
            "exactUniqueAssetMapContainer",
        )

    def test_streaming_prefab_duplicate_asset_map_rows_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            row = {
                "Name": "GameObject",
                "Container": "assets/effects/wind.prefab",
                "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/prefab.chk",
                "PathID": 99,
                "Type": "GameObject",
            }
            map_path.write_text(json.dumps({
                "GameType": "Endfield", "AssetEntries": [row, dict(row)]
            }), encoding="utf-8")
            catalog = {
                "status": "exactPrefabIdentityEntries",
                "entries": [{
                    "levelId": "map01_lv001",
                    "prefabIdentity": {
                        "status": "exact",
                        "source": "VFS/root/prefab.chk",
                        "pathId": 99,
                    },
                }],
                "diagnostics": [],
            }
            enriched = scene_backgrounds._enrich_streaming_instance_asset_paths(root, catalog)
        entry = enriched["entries"][0]
        self.assertEqual(entry["prefabAssetPathStatus"], "duplicateAssetMapIdentityRows")
        self.assertEqual(enriched["assetMapResolution"]["duplicateIdentityRowCount"], 1)
        self.assertTrue(any(
            row["reason"] == "multipleAssetMapRowsForSameSourcePathId"
            for row in enriched["assetMapResolution"]["diagnostics"]
        ))

    def test_streaming_prefab_and_unity_container_family_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            base = {
                "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/prefab.chk",
                "PathID": 99,
                "Type": "GameObject",
            }
            rows = [
                {**base, "Container": "assets/effects/wind.prefab"},
                {**base, "Container": "assets/scenes/map01.unity"},
            ]
            map_path.write_text(json.dumps({"GameType": "Endfield", "AssetEntries": rows}), encoding="utf-8")
            catalog = {
                "status": "exactPrefabIdentityEntries",
                "entries": [{
                    "levelId": "map01_lv001",
                    "prefabIdentity": {
                        "status": "exact", "source": "VFS/root/prefab.chk", "pathId": 99
                    },
                }],
                "diagnostics": [],
            }
            enriched = scene_backgrounds._enrich_streaming_instance_asset_paths(root, catalog)
        self.assertEqual(
            enriched["entries"][0]["prefabAssetPathStatus"],
            "conflictingAssetMapContainerFamilies",
        )
        self.assertNotIn("prefabSourceAssetPath", enriched["entries"][0])

    def test_streaming_prefab_and_other_container_family_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = (
                root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "maps" / "endfield_streamingassets_assets.json"
            )
            map_path.parent.mkdir(parents=True)
            base = {
                "Source": "D:/Game/Endfield_Data/StreamingAssets/VFS/root/prefab.chk",
                "PathID": 99,
                "Type": "GameObject",
            }
            rows = [
                {**base, "Container": "assets/effects/wind.prefab"},
                {**base, "Container": "assets/effects/wind.assetbundle"},
            ]
            map_path.write_text(json.dumps({"GameType": "Endfield", "AssetEntries": rows}), encoding="utf-8")
            catalog = {
                "status": "exactPrefabIdentityEntries",
                "entries": [{
                    "levelId": "map01_lv001",
                    "prefabIdentity": {
                        "status": "exact", "source": "VFS/root/prefab.chk", "pathId": 99
                    },
                }],
                "diagnostics": [],
            }
            enriched = scene_backgrounds._enrich_streaming_instance_asset_paths(root, catalog)
        self.assertEqual(
            enriched["entries"][0]["prefabAssetPathStatus"],
            "conflictingAssetMapContainerFamilies",
        )
        self.assertNotIn("prefabSourceAssetPath", enriched["entries"][0])


class SceneGlobalCompactAttributionTests(unittest.TestCase):
    CATALOG = {
        "status": "validatedPublishedObjectIndex",
        "scenes": [{"sceneId": "map01_lv001"}, {"sceneId": "map02_lv002"}],
    }
    MAP_OWNER = {
        "serializedFile": "CAB-map",
        "source": "VFS/map.chk",
        "sourceOffset": 10,
        "pathId": 7,
    }

    @classmethod
    def context(cls, **overrides: object) -> dict:
        context = {
            "kind": "sceneGlobalAudioEvent",
            "semanticRole": "levelInitEvents",
            "source": "StreamingAssets",
            "owner": dict(cls.MAP_OWNER),
            "eventHash": 123,
            "confidence": "direct",
            "evidence": "exactAudioMapDataSceneIndex",
            "sceneId": "map01_lv001",
            "triggerRuntimeActivationStatuses": [
                "authoredDefinitionOnly",
                "runtimeActivationNotObserved",
                "wwiseBranchSelectionNotObserved",
            ],
        }
        context.update(overrides)
        return context

    def test_exact_multi_scene_keeps_all_ids_and_original_roles(self) -> None:
        result = scene_backgrounds.project_scene_global_compact_attribution(
            [
                self.context(),
                self.context(sceneId="map02_lv002", semanticRole="levelExitEvents"),
            ],
            self.CATALOG,
        )
        self.assertEqual(result["sceneGlobalContextStatus"], "exact")
        self.assertEqual(result["sceneGlobalSceneIds"], ["map01_lv001", "map02_lv002"])
        self.assertEqual(result["sceneGlobalSemanticRoles"], ["levelExitEvents", "levelInitEvents"])
        self.assertNotIn("sceneKeys", result)

    def test_audio_level_row_is_an_exact_alternate_producer(self) -> None:
        result = scene_backgrounds.project_scene_global_compact_attribution(
            [self.context(
                source="structured/StreamingAssets/Table/AudioLevel.json",
                owner={"table": "AudioLevel", "levelId": "map01_lv001"},
                evidence="exactAudioLevelRow",
                semanticRole="levelInitEvent",
            )],
            self.CATALOG,
        )
        self.assertEqual(result["sceneGlobalContextStatus"], "exact")
        self.assertEqual(result["sceneGlobalSemanticRoles"], ["levelInitEvent"])

    def test_audio_level_source_requires_one_canonical_normalized_path(self) -> None:
        for source in (
            "structured/persistent/Table/AudioLevel.json",
            "structured\\Persistent\\Table\\AudioLevel.json",
            "structured/Persistent/Wrapper/Table/AudioLevel.json",
            "structured/Persistent/Table/AudioLevel.json/extra",
        ):
            result = scene_backgrounds.project_scene_global_compact_attribution(
                [self.context(
                    source=source,
                    owner={"table": "AudioLevel", "levelId": "map01_lv001"},
                    evidence="exactAudioLevelRow",
                    semanticRole="levelInitEvent",
                )],
                self.CATALOG,
            )
            self.assertEqual(result["sceneGlobalContextStatus"], "unavailable")
            self.assertNotIn("sceneGlobalSceneIds", result)
            self.assertEqual(
                result["sceneGlobalContextDiagnostics"][0]["reason"],
                "audioLevelSourcePathMismatch",
            )

    def test_empty_contexts_do_not_publish_compact_fields(self) -> None:
        self.assertEqual(
            scene_backgrounds.project_scene_global_compact_attribution([], self.CATALOG),
            {},
        )

    def test_truncated_or_non_direct_context_fails_closed(self) -> None:
        cases = (
            (self.context(), {"contexts_truncated": True}),
            (self.context(confidence="inferred"), {}),
        )
        for context, kwargs in cases:
            result = scene_backgrounds.project_scene_global_compact_attribution(
                [context], self.CATALOG, **kwargs
            )
            self.assertEqual(result["sceneGlobalContextStatus"], "unavailable")
            self.assertNotIn("sceneGlobalSceneIds", result)
            self.assertNotIn("sceneGlobalSemanticRoles", result)
            self.assertLessEqual(
                len(result["sceneGlobalContextDiagnostics"]),
                scene_backgrounds.SCENE_GLOBAL_COMPACT_DIAGNOSTIC_LIMIT,
            )

    def test_malformed_source_owner_evidence_and_scene_fail_closed(self) -> None:
        cases = (
            {"source": "", "reason": "missingSource"},
            {"owner": {"pathId": 7}, "reason": "audioMapOwnerIdentityIncomplete"},
            {"evidence": "inferredAudioMap", "reason": "sceneGlobalEvidenceNotExact"},
            {"sceneId": "not_in_catalog", "reason": "sceneGlobalSceneNotInCatalog"},
            {"triggerRuntimeActivationStatuses": [None], "reason": "sceneGlobalRuntimeStatusIncomplete"},
        )
        for overrides in cases:
            result = scene_backgrounds.project_scene_global_compact_attribution(
                [self.context(**{key: value for key, value in overrides.items() if key != "reason"})],
                self.CATALOG,
            )
            self.assertEqual(result["sceneGlobalContextStatus"], "unavailable")
            self.assertIn(
                overrides["reason"],
                {row["reason"] for row in result["sceneGlobalContextDiagnostics"]},
            )

    def test_diagnostics_are_bounded_while_total_count_is_retained(self) -> None:
        contexts = [
            self.context(
                source="structured/Persistent/Table/AudioLevel.json",
                owner={"table": "AudioLevel", "levelId": "missing"},
                evidence="exactAudioLevelRow",
                sceneId="missing",
            )
            for _ in range(20)
        ]
        result = scene_backgrounds.project_scene_global_compact_attribution(
            contexts, self.CATALOG
        )
        self.assertEqual(result["sceneGlobalContextStatus"], "unavailable")
        self.assertEqual(
            len(result["sceneGlobalContextDiagnostics"]),
            scene_backgrounds.SCENE_GLOBAL_COMPACT_DIAGNOSTIC_LIMIT,
        )
        self.assertGreater(
            result["sceneGlobalContextDiagnosticCount"],
            len(result["sceneGlobalContextDiagnostics"]),
        )

    def test_invalid_catalog_is_not_replaced_by_context_scene_id(self) -> None:
        result = scene_backgrounds.project_scene_global_compact_attribution(
            [self.context()],
            {"status": "unavailable", "scenes": [{"sceneId": "map01_lv001"}]},
        )
        self.assertEqual(result["sceneGlobalContextStatus"], "unavailable")
        self.assertNotIn("sceneGlobalSceneIds", result)


class SceneEmitterCompactAttributionTests(unittest.TestCase):
    CATALOG = {
        "status": "validatedPublishedObjectIndex",
        "scenes": [
            {"sceneId": "map01_lv001"},
            {"sceneId": "map02_lv002"},
        ],
    }
    OWNER = {
        "serializedFile": "CAB-emitter",
        "source": "VFS/emitter.chk",
        "sourceOffset": 10,
        "pathId": 7,
    }

    @classmethod
    def context(cls, **overrides: object) -> dict:
        context = {
            "kind": "sceneEmitterAudioEvent",
            "semanticRole": "authoredAmbientEmitterCandidate",
            "owner": dict(cls.OWNER),
            "eventHash": 123,
            "confidence": "direct",
            "sceneContainmentStatus": "prefabLocalNotSceneContained",
            "streamingPrefabInstanceStatus": "unavailablePrefabIdentity",
        }
        context.update(overrides)
        return context

    @classmethod
    def exact_scene_context(
        cls,
        scene_id: str = "map01_lv001",
        **overrides: object,
    ) -> dict:
        context = cls.context(
            sceneContainmentStatus="exactSceneAssetLevelContainment",
            sceneId=scene_id,
            sourceName=f"{scene_id}.unity",
            sourcePath=f"Assets/Scenes/{scene_id}.unity",
            sceneContainmentEvidence={
                "kind": "exactSceneAssetLevelContainment",
                "relation": "explicitObjectIdentityToSceneAssetLevel",
                "identity": dict(cls.OWNER),
                "containmentType": "SceneAsset",
            },
        )
        context.update(overrides)
        return context

    @classmethod
    def exact_streaming_catalog(cls, level_id: str = "map02_lv002") -> dict:
        return {
            "schemaVersion": scene_backgrounds.STREAMING_INSTANCE_CONTRACT_VERSION,
            "status": "exactPrefabIdentityEntries",
            "authoritativeContractStatus": "validatedAuthoritative",
            "sources": [{
                "path": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json",
                "levelId": level_id,
                "schemaVersion": 2,
                "prefabIdentityContractStatus": "exact",
            }],
            "counts": {
                "exactPrefabIdentityInstances": 1,
                "malformedInstances": 0,
            },
            "entries": [{
                "levelId": level_id,
                "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json",
                "prefabIdentity": {
                    "source": "VFS/root/prefab.chk",
                    "pathId": 19,
                },
                "identityKey": ["assetMap", "root/prefab.chk", 19],
            }],
            "diagnostics": [],
        }

    def test_current_prefab_local_negative_projection_is_compact_and_non_exact(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(), self.context(owner={**self.OWNER, "pathId": 8})],
            self.CATALOG,
        )
        self.assertEqual(
            result["sceneEmitterAttributionStatus"],
            "prefabLocalSceneUnresolved",
        )
        self.assertEqual(
            result["sceneEmitterSceneContainmentStatuses"],
            ["prefabLocalNotSceneContained"],
        )
        self.assertEqual(
            result["sceneEmitterStreamingPrefabIdentityStatuses"],
            ["unavailablePrefabIdentity"],
        )
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_exact_scene_containment_is_the_only_scene_id_from_scene_side(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.exact_scene_context()],
            self.CATALOG,
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "exactSceneAttribution")
        self.assertEqual(result["sceneEmitterSceneIds"], ["map01_lv001"])

    def test_real_containment_producer_shape_promotes_through_projector(self) -> None:
        raw_index = {"entries": [{
            "identity": dict(self.OWNER),
            "sceneId": "map01_lv001",
            "sourceName": "map01_lv001.unity",
            "sourcePath": "Assets/Scenes/map01_lv001.unity",
            "containmentType": "SceneAsset",
        }]}
        normalized, diagnostics = scene_backgrounds._normalise_scene_containment_index(
            raw_index
        )
        containment = scene_backgrounds._resolve_scene_emitter_containment(
            self.OWNER,
            None,
            normalized,
            index_diagnostics=diagnostics,
        )
        produced_context = scene_backgrounds._event_context(
            source="StreamingAssets",
            owner=dict(self.OWNER),
            role="authoredAmbientEmitterCandidate",
            event_hash=123,
            kind="sceneEmitterAudioEvent",
            scene_containment=containment,
        )
        produced_context["streamingPrefabInstanceStatus"] = "unavailablePrefabIdentity"
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [produced_context], self.CATALOG
        )
        self.assertEqual(containment["status"], "exactSceneAssetLevelContainment")
        self.assertEqual(
            produced_context["sceneContainmentEvidence"],
            containment["sceneContainmentEvidence"],
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "exactSceneAttribution")
        self.assertEqual(result["sceneEmitterSceneIds"], ["map01_lv001"])

    def test_missing_or_malformed_containment_evidence_never_promotes(self) -> None:
        for evidence in (None, {}, {
            "kind": "exactSceneAssetLevelContainment",
            "relation": "explicitObjectIdentityToSceneAssetLevel",
            "identity": {**self.OWNER, "pathId": 999},
            "containmentType": "SceneAsset",
        }):
            with self.subTest(evidence=evidence):
                context = self.exact_scene_context(
                    sceneContainmentEvidence=evidence,
                )
                result = scene_backgrounds.project_scene_emitter_compact_attribution(
                    [context], self.CATALOG
                )
                self.assertEqual(
                    result["sceneEmitterAttributionStatus"],
                    "sceneEmitterAttributionUnavailable",
                )
                self.assertNotIn("sceneEmitterSceneIds", result)

    def test_exact_prefab_identity_is_required_before_streaming_level_promotion(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(
                sceneContainmentStatus="missingSceneAssetLevelContainment",
                streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                streamingPrefabInstanceLevelId="map02_lv002",
                streamingPrefabInstanceEvidence=[{
                    "levelId": "map02_lv002",
                    "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json",
                    "prefabIdentity": {"source": "VFS/root/prefab.chk", "pathId": 19},
                    "identityKey": ["assetMap", "root/prefab.chk", 19],
                }],
            )],
            self.CATALOG,
            self.exact_streaming_catalog(),
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "exactSceneAttribution")
        self.assertEqual(result["sceneEmitterSceneIds"], ["map02_lv002"])

    def test_exact_prefab_compact_promotion_rejects_malformed_provider_contract(self) -> None:
        catalog = self.exact_streaming_catalog()
        catalog.pop("authoritativeContractStatus")
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(
                sceneContainmentStatus="missingSceneAssetLevelContainment",
                streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                streamingPrefabInstanceLevelId="map02_lv002",
                streamingPrefabInstanceEvidence=[{
                    "levelId": "map02_lv002",
                    "prefabIdentity": {
                        "source": "VFS/root/prefab.chk",
                        "pathId": 19,
                    },
                    "identityKey": ["assetMap", "root/prefab.chk", 19],
                }],
            )],
            self.CATALOG,
            catalog,
        )
        self.assertEqual(
            result["sceneEmitterAttributionStatus"],
            "sceneEmitterAttributionUnavailable",
        )
        self.assertNotIn("sceneEmitterSceneIds", result)
        self.assertTrue(any(
            row.get("reason") == "streamingPrefabIdentityCatalogUnavailable"
            for row in result["sceneEmitterAttributionDiagnostics"]
        ))

    def test_exact_catalog_requires_canonical_sidecar_provenance(self) -> None:
        catalog = self.exact_streaming_catalog()
        catalog["entries"][0].pop("sidecarPath")
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(
                sceneContainmentStatus="missingSceneAssetLevelContainment",
                streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                streamingPrefabInstanceLevelId="map02_lv002",
                streamingPrefabInstanceEvidence=[{
                    "levelId": "map02_lv002",
                    "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json",
                    "prefabIdentity": {
                        "source": "VFS/root/prefab.chk",
                        "pathId": 19,
                    },
                    "identityKey": ["assetMap", "root/prefab.chk", 19],
                }],
            )],
            self.CATALOG,
            catalog,
        )
        self.assertEqual(
            result["sceneEmitterAttributionStatus"],
            "sceneEmitterAttributionUnavailable",
        )
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_canonical_sidecar_path_rejects_extra_segments_and_nonterminal_json(self) -> None:
        canonical = "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json"
        self.assertEqual(
            scene_backgrounds._canonical_streaming_sidecar_path(canonical),
            canonical,
        )
        for path in (
            "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/nested/map.json",
            "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json/",
            "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/./map.json",
            "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json.bak",
        ):
            with self.subTest(path=path):
                self.assertIsNone(
                    scene_backgrounds._canonical_streaming_sidecar_path(path)
                )

    def test_same_sidecar_path_for_multiple_levels_blocks_authoritative_catalog(self) -> None:
        catalog = self.exact_streaming_catalog()
        catalog["sources"].append({
            "path": catalog["sources"][0]["path"],
            "levelId": "map03_lv003",
            "schemaVersion": 2,
            "prefabIdentityContractStatus": "exact",
        })
        duplicate = dict(catalog["entries"][0])
        duplicate["levelId"] = "map03_lv003"
        catalog["entries"].append(duplicate)
        catalog["counts"]["exactPrefabIdentityInstances"] = 2
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(
                sceneContainmentStatus="missingSceneAssetLevelContainment",
                streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                streamingPrefabInstanceLevelId="map02_lv002",
                streamingPrefabInstanceEvidence=[catalog["entries"][0]],
            )],
            self.CATALOG,
            catalog,
        )
        self.assertEqual(
            result["sceneEmitterAttributionStatus"],
            "sceneEmitterAttributionUnavailable",
        )
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_exact_prefab_evidence_must_join_catalog_identity_and_level(self) -> None:
        for catalog, evidence in (
            (
                self.exact_streaming_catalog("map03_lv003"),
                [{
                    "levelId": "map02_lv002",
                    "prefabIdentity": {
                        "source": "VFS/root/prefab.chk",
                        "pathId": 19,
                    },
                    "identityKey": ["assetMap", "root/prefab.chk", 19],
                }],
            ),
            (
                self.exact_streaming_catalog(),
                [{
                    "levelId": "map02_lv002",
                    "prefabIdentity": {
                        "source": "VFS/root/missing.chk",
                        "pathId": 999,
                    },
                    "identityKey": ["assetMap", "root/missing.chk", 999],
                }],
            ),
            (
                self.exact_streaming_catalog(),
                [{
                    "levelId": "map02_lv002",
                    "sidecarPath": "other-sidecar.json",
                    "prefabIdentity": {
                        "source": "VFS/root/prefab.chk",
                        "pathId": 19,
                    },
                    "identityKey": ["assetMap", "root/prefab.chk", 19],
                }],
            ),
        ):
            with self.subTest(catalog=catalog, evidence=evidence):
                result = scene_backgrounds.project_scene_emitter_compact_attribution(
                    [self.context(
                        sceneContainmentStatus="missingSceneAssetLevelContainment",
                        streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                        streamingPrefabInstanceLevelId="map02_lv002",
                        streamingPrefabInstanceEvidence=evidence,
                    )],
                    self.CATALOG,
                    catalog,
                )
                self.assertEqual(
                    result["sceneEmitterAttributionStatus"],
                    "sceneEmitterAttributionUnavailable",
                )
                self.assertNotIn("sceneEmitterSceneIds", result)

    def test_duplicate_catalog_identity_blocks_exact_promotion(self) -> None:
        catalog = self.exact_streaming_catalog()
        duplicate = dict(catalog["entries"][0])
        catalog["entries"].append(duplicate)
        catalog["counts"]["exactPrefabIdentityInstances"] = 2
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(
                sceneContainmentStatus="missingSceneAssetLevelContainment",
                streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                streamingPrefabInstanceLevelId="map02_lv002",
                streamingPrefabInstanceEvidence=[duplicate],
            )],
            self.CATALOG,
            catalog,
        )
        self.assertEqual(
            result["sceneEmitterAttributionStatus"],
            "sceneEmitterAttributionUnavailable",
        )
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_candidate_only_path_position_and_sidecar_level_do_not_make_scene_id(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [self.context(
                sceneContainmentStatus="sceneAssetContainerWithoutAuthoritativeSceneId",
                streamingPrefabInstanceStatus="unavailablePrefabIdentity",
                streamingPrefabInstanceLevelId="map03_lv003",
                sourceAssetPath="Assets/Scenes/map03_lv003.unity",
                placement={"worldPosition": {"x": 1, "y": 2, "z": 3}},
                sceneContainmentDiagnostics=[{
                    "candidates": [{"sourceAssetPath": "Assets/Scenes/map03_lv003.unity"}],
                }],
            )],
            self.CATALOG,
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "sceneEmitterAttributionUnavailable")
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_mixed_exact_scene_and_prefab_attributions_fail_closed(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [
                self.context(
                    **self.exact_scene_context(),
                ),
                self.context(
                    sceneContainmentStatus="missingSceneAssetLevelContainment",
                    streamingPrefabInstanceStatus="exactPrefabInstanceToLevel",
                    streamingPrefabInstanceLevelId="map02_lv002",
                    streamingPrefabInstanceEvidence=[{
                        "levelId": "map02_lv002",
                        "sidecarPath": "recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances/map.json",
                        "prefabIdentity": {"source": "VFS/root/prefab.chk", "pathId": 19},
                        "identityKey": ["assetMap", "root/prefab.chk", 19],
                    }],
                ),
            ],
            self.CATALOG,
            self.exact_streaming_catalog(),
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "sceneEmitterAttributionConflict")
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_exact_owner_mixed_with_unresolved_owner_fails_closed(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [
                self.context(
                    **self.exact_scene_context(),
                ),
                self.context(owner={**self.OWNER, "pathId": 8}),
            ],
            self.CATALOG,
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "sceneEmitterAttributionConflict")
        self.assertNotIn("sceneEmitterSceneIds", result)

    def test_malformed_or_non_direct_context_is_unavailable_with_bounded_diagnostics(self) -> None:
        result = scene_backgrounds.project_scene_emitter_compact_attribution(
            [None, self.context(confidence="inferred"), self.context(owner={})],
            self.CATALOG,
        )
        self.assertEqual(result["sceneEmitterAttributionStatus"], "sceneEmitterAttributionUnavailable")
        self.assertNotIn("sceneEmitterSceneIds", result)
        self.assertLessEqual(
            len(result["sceneEmitterAttributionDiagnostics"]),
            scene_backgrounds.SCENE_EMITTER_COMPACT_DIAGNOSTIC_LIMIT,
        )
        self.assertGreaterEqual(
            result["sceneEmitterAttributionDiagnosticCount"],
            len(result["sceneEmitterAttributionDiagnostics"]),
        )


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

    def test_missing_source_preserves_independently_validated_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            index_dir = root / "persistent-index"
            index_dir.mkdir()
            objects_path = index_dir / "objects.jsonl.gz"
            with gzip.open(objects_path, "wt", encoding="utf-8") as stream:
                stream.write(json.dumps(object_row(
                    scene_backgrounds.AUDIO_MAP_DATA_TYPE,
                    [["$.levelGlobalEvents._sceneNames[0]", "s", "map01_lv001"]],
                    path_id=6,
                    name="persistent_audio",
                )) + "\n")
            summary = {
                "complete": True,
                "counts": {"objects": 1},
                "outputs": {"objects": {"path": objects_path.name, "sha256": "fixture"}},
                "stageSignature": {"sha256": "stage"},
            }

            def load_summary(_root: Path, source: str) -> dict[str, object] | None:
                return summary if source == "Persistent" else None

            with (
                patch.object(
                    scene_backgrounds,
                    "load_animestudio_object_index_summary",
                    side_effect=load_summary,
                ),
                patch.object(
                    scene_backgrounds,
                    "animestudio_object_index_dir",
                    return_value=index_dir,
                ),
            ):
                result = scene_backgrounds.collect_scene_background_semantics(
                    root, {}, sources=("StreamingAssets", "Persistent")
                )

            self.assertEqual(result["status"], "validatedPartialPublishedObjectIndex")
            self.assertEqual(result["counts"]["requestedObjectIndexSources"], 2)
            self.assertEqual(result["counts"]["validatedObjectIndexSources"], 1)
            self.assertEqual(result["counts"]["unavailableObjectIndexSources"], 1)
            self.assertEqual(
                result["counts"]["objectRowsScannedBySource"], {"Persistent": 1}
            )
            self.assertEqual(result["sources"][0]["source"], "Persistent")
            self.assertEqual(result["sourceDiagnostics"], [{
                "source": "StreamingAssets",
                "status": "missingPublishedObjectIndex",
                "diagnostic": (
                    "StreamingAssets: no published object index; run an installed-game "
                    "Story/all export with --animestudio-object-index"
                ),
            }])
            self.assertEqual(result["scenes"][0]["sceneId"], "map01_lv001")
            self.assertIn("no cross-source identity", result["evidenceBoundary"])

    def test_all_missing_sources_still_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(
                scene_backgrounds,
                "load_animestudio_object_index_summary",
                return_value=None,
            ):
                with self.assertRaisesRegex(
                    scene_backgrounds.SceneBackgroundError,
                    "no published object index",
                ):
                    scene_backgrounds.collect_scene_background_semantics(
                        Path(temporary), {}, sources=("StreamingAssets", "Persistent")
                    )

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
