import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from struct import pack


SCRIPT = Path(__file__).resolve().parents[1] / "build_audio_semantics.py"
SPEC = importlib.util.spec_from_file_location("build_audio_semantics_test", SCRIPT)
audio_semantics = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audio_semantics)


def mp_string(value: str | None) -> bytes:
    if value is None:
        return pack("<I", 0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return pack("<I", len(encoded)) + encoded


def spawner_enemy_item(event_id: str, *, enemy_id: str, template_id: str | None, effect_id: str, time: float) -> bytes:
    return (
        b"\x0d\xff"
        + pack("<I", 0)
        + mp_string(template_id)
        + mp_string(enemy_id)
        + pack("<i", 20)
        + b"\x00"
        + mp_string("fixture-key")
        + mp_string(None)
        + pack("<i", 0)
        + mp_string(event_id)
        + pack("<ffff", 0.0, 0.0, 0.0, 1.0)
        + mp_string(effect_id)
        + pack("<f", time)
    )


def spawner_config_fixture() -> bytes:
    rows = [
        spawner_enemy_item(
            "au_interactive_monsterspawn_white_2s",
            enemy_id="eny_0018_lbtough_train",
            template_id=None,
            effect_id="P_monsterspawn_summon_02_2s",
            time=2.0,
        ),
        spawner_enemy_item(
            "au_int_electric_fence_hit",
            enemy_id="eny_fixture",
            template_id="eny_template_fixture",
            effect_id="P_monsterspawn_summon_01_1s",
            time=1.0,
        ),
    ]
    return b"\x05" + mp_string("sc_fixture") + pack("<I", len(rows)) + b"".join(rows) + b"unused-tail"


class AudioSemanticDataTests(unittest.TestCase):
    def test_direct_and_content_equivalent_media_keep_honest_counts(self) -> None:
        media = []
        for media_id in (10, 11):
            media.append({
                "id": "au_sfx_same",
                "eventId": "au_sfx_same",
                "eventHash": 5,
                "mediaId": media_id,
                "src": f"/audio/{media_id}.flac",
                "rel": f"wwise/sfx/{media_id}.flac",
                "contentSha256": "abc",
                "wwiseMediaEvidence": [{
                    "rootActionIds": [7],
                    "soundObjectCount": 1,
                    "relationTypes": ["directSound"],
                    "bankId": 9,
                }],
            })
        rows, _, _ = audio_semantics.build_event_rows({
            "eventNames": ["au_sfx_same"],
            "events": media,
            "eventEvidence": [{
                "eventId": "au_sfx_same",
                "eventHash": 5,
                "bankId": 9,
                "actionIds": [7],
                "rootPlayActionCount": 1,
                "traversalStatus": "complete",
                "mediaIds": [10, 11],
            }],
        }, {})
        event = rows[0]
        self.assertEqual(event["possibleMediaCount"], 2)
        self.assertEqual(event["uniqueDecodedContentCount"], 1)
        self.assertEqual(event["contentEquivalentLeafCount"], 1)
        self.assertEqual(event["runtimeSelection"], "multiplePossibleMediaUnresolved")
        self.assertEqual([row["contentEquivalentCount"] for row in event["media"]], [2, 2])

    def test_event_categories_preserve_unknowns(self) -> None:
        self.assertEqual(audio_semantics.event_category("au_sfx_test"), "sfx")
        self.assertEqual(audio_semantics.event_category("au_chr_test_attack"), "sfx")
        self.assertEqual(audio_semantics.event_category("au_eny_test_hit"), "sfx")
        self.assertEqual(audio_semantics.event_category("au_music_test"), "music")
        self.assertEqual(audio_semantics.event_category("au_amb_wind"), "ambience")
        self.assertEqual(audio_semantics.event_category("au_rtpc_speed"), "control")
        self.assertEqual(audio_semantics.event_category("au_vibration_test"), "control")
        self.assertEqual(audio_semantics.event_category("unproven_name"), "unknown")

    def test_missing_metadata_degrades_without_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            model = audio_semantics.build_runtime_model(None, Path(raw_root))
        self.assertEqual(model["status"], "degraded")
        self.assertEqual(model["systems"], [])
        self.assertEqual(
            len(model["missingTypes"]),
            len(audio_semantics.RUNTIME_SYSTEM_SPECS),
        )

    def test_runtime_model_covers_ability_sound_request_and_lifecycle(self) -> None:
        specs = {row["type"]: row for row in audio_semantics.RUNTIME_SYSTEM_SPECS}
        action = specs["Beyond.Gameplay.Core.PlaySoundAction"]
        data = specs["Beyond.Gameplay.Core.PlaySoundAction+PlaySoundActionData"]

        self.assertEqual(action["layer"], "skill_actions")
        self.assertIn("m_audioInstanceIds", action["fields"])
        self.assertIn("_DoPostEventAtPosition", action["methods"])
        self.assertIn("_StopAllSoundInstance", action["methods"])
        self.assertEqual(data["layer"], "skill_actions")
        self.assertIn("_soundEvent", data["fields"])
        self.assertIn("targetSettings", data["fields"])
        self.assertIn("useWeaponMountPoint", data["fields"])
        self.assertIn("useTimeDilationPauseAndSeek", data["fields"])

    def test_runtime_cache_schema_invalidates_changed_system_catalog(self) -> None:
        stale = {
            "schemaVersion": audio_semantics.RUNTIME_MODEL_CACHE_SCHEMA_VERSION - 1,
            "sourceFingerprint": {"sha256": "fixture", "size": 7},
            "runtimeModel": {"systems": [{"type": "stale"}]},
        }
        self.assertIsNone(audio_semantics._runtime_cache_hit(stale, "fixture", 7))
        stale["schemaVersion"] = audio_semantics.RUNTIME_MODEL_CACHE_SCHEMA_VERSION
        self.assertEqual(
            audio_semantics._runtime_cache_hit(stale, "fixture", 7),
            stale["runtimeModel"],
        )

    def test_recovers_exact_managed_audio_string_literals(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "global-metadata.dat"
            values = [b"au_ui_confirm", b"not_an_audio_literal", b"BARK_TEST", b"au_rtpc_fixture"]
            literal_data = b"".join(values)
            data_indexes = []
            cursor = 0
            for value in values:
                data_indexes.append(cursor)
                cursor += len(value)
            records = b"".join(
                pack("<II", len(value), index)
                for value, index in zip(values, data_indexes)
            )
            header = bytearray(32)
            header[0:8] = pack("<II", audio_semantics.METADATA_MAGIC, 29)
            header[8:24] = pack("<IiIi", 32, len(records), 32 + len(records), len(literal_data))
            path.write_bytes(bytes(header) + records + literal_data)

            self.assertEqual(
                audio_semantics.collect_metadata_audio_literals(path),
                ["au_rtpc_fixture", "au_ui_confirm", "BARK_TEST"],
            )
            contexts, event_names = audio_semantics.managed_literal_contexts(path)
            self.assertEqual(event_names, ["au_ui_confirm", "BARK_TEST"])
            self.assertNotIn("au_rtpc_fixture", contexts)

    def test_collects_signed_table_event_hashes_without_promoting_music_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            table_path = root / "structured/StreamingAssets/Table/AudioLevel.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "level": {
                    "battleMusicTriggerEvent": -1,
                    "levelInitEvent": [123, -2],
                    "customMusicModeBaseState": 456,
                }
            }), encoding="utf-8")
            hashes = audio_semantics.collect_table_audio_event_hashes(root)
            self.assertEqual(hashes, {0xFFFFFFFF, 123, 0xFFFFFFFE})

    def test_table_contexts_do_not_flatten_voice_media_ids_into_events(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            streaming = root / "structured/StreamingAssets/Table/RadioTable.json"
            persistent = root / "structured/Persistent/Table/RadioTable.json"
            streaming.parent.mkdir(parents=True)
            persistent.parent.mkdir(parents=True)
            payload = {
                "radio_fixture": {
                    "radioSingleDataList": [{
                        "id": "radio_fixture_001",
                        "audioOverride": "au_radio_fixture_001",
                        "audioEvent": "au_sfx_radio_transition",
                    }]
                }
            }
            streaming.write_text(json.dumps(payload), encoding="utf-8")
            persistent.write_text(json.dumps(payload), encoding="utf-8")

            contexts = audio_semantics.collect_table_contexts(root)

            self.assertEqual(set(contexts), {"au_sfx_radio_transition"})
            self.assertEqual(len(contexts["au_sfx_radio_transition"]), 1)
            self.assertIn("Persistent", contexts["au_sfx_radio_transition"][0]["source"])

    def test_audio_cue_separates_behavior_events_from_control_operands(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            table_path = root / "structured/StreamingAssets/Table/AudioCueTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "-2": {
                    "directHandlers": [{
                        "behaviourExpr": {
                            "exprType": 3,
                            "stringValue": "au_music_direct",
                            "boolValue": False,
                            "intValue": 0,
                            "floatValue": 0.0,
                            "children": [{
                                "exprType": 8,
                                "stringValue": "au_trigger_behavior_operand",
                                "children": [],
                            }],
                        },
                        "conditionExpr": {
                            "exprType": 2,
                            "stringValue": "",
                            "children": [{
                                "exprType": 8,
                                "stringValue": "au_trigger_condition_operand",
                                "boolValue": True,
                                "intValue": 7,
                                "floatValue": 1.5,
                                "children": [],
                            }],
                        },
                    }],
                    "levelHandlerMap": {
                        "map_test": {"handlers": [{
                            "behaviourExpr": {
                                "exprType": 3,
                                "stringValue": "au_music_level",
                                "children": [],
                            },
                            "conditionExpr": {"exprType": 0, "stringValue": "", "children": []},
                        }]},
                    },
                },
            }), encoding="utf-8")

            semantics = audio_semantics.collect_audio_cue_semantics(root)

            self.assertEqual(set(semantics["eventContexts"]), {"au_music_direct", "au_music_level"})
            level = semantics["eventContexts"]["au_music_level"][0]
            self.assertEqual(level["handlerScope"], "level")
            self.assertEqual(level["levelId"], "map_test")
            self.assertEqual(level["cueId"], 0xFFFFFFFE)
            self.assertEqual(len(semantics["expressionOperands"]), 2)
            self.assertEqual(
                {row["stringValue"] for row in semantics["expressionOperands"]},
                {"au_trigger_behavior_operand", "au_trigger_condition_operand"},
            )
            self.assertEqual(
                audio_semantics.collect_table_audio_event_names(root),
                {"au_music_direct", "au_music_level"},
            )

    def test_global_music_cues_and_rtpc_parameters_are_controls(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            table_path = root / "structured/StreamingAssets/Table/AudioCueTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "123": {
                    "directHandlers": [{
                        "behaviourExpr": {"exprType": 3, "stringValue": "au_music_fixture", "children": []},
                        "conditionExpr": {"exprType": 0, "stringValue": "", "children": []},
                    }],
                    "levelHandlerMap": {},
                },
            }), encoding="utf-8")
            mono_root = root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/MonoBehaviour"
            mono_root.mkdir(parents=True)
            (mono_root / "AudioGlobalConfig_p1.json").write_text(json.dumps({
                "musicCueCombatIn": {"_id": 123},
                "musicCueFactoryAreaIn": {"_id": -2},
                "rtpcGlobalVol": "au_rtpc_global_fixture",
                "listenerSpeedRtpcName": "au_rtpc_speed_fixture",
            }), encoding="utf-8")

            cue_semantics = audio_semantics.collect_audio_cue_semantics(root)
            controls = audio_semantics.collect_audio_global_control_semantics(root, cue_semantics)

            refs = {row["field"]: row for row in controls["audioGlobalMusicCueRefs"]}
            self.assertEqual(refs["musicCueCombatIn"]["definitionStatus"], "resolved")
            self.assertEqual(refs["musicCueFactoryAreaIn"]["definitionStatus"], "missing")
            self.assertEqual(
                {row["parameterName"] for row in controls["rtpcParameters"]},
                {"au_rtpc_global_fixture", "au_rtpc_speed_fixture"},
            )
            derived = controls["eventContexts"]["au_music_fixture"][0]
            self.assertEqual(derived["globalMusicCueField"], "musicCueCombatIn")
            contexts = audio_semantics.collect_table_contexts(root)
            self.assertIn("au_music_fixture", contexts)
            self.assertNotIn("#0xfffffffe", contexts)

    def test_collects_interactive_lifecycle_and_global_policy_events(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            mono_root = root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/MonoBehaviour"
            mono_root.mkdir(parents=True)
            (mono_root / "InteractiveAudioSetting_p1.json").write_text(json.dumps({
                "subTemplateList": [{
                    "modelId": "int_ore_model",
                    "subTemplateId": "int_ore",
                    "audioList": [{"state": 14, "audio": ["au_item_ore_collect"]}],
                    "customAudioList": [{
                        "audioState": "door_open",
                        "audioEvent": "au_int_door_open",
                        "desc": "Open door",
                    }],
                }],
            }), encoding="utf-8")
            (mono_root / "AudioGlobalConfig_p2.json").write_text(json.dumps({
                "gameplayMusicStartEvent": "au_music_main",
                "initEvents": ["au_sfx_init"],
                "charInitEvent": {
                    "_keyData": ["chr_test"],
                    "_valueData": [{"_id": -2}],
                },
                "audioStatesIn": {
                    "_keyData": [512],
                    "_valueData": [{"_ids": [{"_id": 123}]}],
                },
            }), encoding="utf-8")
            runtime_model = {"systems": [{
                "type": "Beyond.Gameplay.Core.InteractiveAudioComponent+EAudioTriggerState",
                "enumValues": {"Collect": 14},
            }]}

            contexts = audio_semantics.collect_table_contexts(root, runtime_model)

            collect = contexts["au_item_ore_collect"][0]
            self.assertEqual(collect["kind"], "interactiveAudioTrigger")
            self.assertEqual(collect["triggerStateName"], "Collect")
            self.assertEqual(collect["modelId"], "int_ore_model")
            custom = contexts["au_int_door_open"][0]
            self.assertEqual(custom["triggerCustomState"], "door_open")
            self.assertEqual(custom["description"], "Open door")
            self.assertEqual(contexts["au_music_main"][0]["semanticRole"], "gameplayMusicStartEvent")
            char_init = contexts["#0xfffffffe"][0]
            self.assertEqual(char_init["ownerId"], "chr_test")
            self.assertEqual(char_init["ownerKind"], "character")
            state_in = contexts["#0x0000007b"][0]
            self.assertEqual(state_in["stateDirection"], "enter")
            self.assertEqual(state_in["audioStateMask"], 512)
            self.assertEqual(
                audio_semantics.collect_table_audio_event_names(root),
                {"au_int_door_open", "au_item_ore_collect", "au_music_main", "au_sfx_init"},
            )
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)
            (component_root / "data_int_fixture.json").write_bytes(b"fixture")

            def decode_fixture(_path: Path, _data: bytes, _size: int) -> dict:
                return {"decoded": {"componentAudioComponents": [{
                    "index": 2,
                    "audioRows": [{
                        "state": 13,
                        "stateName": "Destroy",
                        "events": ["au_int_fixture_break"],
                    }],
                    "customRows": [{
                        "event": "au_int_fixture_open",
                        "name": "panel_open",
                        "note": "Open panel",
                    }],
                }]}}

            component_contexts = audio_semantics.collect_interactive_component_contexts(
                root,
                decoder=decode_fixture,
            )
            lifecycle = component_contexts["au_int_fixture_break"][0]
            self.assertEqual(lifecycle["triggerStateName"], "Destroy")
            self.assertEqual(lifecycle["ownerId"], "data_int_fixture")
            custom_component = component_contexts["au_int_fixture_open"][0]
            self.assertEqual(custom_component["triggerCustomState"], "panel_open")
            self.assertEqual(custom_component["componentIndex"], 2)

    def test_collects_exact_projectile_lifecycle_sound_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            path = root / "data/gameplay/projectiles.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "entries": [{
                    "key": "StreamingAssets:projectile_chr_test:42",
                    "id": "projectile_chr_test",
                    "source": {
                        "root": "StreamingAssets",
                        "pathId": "42",
                        "jsonPath": "export_full/recovered/projectile_chr_test.json",
                    },
                    "template": {
                        "activeSkillIds": ["chr_test_skill"],
                        "passiveSkillIds": [],
                    },
                    "sounds": {
                        "launchSound": {"value": -2, "hex": "0xfffffffe"},
                        "loopSound": {"value": 0, "hex": "0x00000000"},
                        "hitSound": {"value": 123, "hex": "0x0000007b"},
                    },
                }],
            }), encoding="utf-8")

            contexts = audio_semantics.collect_projectile_contexts(root)

            self.assertEqual(set(contexts), {"#0xfffffffe", "#0x0000007b"})
            launch = contexts["#0xfffffffe"][0]
            self.assertEqual(launch["kind"], "projectileSoundField")
            self.assertEqual(launch["soundField"], "launchSound")
            self.assertEqual(launch["triggerPhase"], "launch")
            self.assertEqual(launch["eventHash"], 0xFFFFFFFE)
            self.assertEqual(launch["signedValue"], -2)
            self.assertEqual(launch["eventHex"], "0xfffffffe")
            self.assertEqual(launch["authoredSkillIds"], ["chr_test_skill"])
            self.assertEqual(launch["skillOwnershipStatus"], "projectileTemplateReferenceOnly")
            self.assertEqual(launch["runtimeActivationStatus"], "projectileLifecycleExecutionNotObserved")
            rows, _, _ = audio_semantics.build_event_rows({"eventNames": [], "events": [], "eventEvidence": []}, contexts)
            hashed = next(row for row in rows if row["hash"] == 0xFFFFFFFE)
            self.assertEqual(hashed["category"], "sfx")
            self.assertEqual(hashed["categoryEvidence"], "exactProjectileSoundField")

    def test_spawner_pre_warn_context_preserves_unresolved_authored_event(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root = root / "export_full"
            webui_root = root / "webui"
            spawner_path = (
                export_root
                / "structured/StreamingAssets/Data/Json/SpawnerConfig/base01_dg001/sc_fixture.json"
            )
            spawner_path.parent.mkdir(parents=True)
            spawner_path.write_bytes(spawner_config_fixture())

            semantics = audio_semantics.collect_spawner_pre_warn_semantics(export_root)
            stats = semantics["stats"]
            self.assertEqual(stats["status"], "complete")
            self.assertEqual(stats["sourceFiles"], 1)
            self.assertEqual(stats["decodedFiles"], 1)
            self.assertEqual(stats["enemyRows"], 2)
            self.assertEqual(stats["preWarnAudioContexts"], 2)
            self.assertEqual(stats["distinctPreWarnAudioEvents"], 2)
            unresolved = semantics["eventContexts"]["au_interactive_monsterspawn_white_2s"][0]
            self.assertEqual(unresolved["kind"], "spawnerPreWarnAudio")
            self.assertEqual(unresolved["enemyId"], "eny_0018_lbtough_train")
            self.assertEqual(unresolved["bornTemplateId"], "")
            self.assertEqual(unresolved["preWarnTime"], 2.0)
            self.assertEqual(unresolved["preWarnEffectKey"], "P_monsterspawn_summon_02_2s")
            self.assertEqual(unresolved["path"], "enemyLibrary[0].preWarnAudioEventKey")
            self.assertEqual(len(unresolved["sourceFingerprint"]), 64)

            payload = audio_semantics.build_audio_semantic_data(
                {
                    "eventNames": ["au_int_electric_fence_hit"],
                    "events": [],
                    "eventEvidence": [{
                        "eventId": "au_int_electric_fence_hit",
                        "eventHash": 123,
                        "bankId": 7,
                        "bank": "main_banks.pck",
                        "traversalStatus": "complete",
                    }],
                    "entries": [],
                },
                language="CN",
                export_root=export_root,
                webui_root=webui_root,
                metadata_path=None,
            )
            self.assertEqual(payload["counts"]["spawnerPreWarnAudioEvents"], 2)
            self.assertEqual(payload["counts"]["spawnerPreWarnAudioContexts"], 2)
            self.assertEqual(payload["counts"]["spawnerPreWarnAudioEventsFoundInWwise"], 1)
            self.assertEqual(payload["counts"]["spawnerPreWarnAudioEventsUnresolved"], 1)
            self.assertEqual(payload["triggerCatalog"]["spawnerPreWarnAudio"]["decodedFiles"], 1)
            event_summaries = json.loads(
                (webui_root / "data/lang/CN/audio/events.json").read_text(encoding="utf-8")
            )["events"]
            unresolved_summary = next(
                row for row in event_summaries
                if row["id"] == "au_interactive_monsterspawn_white_2s"
            )
            self.assertFalse(unresolved_summary["foundInWwise"])
            self.assertEqual(unresolved_summary["category"], "sfx")
            self.assertEqual(
                unresolved_summary["categoryEvidence"],
                "exactSpawnerPreWarnAudioField",
            )
            self.assertIn("spawnerPreWarnAudio", unresolved_summary["contextKinds"])
            self.assertIn("sc_fixture", unresolved_summary["contextSearch"])

    def test_collects_owner_unresolved_animation_callbacks_as_debug_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            gameplay_path = root / "data/lang/CN/gameplay/sound_effects.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({
                "animationEvidencePath": "sound_effects_animation_evidence.json",
                "characters": {},
                "enemies": {},
            }), encoding="utf-8")
            gameplay_path.with_name("sound_effects_animation_evidence.json").write_text(json.dumps({
                "ownerUnresolved": [{
                    "id": "au_ui_generic",
                    "actionKinds": ["action"],
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClipContexts": ["ui"],
                    "sourceAnimationClips": ["UI_Generic"],
                    "clipReachability": "unresolved",
                    "authoredEventIds": ["au_ui_generic"],
                    "evidence": [{
                        "clipSource": "AnimationClip/UI_Generic.anim",
                        "time": 0.5,
                        "function": "PostAudioEvent",
                    }],
                }],
            }), encoding="utf-8")

            contexts = audio_semantics.collect_gameplay_contexts(root, "CN")

            context = contexts["au_ui_generic"][0]
            self.assertEqual(context["kind"], "animationCallbackOwnerUnresolved")
            self.assertEqual(context["confidence"], "exactCallbackOwnerUnresolved")
            self.assertEqual(context["ownerStatus"], "unresolved")
            self.assertEqual(context["animationOccurrenceCount"], 1)
            self.assertEqual(context["sourcePaths"], ["AnimationClip/UI_Generic.anim"])

    def test_builds_compact_lazy_shards_with_evidence_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root = root / "export_full"
            webui_root = root / "webui"
            gameplay_path = webui_root / "data/lang/CN/gameplay/sound_effects.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({
                "authoredPlaySoundActions": [{
                    "buffId": "buff_test",
                    "eventId": "au_sfx_test",
                    "startFrame": 17,
                    "endFrame": 34,
                    "stopOnEnd": True,
                    "stopFadeDurationMs": 300,
                    "targetSelector": "smart_target",
                    "targetSettingsStatus": "partial-target-settings-envelope-opaque",
                    "sourcePaths": ["BuffData/buff_test.json"],
                }],
                "characters": {
                    "chr_test": {
                        "animationOwnershipConfidence": "inferred",
                        "animationEvents": [{
                            "id": "au_sfx_test",
                            "actionKinds": ["attack"],
                            "animationFunctions": ["OnCustomFootStep"],
                            "sourceAnimationClips": ["A_actor_test_battle_attack1"],
                            "animationOwnerCount": 2,
                            "animationOwnershipScope": "sharedPlayableCharacters",
                            "possibleMediaScope": "sharedEventGraph",
                            "evidence": [{"time": 0.25, "function": "PostAudioEvent"}],
                        }],
                        "groups": {
                            "normal": {
                                "ownershipConfidence": "direct",
                                "skillIds": ["skill_test"],
                                 "events": [{
                                     "id": "au_sfx_test",
                                     "sourceSkillIds": ["skill_test"],
                                     "triggerBindingStatus": "exactSkillConfig",
                                     "triggerRelationTypes": ["buffPlaySoundAction", "skillBuffChain"],
                                     "triggerBindings": [{
                                         "status": "exactSkillConfig",
                                         "requestEvidence": "exactAuthoredPlaySoundAction",
                                         "runtimeActivationStatus": "authoredFrameWindowRecoveredConditionUnresolved",
                                         "ownershipMethod": "gameplaySkillId",
                                         "evidenceKinds": ["skillBuffData"],
                                         "sourcePaths": ["BuffData/buff_test.json"],
                                         "playSoundActions": [{
                                             "buffId": "buff_test",
                                             "eventId": "au_sfx_test",
                                             "startFrame": 17,
                                             "endFrame": 34,
                                             "stopOnEnd": True,
                                             "stopFadeDurationMs": 300,
                                             "targetSelector": "smart_target",
                                             "targetSettingsStatus": "partial-target-settings-envelope-opaque",
                                         }],
                                     }],
                                 }],
                            }
                        }
                    },
                    "chr_test_2": {
                        "animationOwnershipConfidence": "inferred",
                        "animationEvents": [{
                            "id": "au_sfx_test",
                            "actionKinds": ["attack"],
                            "animationFunctions": ["OnCustomFootStep"],
                            "sourceAnimationClips": ["A_actor_test_2_battle_attack1"],
                            "animationOwnerCount": 2,
                            "animationOwnershipScope": "sharedPlayableCharacters",
                            "possibleMediaScope": "sharedEventGraph",
                            "evidence": [{"time": 0.5, "function": "OnCustomFootStep"}],
                        }],
                        "groups": {},
                    },
                },
                "enemies": {},
            }), encoding="utf-8")
            table_path = export_root / "structured/StreamingAssets/Table/AudioCueTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "123": {
                    "directHandlers": [{
                        "behaviourExpr": {"exprType": 3, "stringValue": "au_sfx_test", "children": []},
                        "conditionExpr": {"exprType": 0, "stringValue": "", "children": []},
                    }],
                    "levelHandlerMap": {},
                },
            }), encoding="utf-8")

            media_entry = {
                "id": "42",
                "mediaId": 42,
                "rel": "wwise/sfx/42.flac",
                "src": "/export_full/structured/Audio/shared/wwise/sfx/42.flac",
                "format": "flac",
                "bytes": 100,
                "storageRoot": "shared",
                "audioScope": "shared",
                "audioCategory": "sfx",
                "sourceBlock": "audio",
                "sourceBank": "main",
            }
            event_entry = {
                **media_entry,
                "id": "au_sfx_test",
                "eventId": "au_sfx_test",
                "eventHash": 123,
                "bankId": 7,
                "bank": "main_banks.pck",
            }
            audio_index = {
                "generated": "2026-08-09T00:00:00Z",
                "eventNames": ["au_sfx_test", "au_music_unlinked"],
                "events": [event_entry],
                "eventEvidence": [{
                    "eventId": "au_sfx_test",
                    "eventHash": 123,
                    "bankId": 7,
                    "bank": "main_banks.pck",
                    "actionIds": [8],
                    "visitedObjectIds": [123, 8, 9],
                    "objectTypeCounts": {"3": 1, "4": 1, "6": 1},
                    "selectionObjectTypes": [6],
                    "mediaIds": [42],
                    "source": "wwiseHirc",
                    "nestedReferenceConfidence": "candidate",
                }],
                "entries": [media_entry, event_entry],
            }
            payload = audio_semantics.build_audio_semantic_data(
                audio_index,
                language="CN",
                export_root=export_root,
                webui_root=webui_root,
                metadata_path=None,
                cutscene_events={"cutscene_test": ["au_sfx_test"]},
            )

            out_root = webui_root / "data/lang/CN/audio"
            event_payload = json.loads((out_root / "events.json").read_text(encoding="utf-8"))
            media_payload = json.loads((out_root / "media.json").read_text(encoding="utf-8"))
            event_summary = next(row for row in event_payload["events"] if row["id"] == "au_sfx_test")
            detail_payload = json.loads((out_root / event_summary["detailShard"]).read_text(encoding="utf-8"))
            event = next(row for row in detail_payload["events"] if row["id"] == "au_sfx_test")
            media = media_payload["media"][0]

            self.assertEqual(payload["shards"], {"events": "events.json", "media": "media.json"})
            self.assertTrue(payload["debugOnly"])
            self.assertEqual(payload["runtimeModel"]["status"], "degraded")
            self.assertEqual(event["runtimeSelection"], "runtimeBranchUnresolved")
            self.assertEqual(event["selectionContainerTypes"], ["switchContainer"])
            self.assertEqual(event["candidateCount"], 1)
            self.assertEqual(event["possibleMediaCount"], 1)
            self.assertEqual(event["playableCharacterAnimationOwnerCount"], 2)
            self.assertEqual(event["animationContextScope"], "sharedPlayableCharacters")
            self.assertEqual(event["animationFunctions"], ["OnCustomFootStep"])
            self.assertEqual(set(event_summary["contextGroups"]), {"gameplay", "animation", "authoredConfig", "cutscene"})
            skill_context = next(context for context in event["contexts"] if context["kind"] == "characterSkill")
            action_context = next(context for context in event["contexts"] if context["kind"] == "buffPlaySoundAction")
            self.assertEqual(skill_context["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(skill_context["triggerRelationTypes"], ["buffPlaySoundAction", "skillBuffChain"])
            self.assertEqual(skill_context["triggerRequestEvidence"], ["exactAuthoredPlaySoundAction"])
            self.assertEqual(
                skill_context["triggerRuntimeActivationStatuses"],
                ["authoredFrameWindowRecoveredConditionUnresolved"],
            )
            self.assertEqual(skill_context["triggerPlaySoundActionCount"], 1)
            self.assertNotIn("triggerPlaySoundActions", skill_context)
            self.assertEqual(action_context["triggerPlaySoundActions"][0]["startFrame"], 17)
            self.assertEqual(event_summary["triggerBindingStatuses"], ["exactSkillConfig"])
            self.assertIn("authoredFrameWindowRecoveredConditionUnresolved", event_summary["contextSearch"])
            self.assertEqual(event_summary["triggerPlaySoundActionCount"], 1)
            self.assertEqual(payload["counts"]["exactSkillConfigTriggerEvents"], 1)
            self.assertEqual(payload["counts"]["exactSkillConfigTriggerContexts"], 1)
            self.assertEqual(payload["counts"]["authoredPlaySoundActionEvents"], 1)
            self.assertEqual(payload["counts"]["authoredPlaySoundActionOccurrences"], 1)
            self.assertEqual(skill_context["triggerOwnershipMethods"], ["gameplaySkillId"])
            self.assertEqual(skill_context["triggerEvidenceKinds"], ["skillBuffData"])
            self.assertGreater(payload["eventDetailShardCount"], 0)
            self.assertEqual(
                {row["kind"] for row in event["contexts"]},
                {"buffPlaySoundAction", "characterSkill", "characterAnimation", "audioCueBehaviorEvent", "cutsceneTimeline"},
            )
            self.assertEqual(media["eventIds"], ["au_sfx_test"])
            self.assertIn("eventMedia", payload["evidenceBoundary"])
            self.assertIn("animationOwnership", payload["evidenceBoundary"])
            self.assertEqual(payload["counts"]["sharedPlayableCharacterAnimationEvents"], 1)
            self.assertEqual(payload["counts"]["footstepSystemEvents"], 1)


if __name__ == "__main__":
    unittest.main()
