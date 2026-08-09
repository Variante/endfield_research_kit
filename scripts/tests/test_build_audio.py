import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from struct import pack
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "build_audio.py"
SPEC = importlib.util.spec_from_file_location("build_audio", SCRIPT)
build_audio = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(build_audio)


class AudioCategoryTests(unittest.TestCase):
    def test_wav_decode_defaults_to_lossless_flac_output(self) -> None:
        self.assertEqual(
            build_audio.audio_output_format(argparse.Namespace(format="wav", audio_format=None)),
            "flac",
        )
        self.assertEqual(
            build_audio.audio_output_format(argparse.Namespace(format="wem", audio_format=None)),
            "wem",
        )

    def test_wem_decode_cannot_claim_browser_flac_output(self) -> None:
        with self.assertRaises(SystemExit):
            build_audio.audio_output_format(
                argparse.Namespace(format="wem", audio_format="flac")
            )

    def test_dialog_path_uses_requested_browser_extension(self) -> None:
        self.assertEqual(
            build_audio.audio_rel_for_dialog_path("v1d3/line.wem", ".flac"),
            "voice/other/line.flac",
        )

    def test_voice_categories_keep_useful_story_detail(self) -> None:
        self.assertEqual(
            build_audio.audio_category_for_rel("voice/story/main_episodes/line.wav"),
            ("story_voice", "main_episodes"),
        )
        self.assertEqual(
            build_audio.audio_category_for_rel("voice/characters/avywen/line.wav"),
            ("character_voice", "avywen"),
        )

    def test_event_category_handles_voice_alias(self) -> None:
        self.assertEqual(build_audio.event_audio_category("au_voice_test"), "au_vo")
        self.assertEqual(
            build_audio.audio_category_for_rel("wwise/unknown/1.wav", "au_music"),
            ("music", ""),
        )

    def test_combined_decode_retains_shared_bank_provenance(self) -> None:
        self.assertEqual(
            build_audio.combined_decode_source_block(
                "shared", "CN", "unmapped/initial/123.wav"
            ),
            "initial-audio",
        )
        self.assertEqual(
            build_audio.combined_decode_source_block("CN", "CN", "voice/line.wav"),
            "voice",
        )

    def test_hirc_summary_keeps_raw_types_and_marks_runtime_selectors(self) -> None:
        counts, labels, selectors = build_audio.summarize_hirc_object_types(
            {
                1: {"type": 4},
                2: {"type": 3},
                3: {"type": 6},
                4: {"type": 99},
            },
            {1, 2, 3, 4, 5},
        )
        self.assertEqual(counts, {"3": 1, "4": 1, "6": 1, "99": 1})
        self.assertEqual(labels["6"], "switchContainer")
        self.assertEqual(labels["99"], "type99")
        self.assertEqual(selectors, [6])

    def test_typed_hirc_traversal_uses_reciprocal_children_and_sound_source(self) -> None:
        event_id = 100
        play_action = 101
        stop_action = 102
        container_id = 200
        sound_a = 301
        sound_b = 302
        unrelated_sound = 303

        event_data = bytes([2]) + pack("<II", play_action, stop_action)
        play_data = pack("<HI", 0x0403, container_id)
        stop_data = pack("<HI", 0x0103, unrelated_sound)
        container_data = bytearray(80)
        container_data[8:12] = pack("<I", 999)
        # Incidental object/media-looking integers are not typed child edges.
        container_data[16:20] = pack("<I", unrelated_sound)
        children_offset = 40
        container_data[children_offset - 3] = 0
        container_data[children_offset - 2] = 0
        container_data[children_offset - 1] = 0x12
        container_data[children_offset:children_offset + 12] = pack("<III", 2, sound_a, sound_b)

        def sound_data(media_id: int, parent_id: int) -> bytes:
            data = bytearray(30)
            data[5:9] = pack("<I", media_id)
            data[22:26] = pack("<I", parent_id)
            return bytes(data)

        objects = {
            event_id: {"type": 4, "data": event_data},
            play_action: {"type": 3, "data": play_data},
            stop_action: {"type": 3, "data": stop_data},
            container_id: {"type": 5, "data": bytes(container_data)},
            sound_a: {"type": 2, "data": sound_data(401, container_id)},
            sound_b: {"type": 2, "data": sound_data(402, container_id)},
            unrelated_sound: {"type": 2, "data": sound_data(499, 777)},
        }

        result = build_audio.traverse_hirc_event(event_id, objects, {401, 402, 499})
        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["rootPlayActionCount"], 1)
        self.assertEqual(result["rootStopActionCount"], 1)
        self.assertEqual(result["containerEvidence"][0]["childrenOffset"], children_offset)
        self.assertEqual(result["containerEvidence"][0]["modeLabel"], "random")
        self.assertEqual(result["containerEvidence"][0]["flagLabels"], [
            "resetPlaylistAtEachPlay", "global",
        ])
        self.assertEqual(
            {tuple(row["relationTypes"]) for row in result["mediaEvidence"]},
            {("randomAlternative",)},
        )
        self.assertNotIn(unrelated_sound, result["visitedObjectIds"])

    def test_typed_hirc_traversal_fails_closed_on_music_node(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 10, "data": pack("<I", 777)},
            777: {"type": 2, "data": bytes(30)},
        }
        result = build_audio.traverse_hirc_event(1, objects, {777})
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["traversalStatus"], "partial")
        self.assertEqual(result["unresolvedNodes"][0]["reason"], "unsupportedTypedNode")

    def test_play_event_follows_nested_event_actions(self) -> None:
        sound = bytearray(30)
        sound[5:9] = pack("<I", 99)
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x2103, 3)},
            3: {"type": 4, "data": bytes([1]) + pack("<I", 4)},
            4: {"type": 3, "data": pack("<HI", 0x0403, 5)},
            5: {"type": 2, "data": bytes(sound)},
        }
        result = build_audio.traverse_hirc_event(1, objects, {99})
        self.assertEqual(result["mediaIds"], [99])
        self.assertEqual([row["operation"] for row in result["actionEvidence"]], ["playEvent", "play"])

    def test_shared_sound_keeps_every_play_root_without_duplicate_media(self) -> None:
        sound = bytearray(30)
        sound[5:9] = pack("<I", 99)
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            3: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            4: {"type": 2, "data": bytes(sound)},
        }
        result = build_audio.traverse_hirc_event(1, objects, {99})
        self.assertEqual(result["mediaIds"], [99])
        self.assertEqual(result["rootPlayActionCount"], 2)
        self.assertEqual(result["mediaEvidence"], [{
            "mediaId": 99,
            "decoded": True,
            "soundObjectCount": 1,
            "soundObjectIds": [4],
            "rootActionIds": [2, 3],
            "relationTypes": ["directSound"],
            "selectionPaths": [["directSound"]],
        }])


