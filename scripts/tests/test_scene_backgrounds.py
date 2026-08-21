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