class AudioDumperTests(unittest.TestCase):
    def test_all_mode_runs_once_per_vfs_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            executable = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            audio_root = root / "Audio"
            executable.touch()
            streaming.mkdir()
            persistent.mkdir()
            args = argparse.Namespace(
                skip_decode=False,
                audio_dumper=executable,
                streaming_assets=streaming,
                fallback_assets=persistent,
                audio_root=audio_root,
                block="all",
                format="wav",
            )

            with mock.patch.object(build_audio.subprocess, "run") as run:
                build_audio.run_audio_dumper(args, "CN", build_audio.LANGUAGES["CN"])

            self.assertEqual(run.call_count, 1)
            for call in run.call_args_list:
                command = call.args[0]
                self.assertEqual(command[1:3], ["audio", "--streaming-assets"])
                self.assertIn("--block", command)
                self.assertEqual(command[command.index("--block") + 1], "all")
                self.assertIn("--shared-output", command)

    def test_audio_file_priority_prefers_flac_over_legacy_wav(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            (root / "same.wav").write_bytes(b"wav")
            (root / "same.flac").write_bytes(b"flac")
            files = build_audio.iter_audio_files(root)
            self.assertEqual([path.suffix for path in files], [".flac", ".wav"])

    def test_media_id_collisions_preserve_distinct_physical_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            source = root / "Audio/shared"
            (source / "wwise/sfx").mkdir(parents=True)
            (source / "wwise/unknown").mkdir(parents=True)
            (source / "wwise/sfx/42.flac").write_bytes(b"preferred")
            (source / "wwise/sfx/42.wav").write_bytes(b"legacy")
            (source / "wwise/unknown/42.flac").write_bytes(b"other occurrence")

            index = build_audio.collect_audio_files(
                root / "Audio",
                root,
                source,
                "shared",
                "CN",
                build_audio.LANGUAGES["CN"],
            )

            self.assertEqual(len(index), 2)
            self.assertEqual({row["format"] for row in index.values()}, {"flac"})
            self.assertEqual(
                {row["rel"] for row in index.values()},
                {"wwise/sfx/42.flac", "wwise/unknown/42.flac"},
            )

    def test_cross_scope_merge_keeps_later_lookup_priority_and_both_files(self) -> None:
        shared = {"42": {"id": "42", "storageRoot": "shared", "rel": "wwise/42.flac"}}
        language = {"42": {"id": "42", "storageRoot": "CN", "rel": "voice/42.flac"}}
        merged = build_audio.merge_audio_file_indexes(shared, language)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged["42"]["storageRoot"], "CN")
        self.assertIn("42@shared:wwise/42.flac", merged)


class ProjectileAudioLinkTests(unittest.TestCase):
    def test_links_signed_projectile_hash_to_playable_hirc_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            projectile_path = webui_root / "data" / "gameplay" / "projectiles.json"
            projectile_path.parent.mkdir(parents=True)
            projectile_path.write_text(
                json.dumps({
                    "entries": [{
                        "id": "projectile_test",
                        "sounds": {"launchSound": {"value": -1, "hex": "0xffffffff"}},
                    }],
                }),
                encoding="utf-8",
            )
            key = build_audio.projectile_event_key(0xFFFFFFFF)
            stats = build_audio.link_projectile_audio(
                webui_root,
                {key: [{
                    "src": "/export_full/structured/Audio/shared/wwise/sfx/7.wav",
                    "mediaId": 7,
                    "format": "wav",
                    "bytes": 120,
                    "audioScope": "shared",
                    "bankId": 9,
                }]},
                [{"eventId": key, "eventHash": 0xFFFFFFFF, "source": "wwiseHirc"}],
            )

            payload = json.loads(projectile_path.read_text(encoding="utf-8"))
            launch = payload["entries"][0]["sounds"]["launchSound"]
            self.assertEqual(stats["projectileSoundRefsLinked"], 1)
            self.assertTrue(launch["event"]["foundInWwise"])
            self.assertEqual(launch["event"]["runtimeSelection"], "singleCandidate")
            self.assertEqual(launch["audio"][0]["mediaId"], 7)


class GameplayAudioLinkTests(unittest.TestCase):
    @staticmethod
    def memorypack_strings(member_count: int, *values: str) -> bytes:
        return bytes([member_count]) + b"".join(
            pack("<I", len(value.encode("utf-8"))) + value.encode("utf-8")
            for value in values
        )

    def test_length_prefixed_scan_rejects_incidental_ascii(self) -> None:
        valid = self.memorypack_strings(47, "au_skill_test")
        incidental = b"\x00xxxxau_incidental"
        self.assertEqual(
            build_audio.length_prefixed_matches(
                valid + incidental,
                build_audio.GAMEPLAY_AUDIO_EVENT_BYTES_RE,
            ),
            {"au_skill_test"},
        )

    def test_animation_collection_normalizes_event_identity_and_preserves_authored_case(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            clip_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            clip_root.mkdir(parents=True)
            (clip_root / "A_actor_test_battle_walk_p0000000000000001.anim").write_text(
                """%YAML 1.1
AnimationClip:
  m_Name: A_actor_test_battle_walk
  m_Events:
  - time: 0.25
    functionName: OnCustomFootStep
    data: Player_FOL_FS_Walk
    floatParameter: 0.5
    intParameter: 0
  - time: 0.75
    functionName: OnCustomFootStep
    data: player_fol_fs_walk
    floatParameter: 0.5
    intParameter: 1
""",
                encoding="utf-8",
            )
            result = build_audio.collect_gameplay_animation_audio(
                export_root,
                [{"kind": "character", "id": "chr_0001_test", "skillGroups": []}],
                [],
            )

            owner = result["owners"][0]
            self.assertEqual(set(owner["events"]), {"player_fol_fs_walk"})
            self.assertEqual(
                [row["authoredEventId"] for row in owner["events"]["player_fol_fs_walk"]],
                ["Player_FOL_FS_Walk", "player_fol_fs_walk"],
            )
            self.assertEqual({row["clipContext"] for row in owner["events"]["player_fol_fs_walk"]}, {"battle"})
            self.assertEqual({row["clipReachability"] for row in owner["events"]["player_fol_fs_walk"]}, {"unresolved"})

    def test_collects_direct_character_and_bounded_enemy_audio(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [
                {
                    "kind": "character",
                    "id": "chr_0001_test",
                    "skillGroups": [{"id": "normal", "skills": [{"id": "chr_0001_test_normal"}]}],
                },
                {
                    "kind": "enemy",
                    "id": "eny_0001_test",
                    "variantIds": ["eny_0001_test_elite"],
                    "bornBuffs": ["buff_enemy_spawn"],
                },
            ]}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            buff_root = export_root / "structured/StreamingAssets/Data/Json/BuffData"
            skill_root.mkdir(parents=True)
            buff_root.mkdir(parents=True)
            (skill_root / "chr_0001_test_normal.json").write_bytes(
                self.memorypack_strings(47, "au_character_attack", "buff_character_hit")
            )
            (buff_root / "buff_character_hit.json").write_bytes(
                self.memorypack_strings(30, "au_character_hit")
            )
            (skill_root / "eny_0001_test_elite_attack.json").write_bytes(
                self.memorypack_strings(47, "au_enemy_attack")
            )
            (buff_root / "buff_enemy_spawn.json").write_bytes(
                self.memorypack_strings(30, "au_enemy_spawn")
            )

            result = build_audio.collect_gameplay_audio_references(webui_root, export_root, "CN")
            owners = result["owners"]
            character = next(row for row in owners if row["ownerKind"] == "character")
            enemy_skill = next(row for row in owners if row["ownerKind"] == "enemy" and row["skillId"])
            enemy_spawn = next(row for row in owners if row["ownerKind"] == "enemy" and not row["skillId"])
            self.assertEqual(character["confidence"], "direct")
            self.assertEqual(set(character["events"]), {"au_character_attack", "au_character_hit"})
            self.assertEqual(enemy_skill["confidence"], "inferred")
            self.assertEqual(set(enemy_skill["events"]), {"au_enemy_attack"})
            self.assertEqual(enemy_spawn["confidence"], "direct")
            self.assertEqual(set(enemy_spawn["events"]), {"au_enemy_spawn"})

    def test_collects_enemy_template_skill_authored_under_another_enemy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "enemy",
                "id": "eny_0101_variant",
                "templateId": "eny_0101_variant",
                "variantIds": ["eny_0101_variant"],
                "bornBuffs": [],
            }]}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            skill_root.mkdir(parents=True)
            (skill_root / "eny_0001_base_attack.json").write_bytes(
                self.memorypack_strings(47, "au_enemy_base_attack")
            )
            template_root = (
                export_root
                / "recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour"
            )
            template_root.mkdir(parents=True)
            (template_root / "data_eny_0101_variant_p1234.json").write_text(json.dumps({
                "references": {"RefIds": [{
                    "type": {"class": "AbilitySystemData"},
                    "data": {"remainingStringHints": [
                        {"offset": 24, "value": "eny_0001_base_attack"},
                    ]},
                }]},
            }), encoding="utf-8")

            result = build_audio.collect_gameplay_audio_references(
                webui_root,
                export_root,
                "CN",
            )
            owner = next(row for row in result["owners"] if row["skillId"])
            self.assertEqual(owner["ownerId"], "eny_0101_variant")
            self.assertEqual(owner["confidence"], "inferred")
            self.assertEqual(owner["ownershipMethod"], "enemyTemplateAbilitySystemSkill")
            self.assertEqual(set(owner["events"]), {"au_enemy_base_attack"})
            self.assertEqual(result["counts"]["enemyTemplatesWithSkillReferences"], 1)
            self.assertEqual(result["counts"]["enemyTemplateSkillReferences"], 1)

    def test_collects_exact_animation_clip_audio_callback(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "character",
                "id": "chr_0001_test",
                "skillGroups": [{
                    "id": "chr_0001_test_NormalAttack",
                    "actionSkillIds": ["chr_0001_test_attack1"],
                }],
            }]}), encoding="utf-8")
            clip_root = (
                export_root
                / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            )
            clip_root.mkdir(parents=True)
            (clip_root / "A_actor_test_battle_attack1_p0123456789ABCDEF.anim").write_text(
                "\n".join([
                    "%YAML 1.1",
                    "AnimationClip:",
                    "  m_Name: A_actor_test_battle_attack1",
                    "  m_Events:",
                    "  - time: 0.25",
                    "    functionName: PostAudioEvent",
                    "    data: player_test_attack_foley",
                    "  - time: 0.5",
                    "    functionName: NotAudio",
                    "    data: ignored",
                ]),
                encoding="utf-8",
            )

            result = build_audio.collect_gameplay_audio_references(
                webui_root,
                export_root,
                "CN",
            )
            self.assertIn("player_test_attack_foley", result["eventNames"])
            animation_owner = result["animationOwners"][0]
            self.assertEqual(animation_owner["ownerId"], "chr_0001_test")
            evidence = animation_owner["events"]["player_test_attack_foley"][0]
            self.assertEqual(evidence["actionKind"], "attack")
            self.assertEqual(evidence["function"], "PostAudioEvent")
            self.assertEqual(evidence["time"], 0.25)

    def test_collects_direct_combat_profile_voice_and_bark_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root = root / "export_full"
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "CharacterTable.json").write_text(json.dumps({
                "chr_0001_test": {
                    "profileVoice": [{
                        "voId": "chr_0001_test_combat_intobattle_01",
                        "voiceIndex": 7,
                    }, {
                        "voId": "chr_0001_test_chrbark_join_01",
                        "voiceIndex": 8,
                    }],
                },
            }), encoding="utf-8")
            (table_root / "AIBark.json").write_text(json.dumps({
                "bark_test": {"array": [{"triggerKey": ["combat_intobattle"]}]},
            }), encoding="utf-8")
            result = build_audio.collect_gameplay_profile_voices(export_root, [{
                "kind": "character",
                "id": "chr_0001_test",
                "skillGroups": [],
            }])

            self.assertEqual(result["counts"]["profileVoiceRefs"], 1)
            voice = result["owners"][0]["voices"][0]
            self.assertEqual(voice["id"], "chr_0001_test_combat_intobattle_01")
            self.assertEqual(voice["triggerKey"], "combat_intobattle")
            self.assertEqual(voice["actionKind"], "combatVoice")

    def test_writes_only_playable_gameplay_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            references = {
                "eventNames": {"au_yes", "au_no"},
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal",
                    "confidence": "direct",
                    "events": {"au_yes": [{"kind": "skillData"}], "au_no": [{"kind": "skillData"}]},
                }, {
                    "ownerKind": "enemy",
                    "ownerId": "eny_test",
                    "groupId": "",
                    "skillId": "eny_test_attack",
                    "confidence": "inferred",
                    "events": {"au_yes": [{"kind": "skillData"}]},
                }],
                "animationOwners": [{
                    "ownerKind": "enemy",
                    "ownerId": "eny_animation",
                    "ownershipSources": ["animation config"],
                    "events": {"au_yes": [{
                        "kind": "animationClipEvent",
                        "clip": "A_monster_test_battle_attack1",
                        "actionKind": "attack",
                        "time": 0.25,
                        "function": "PostAudioEvent",
                    }]},
                }],
                "profileVoiceOwners": [{
                    "ownerId": "chr_voice",
                    "voices": [{
                        "id": "chr_voice_mono_attack_01",
                        "actionKind": "attackVoice",
                        "characterId": "chr_voice",
                        "profileVoiceIndex": 1,
                        "triggerKey": "",
                        "source": "CharacterTable.json",
                    }],
                }],
                "counts": {},
            }
            stats = build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"au_yes": [{"src": "data/audio/shared/yes.wav", "mediaId": 1}]},
                [{"eventId": "au_yes"}],
                {"chr_voice_mono_attack_01": {
                    "src": "data/audio/CN/voice.wav",
                    "id": "chr_voice_mono_attack_01",
                    "format": "wav",
                }},
            )
            payload = json.loads((webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8"))
            events = payload["characters"]["chr_test"]["groups"]["normal"]["events"]
            self.assertEqual(stats["gameplayAudioRefsLinked"], 4)
            self.assertEqual(stats["animationAudioRefsLinked"], 1)
            self.assertEqual(stats["profileVoiceRefsLinked"], 1)
            self.assertEqual([row["id"] for row in events], ["au_yes"])
            enemy = payload["enemies"]["eny_test"]
            self.assertEqual(enemy["ownershipConfidence"], "inferred")
            self.assertEqual(enemy["skillIds"], ["eny_test_attack"])
            self.assertEqual([row["id"] for row in enemy["events"]], ["au_yes"])
            animation = payload["enemies"]["eny_animation"]
            self.assertEqual(animation["animationOwnershipConfidence"], "inferred")
            self.assertEqual(animation["animationEvents"][0]["actionKinds"], ["attack"])
            self.assertNotIn("audio", animation["animationEvents"][0])
            catalog = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects_animation_catalog.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(catalog["events"]["au_yes"]["audio"][0]["mediaId"], 1)
            self.assertEqual(
                animation["animationEvents"][0]["sourceAnimationClips"],
                ["A_monster_test_battle_attack1"],
            )
            self.assertEqual(
                payload["characters"]["chr_voice"]["profileVoices"][0]["actionKinds"],
                ["attackVoice"],
            )

    def test_animation_events_mark_shared_owner_scope_and_merge_case_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            callback = {
                "kind": "animationClipEvent",
                "clip": "A_actor_test_battle_walk",
                "actionKind": "movement",
                "function": "OnCustomFootStep",
            }
            references = {
                "eventNames": {"player_fol_fs_walk"},
                "owners": [],
                "animationOwners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_a",
                    "events": {
                        "Player_FOL_FS_Walk": [callback],
                        "player_fol_fs_walk": [{**callback, "clip": "A_actor_test_battle_walk_b"}],
                    },
                }, {
                    "ownerKind": "character",
                    "ownerId": "chr_b",
                    "events": {"player_fol_fs_walk": [callback]},
                }],
                "profileVoiceOwners": [],
                "counts": {},
            }
            media = [{"src": "data/audio/shared/walk_1.wav", "mediaId": 1}, {
                "src": "data/audio/shared/walk_2.wav", "mediaId": 2,
            }]
            stats = build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"player_fol_fs_walk": media},
                [{"eventId": "player_fol_fs_walk", "traversalStatus": "complete"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json")
                .read_text(encoding="utf-8")
            )
            event_a = payload["characters"]["chr_a"]["animationEvents"][0]
            event_b = payload["characters"]["chr_b"]["animationEvents"][0]
            self.assertEqual(len(payload["characters"]["chr_a"]["animationEvents"]), 1)
            self.assertEqual(event_a["animationOwnerCount"], 2)
            self.assertEqual(event_b["animationOwnerCount"], 2)
            self.assertEqual(event_a["animationOwnershipScope"], "sharedPlayableCharacters")
            self.assertEqual(event_a["possibleMediaScope"], "sharedEventGraph")
            self.assertEqual(event_a["animationFunctions"], ["OnCustomFootStep"])
            self.assertEqual(event_a["id"], "player_fol_fs_walk")
            self.assertEqual(event_a["authoredEventIds"], ["Player_FOL_FS_Walk", "player_fol_fs_walk"])
            self.assertEqual(event_a["eventAliases"], ["Player_FOL_FS_Walk"])
            self.assertEqual(payload["characters"]["chr_a"]["metrics"]["sharedAnimationEventCount"], 1)
            self.assertEqual(payload["characters"]["chr_a"]["metrics"]["uniqueEventMediaPairCount"], 2)
            self.assertEqual(stats["characterAnimationUniqueEvents"], 1)
            self.assertEqual(stats["characterAnimationSharedEvents"], 1)
            self.assertEqual(stats["characterAnimationSharedEventAssociations"], 2)
            self.assertEqual(stats["characterAnimationSingleOwnerPossibleMediaAssociations"], 0)
            self.assertEqual(stats["characterAnimationSharedGraphPossibleMedia"], 2)
            self.assertEqual(stats["gameplayAudioRefsLinked"], 2)
            self.assertEqual(stats["gameplayPossibleMediaAssociations"], 4)
            self.assertEqual(stats["gameplayRawPossibleMediaAssociations"], 4)

    def test_published_counts_follow_serialized_skill_event_merges(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            references = {
                "eventNames": {"au_shared_buff"},
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal_1",
                    "events": {"au_shared_buff": [{"kind": "buffData"}]},
                }, {
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal_2",
                    "events": {"au_shared_buff": [{"kind": "buffData"}]},
                }],
                "animationOwners": [],
                "profileVoiceOwners": [],
                "counts": {},
            }
            media = [{"src": "data/audio/shared/buff_1.wav", "mediaId": 1}, {
                "src": "data/audio/shared/buff_2.wav", "mediaId": 2,
            }]
            stats = build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"au_shared_buff": media},
                [{"eventId": "au_shared_buff", "traversalStatus": "complete"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8")
            )
            group = payload["characters"]["chr_test"]["groups"]["normal"]
            self.assertEqual(len(group["events"]), 1)
            self.assertEqual(group["events"][0]["sourceSkillIds"], ["chr_test_normal_1", "chr_test_normal_2"])
            self.assertEqual(stats["gameplayRawAudioRefsLinked"], 2)
            self.assertEqual(stats["gameplayAudioRefsLinked"], 1)
            self.assertEqual(stats["gameplayRawPossibleMediaAssociations"], 4)
            self.assertEqual(stats["gameplayPossibleMediaAssociations"], 2)
            self.assertEqual(payload["characters"]["chr_test"]["metrics"]["skillEventAssociationCount"], 1)


if __name__ == "__main__":
    unittest.main()
