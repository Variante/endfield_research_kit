import copy
import json
import tempfile
import unittest
from pathlib import Path
from struct import pack
from unittest.mock import patch

from scripts import build_audio_semantics as audio_semantics
from scripts.audio_semantics import (
    audio_cue_native,
    authored_components,
    event_projection,
    event_summary,
    identifiers,
    interactive_components,
    managed_literals,
    model_view_projection,
    native_evidence,
    purpose,
    responsive_voice,
    table_contexts,
    voice_requests,
)
from scripts.story_builder import level_bindings


def validated_native_context() -> native_evidence.NativeAudioEvidence:
    return native_evidence.NativeAudioEvidence(
        Path("global-metadata.dat"),
        Path("GameAssembly.dll"),
        "validated",
        native_evidence.EXPECTED_METADATA_SHA256,
        native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
    )


def mp_string(value: str | None) -> bytes:
    if value is None:
        return pack("<I", 0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return pack("<I", len(encoded)) + encoded


def ability_voice_trigger_fixture(
    trigger_key: str,
    *,
    enabled: bool = True,
    speaker_type: int = 1,
) -> bytes:
    encoded = trigger_key.encode("ascii")
    return b"".join((
        b"fixture-prefix",
        b"\xfa\x7c\x01\x08",
        bytes((int(enabled),)),
        pack("<iiiiii", 0, 0, 23, 0, speaker_type, len(encoded)),
        encoded,
        b"target-settings-tail",
    ))


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


PATROL_PLAY_AUDIO_ACTION = bytes.fromhex(
    "1a0000000000000000000000000000000000000000000000000000ffffffff"
    "0000000000000000000000000000000080400000000000000000000000000001"
    "0000000000000000000000000101e079120b0b00000000000000"
)


def patrol_leveldata_fixture() -> bytes:
    patrol = b"".join((
        b"\x09",
        pack("<i", 0),
        pack("<f", 4.0),
        b"\x00\x00\x01",
        mp_string(""),
        pack("<iii", 0, 280007, 1),
        b"\x03",
        pack("<i", 1),
        PATROL_PLAY_AUDIO_ACTION,
        pack("<i", 0),
        pack("<fff", 1.0, 2.0, 3.0),
    ))
    return b"\x2bfixture" + pack("<i", 1) + patrol


def char_interact_audio_action(event_id: int) -> bytes:
    return b"".join((
        b"\x02\x0f\x03\x00",
        pack("<iI", 0, 0),
        pack("<fBfI", 0.5, 0, -1.0, 0),
        b"\x00" + pack("<I", 9) + b"\x00\x00\x00",
        pack("<iIiBB", 1, event_id, -1, 1, 1),
    ))


def char_interact_fixture(event_id: int) -> bytes:
    action = char_interact_audio_action(event_id)
    return b"".join((
        b"\x1b", pack("<I", 0), b"\x00", b"\x01" + pack("<I", 0),
        pack("<i", 0), pack("<II", 0, 0), b"\xff\x00", pack("<II", 0, 0),
        pack("<fB", 0.0, 0), pack("<II", 0, 0), b"\x00",
        pack("<III", 0, 0, 0), b"\x00", pack("<IIiI", 0, 0, 0, 0),
        pack("<I", 1), action, b"\x01" + pack("<I", 0), pack("<I", 0), b"\x00",
    ))


class AudioSemanticDataTests(unittest.TestCase):
    def test_semantic_cli_does_not_select_module_global_game_root(self) -> None:
        args = audio_semantics.parse_args([])
        self.assertIsNone(args.game_root)
        self.assertIsNone(args.metadata)

    def test_ability_voice_trigger_context_uses_exact_union_and_owner_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            export_root = Path(temporary)
            skill_root = (
                export_root / "structured" / "Persistent" / "Data" / "Json"
                / "SkillData"
            )
            skill_root.mkdir(parents=True)
            source = skill_root / "chr_0035_liino_attack1.json"
            source.write_bytes(ability_voice_trigger_fixture("combat_attack01"))
            disabled = skill_root / "chr_0035_liino_attack2.json"
            disabled.write_bytes(ability_voice_trigger_fixture(
                "combat_attack02",
                enabled=False,
            ))
            audio_index = {
                "audioDialogWwiseEventAliases": [
                    {
                        "name": "chr_0035_liino_combat_attack01_sv",
                        "eventHash": 0xD54630C8,
                        "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                    },
                    {
                        "name": "chr_0035_liino_combat_attack02_sv",
                        "eventHash": 0x22E0B181,
                        "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                    },
                ]
            }

            contexts = audio_semantics.collect_ability_voice_trigger_contexts(
                export_root,
                audio_index,
            )

        self.assertEqual(
            list(contexts),
            ["chr_0035_liino_combat_attack01_sv"],
        )
        context = contexts["chr_0035_liino_combat_attack01_sv"][0]
        self.assertEqual(context["actionUnionTag"], "0x017c")
        self.assertEqual(context["serializedMemberCount"], 8)
        self.assertEqual(context["triggerKey"], "combat_attack01")
        self.assertEqual(context["ownerId"], "chr_0035_liino")
        self.assertEqual(context["speakerType"], 1)
        self.assertEqual(context["serverActionIndex"], 23)
        self.assertEqual(
            context["playbackPlacementStatus"],
            "authoredPossibleTrigger",
        )
        self.assertIn("VoiceManager.ResponseOnEntity", context["runtimeRoute"])

    def test_native_voice_trigger_context_uses_fingerprint_locked_callsite(self) -> None:
        audio_index = {
            "audioDialogWwiseEventAliases": [
                {
                    "name": "eny_fixture_combat_hurt_break_sv",
                    "eventHash": 0x12345678,
                    "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                },
                {
                    "name": "eny_fixture_combat_hurt_light_sv",
                    "eventHash": 0x87654321,
                    "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                },
            ]
        }
        contexts = voice_requests.collect_native_voice_trigger_contexts(
            audio_index,
            validated_native_context(),
        )

        self.assertEqual(list(contexts), ["eny_fixture_combat_hurt_break_sv"])
        context = contexts["eny_fixture_combat_hurt_break_sv"][0]
        self.assertEqual(context["triggerKey"], "combat_hurt_break")
        self.assertEqual(context["consumerMethod"], "SendVoiceTriggerEventOnPoiseBroken")
        self.assertEqual(context["literalLoadVa"], "0x186d7605e")
        self.assertEqual(context["playbackInvocationVa"], "0x186d7606b")
        self.assertEqual(
            context["playbackPlacementStatus"],
            "exactNativeTriggerCompatibleVoiceDefinition",
        )

    def test_native_voice_trigger_context_fails_closed_on_binary_drift(self) -> None:
        contexts = voice_requests.collect_native_voice_trigger_contexts(
            {"audioDialogWwiseEventAliases": []},
            native_evidence.NativeAudioEvidence(
                Path("metadata"), Path("GameAssembly.dll"), "mismatched"
            ),
        )
        self.assertEqual(contexts, {})

    def test_native_voice_trigger_rows_include_hurt_and_enemy_ai_literals(self) -> None:
        rows = native_evidence.NATIVE_VOICE_TRIGGER_ROWS
        self.assertEqual(rows["combat_hurt_lowhp"]["consumerMethod"], "SendVoiceTriggerEventOnHurt")
        self.assertEqual(rows["combat_hurt_lowhp"]["playbackInvocationVa"], "0x1846fd0ad")
        self.assertEqual(rows["combat_hurt_stun"]["literalLoadVa"], "0x186d76116")
        self.assertEqual(rows["combat_alarm_yell"]["consumerMethod"], "OnEnter")
        self.assertEqual(rows["defence_running"]["additionalMethodIndex"], 43161)
        self.assertEqual(rows["defence_reachcore"]["playbackInvocationVa"], "0x186b3d4b4")
        self.assertEqual(rows["combat_outbattle_flee"]["methodIndex"], 42873)

    def test_builds_native_voice_trigger_catalog_row(self) -> None:
        rows = audio_semantics._build_native_voice_trigger_contexts([{
            "id": "eny_fixture_combat_hurt_break_sv",
            "hash": 0x12345678,
            "category": "voice",
            "foundInWwise": True,
            "possibleMediaCount": 1,
            "media": [],
            "contexts": [{
                "kind": "nativeVoiceTriggerCallsite",
                "triggerKey": "combat_hurt_break",
                "triggerRole": "poiseBrokenResponse",
                "targetBinding": "poiseBrokenEntity",
                "consumerType": "Beyond.Gameplay.Core.BattleManager",
                "consumerMethod": "SendVoiceTriggerEventOnPoiseBroken",
                "methodIndex": 59750,
                "methodVa": "0x186d75ff0",
                "literalLoadVa": "0x186d7605e",
                "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
                "playbackInvocationVa": "0x186d7606b",
                "nativeMappingId": "fixture",
                "triggerBindingStatus": "exact",
                "runtimeSelectionStatus": "unobserved",
                "runtimeActivationStatus": "unobserved",
            }],
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "nativeVoiceTriggerCallsite")
        self.assertEqual(rows[0]["triggerRole"], "poiseBrokenResponse")
        self.assertEqual(rows[0]["owner"]["methodIndex"], 59750)

    def test_animation_voice_trigger_uses_exact_clip_owner_and_native_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export_root = root / "export"
            clip_root = export_root / voice_requests.ANIMATION_VOICE_CLIP_RELS[0]
            clip_root.mkdir(parents=True)
            (clip_root / "A_monster_wgthorns_hit_mid_right_pBB4608B41849F22B.anim").write_text(
                "\n".join((
                    "  m_Name: A_monster_wgthorns_hit_mid_right",
                    "  m_Events:",
                    "  - time: 0",
                    "    functionName: TriggerVoice",
                    "    data: combat_hurt_light",
                    "    floatParameter: 0",
                    "    intParameter: 3",
                )),
                encoding="utf-8",
            )
            metadata_path = root / "global-metadata.dat"
            metadata_path.write_bytes(b"metadata")
            (root / "GameAssembly.dll").write_bytes(b"assembly")
            audio_index = {
                "audioDialogWwiseEventAliases": [
                    {
                        "name": "eny_0088_wgthorns_combat_hurt_light_sv",
                        "eventHash": 0x11111111,
                        "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                    },
                    {
                        "name": "eny_0089_wgthorns_combat_hurt_light_sv",
                        "eventHash": 0x12345678,
                        "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                    },
                    {
                        "name": "eny_9999_other_combat_hurt_light_sv",
                        "eventHash": 0x87654321,
                        "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                    },
                ]
            }
            contexts = voice_requests.collect_animation_voice_trigger_contexts(
                export_root,
                audio_index,
                validated_native_context(),
            )

        self.assertEqual(list(contexts), [
            "eny_0088_wgthorns_combat_hurt_light_sv",
            "eny_0089_wgthorns_combat_hurt_light_sv",
        ])
        context = contexts["eny_0089_wgthorns_combat_hurt_light_sv"][0]
        self.assertEqual(context["kind"], "animationVoiceTrigger")
        self.assertEqual(context["ownerId"], "eny_0089_wgthorns")
        self.assertEqual(context["triggerKey"], "combat_hurt_light")
        self.assertEqual(context["intParameter"], 3)
        self.assertEqual(context["methodIndex"], 53421)
        self.assertEqual(context["playbackInvocationVa"], "0x186c9c9b2")
        self.assertEqual(context["confidence"], "exactSharedIdentityTokenCandidate")
        self.assertEqual(context["ownerCandidateIds"], [
            "eny_0088_wgthorns", "eny_0089_wgthorns",
        ])
        self.assertEqual(context["animationOwnershipScope"], "sharedIdentityToken")

        rows = audio_semantics._build_animation_voice_trigger_contexts([{
            "id": "eny_0089_wgthorns_combat_hurt_light_sv",
            "hash": 0x12345678,
            "category": "voice",
            "foundInWwise": True,
            "possibleMediaCount": 1,
            "media": [],
            "contexts": [context],
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "animationVoiceTrigger")
        self.assertEqual(rows[0]["situation"]["ownerId"], "eny_0089_wgthorns")
        self.assertEqual(rows[0]["action"]["intParameter"], 3)

    def test_animation_voice_trigger_parser_does_not_promote_post_audio(self) -> None:
        rows = voice_requests._animation_voice_trigger_rows(b"\n".join((
            b"  m_Events:",
            b"  - time: 0.25",
            b"    functionName: PostAudioEvent",
            b"    data: combat_hurt_light",
            b"    intParameter: 7",
            b"  - time: 0.5",
            b"    functionName: TriggerVoice",
            b"    data: combat_hurt_heavy",
            b"    intParameter: 2",
        )))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["triggerKey"], "combat_hurt_heavy")
        self.assertEqual(rows[0]["intParameter"], 2)

    def test_lua_post_event_contexts_and_trigger_rows_keep_runtime_boundary(self) -> None:
        audio_index = {
            "luaAudioReferences": [
                {
                    "kind": "luaPostEvent",
                    "name": "au_ui_fixture",
                    "hash": 123,
                    "method": "PostEvent",
                    "source": "Data/LuaScripts/UI/Fixture.lua",
                    "line": 17,
                    "expression": 'AudioAdapter.PostEvent("au_ui_fixture")',
                },
                {
                    "kind": "luaRtpcParameter",
                    "name": "au_rtpc_fixture",
                    "hash": 456,
                },
            ]
        }

        contexts = audio_semantics.lua_audio_contexts(audio_index)
        self.assertEqual(list(contexts), ["au_ui_fixture"])
        self.assertEqual(contexts["au_ui_fixture"][0]["line"], 17)
        self.assertEqual(
            contexts["au_ui_fixture"][0]["runtimeActivationStatus"],
            "luaBranchExecutionNotObserved",
        )

        event = {
            "id": "au_ui_fixture",
            "foundInWwise": True,
            "contexts": contexts["au_ui_fixture"],
            "media": [{"mediaId": 9, "src": "/fixture.flac"}],
        }
        rows = audio_semantics._build_lua_post_event_trigger_contexts([event])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "luaPostEvent")
        self.assertEqual(rows[0]["owner"]["ownerStatus"], "exactLuaFileAndLine")
        self.assertEqual(rows[0]["runtimeActivationStatus"], "luaBranchExecutionNotObserved")

    def test_owner_unresolved_gameplay_config_reference_becomes_exact_static_context(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            gameplay_path = webui_root / "data/lang/CN/gameplay/sound_effects.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({
                "schemaVersion": 5,
                "authoredConfigEventReferences": [{
                    "eventId": "au_skill_orphan_exact",
                    "configKind": "SkillData",
                    "configId": "skill_orphan",
                    "sourcePaths": [
                        "structured/StreamingAssets/Data/Json/SkillData/skill_orphan.json"
                    ],
                    "ownerLinkStatus": "unresolved",
                    "evidence": "exactMemoryPackLengthPrefixedAudioEventString",
                    "runtimeExecutionStatus": "configRuntimeExecutionNotObserved",
                }],
                "characters": {},
                "enemies": {},
            }), encoding="utf-8")

            contexts = audio_semantics.collect_gameplay_contexts(webui_root, "CN")
            context = contexts["au_skill_orphan_exact"][0]
            self.assertEqual(context["kind"], "gameplayConfigAudioReference")
            self.assertEqual(context["configKind"], "SkillData")
            self.assertEqual(context["configId"], "skill_orphan")
            self.assertEqual(context["ownerLinkStatus"], "unresolved")

            rows = audio_semantics._build_gameplay_config_trigger_contexts([{
                "id": "au_skill_orphan_exact",
                "hash": 123,
                "category": "sfx",
                "foundInWwise": True,
                "possibleMediaCount": 1,
                "playbackRole": "playable",
                "media": [{"id": "777", "src": "/audio/777.flac"}],
                "contexts": [context],
            }])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["semanticKind"], "gameplayConfigAudioReference")
            self.assertEqual(row["owner"]["configId"], "skill_orphan")
            self.assertEqual(row["owner"]["ownerStatus"], "gameplayOwnerUnresolved")
            self.assertEqual(row["selection"]["memberFieldStatus"], "undecodedConfigMember")
            self.assertEqual(
                row["runtimeActivationStatus"],
                "configRuntimeExecutionNotObserved",
            )

    def test_trigger_context_catalog_keeps_radio_envtalk_and_timeline_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            conv_root = webui_root / "data/lang/CN/conv"
            conv_root.mkdir(parents=True)
            (conv_root / "radio_fixture.json").write_text(
                json.dumps({
                    "kind": "radio",
                    "title": "radio_fixture",
                    "lines": [{
                        "id": "radio_fixture_001",
                        "actor": "Radio NPC",
                        "text": "fixture radio line",
                        "audio": "au_radio_fixture_001",
                        "cid": 1,
                    }],
                }),
                encoding="utf-8",
            )
            (conv_root / "env_envTalk_fixture.json").write_text(
                json.dumps({
                    "kind": "env",
                    "title": "envTalk_fixture",
                    "cooldown": 10.0,
                    "lines": [{
                        "id": "envTalk_fixture",
                        "cid": 1,
                        "aid": "npc_slot",
                        "actor": "Slot NPC",
                        "text": "fixture env line",
                        "audio": "au_envtalk_fixture_001",
                        "slot": 2,
                        "_debug": {
                            "table": "EnvTalkTable.envTalkDataList",
                            "source": {"envTalkId": "envTalk_fixture"},
                            "speakerHints": [{
                                "proxyId": "proxy_fixture",
                                "source": {
                                    "fields": {
                                        "proxyId": "proxy_fixture",
                                        "levelId": "map01_lv001",
                                    },
                                },
                                "proxyInfoData": {
                                    "npcId": "npc_fixture",
                                    "npcNameId": "npc_fixture_name",
                                    "npcProxyType": "NpcProxy",
                                },
                            }],
                        },
                    }],
                }),
                encoding="utf-8",
            )
            media_rows = [
                {
                    "id": "au_radio_fixture_001",
                    "src": "/audio/radio.flac",
                    "duration": 1.0,
                    "audioCategory": "story_voice",
                    "radioTriggerContexts": [{
                        "levelScriptId": "map01_lv001",
                        "action": "PlayRadioAndWait",
                        "triggerRole": "LevelScriptRadioAction",
                        "radioId": "radio_fixture",
                        "recordUid": "uid-radio",
                        "recordStart": 100,
                        "sourcePath": "Persistent/fixture_level_script.json",
                        "fields": {"onlyOnce": True},
                        "audioDialogMatchEvidence": "exactAudioDialogPath",
                        "radioLine": {
                            "lineId": "radio_fixture_001",
                            "radioId": "radio_fixture",
                            "lineOrdinal": 0,
                            "source": "RadioTable/radio_fixture.json",
                        },
                    }],
                },
                {
                    "id": "au_envtalk_fixture_001",
                    "src": "/audio/env.flac",
                    "duration": 2.0,
                    "speakerChannel": "man_fixture",
                    "audioCategory": "story_voice",
                },
                {
                    "id": "au_timeline_fixture",
                    "src": "/audio/timeline.flac",
                    "duration": 3.0,
                    "audioCategory": "sfx",
                    "audioDialogPath": "AudioDialog/au_timeline_fixture",
                },
            ]
            event_rows = [{
                "id": "au_timeline_fixture",
                "category": "sfx",
                "runtimeSelection": "singlePossibleMedia",
                "mediaRelationTypes": ["directSound"],
                "media": [{"id": "au_timeline_fixture", "src": "/audio/timeline.flac"}],
                "contexts": [{
                    "kind": "levelSequenceAudio",
                    "triggerRole": "TimelineAssetPlayback",
                    "confidence": "inferred",
                    "timelineAssetName": "fixture_Audio",
                    "timelineAssetSerializedFile": "CAB-fixture",
                    "timelineAssetPathId": 7,
                    "audioPlayablePathId": 8,
                    "timelineTrackName": "Audio Track",
                    "timelineClipIndex": 0,
                    "triggerBindingStatus": "timelineParentNotLevelSequence",
                    "ownershipEvidenceLevel": "exactSerializedTimelineCarrier",
                    "triggerEvidenceLevel": "inferred",
                    "runtimeActivationStatus": "audioEventRuntimePlaybackUnobserved",
                    "timelineAssetSource": "VFS/fixture.chk",
                    "timelineTrackSource": "VFS/fixture.chk",
                }],
            }]

            catalog = audio_semantics.build_trigger_context_catalog(
                event_rows,
                media_rows,
                webui_root,
                "CN",
            )

            self.assertEqual(
                {"radio": 1, "envTalk": 1, "timelineAudio": 1},
                catalog["counts"]["bySemanticKind"],
            )
            self.assertEqual(3, catalog["counts"]["total"])
            self.assertEqual(0, catalog["counts"]["runtimeExecutionObserved"])
            self.assertEqual(3, catalog["counts"]["runtimeExecutionUnobserved"])
            by_kind = {
                row["semanticKind"]: row for row in catalog["contexts"]
            }
            radio = by_kind["radio"]
            self.assertEqual("radio_fixture_001", radio["situation"]["lineId"])
            self.assertEqual("fixture radio line", radio["meaning"]["text"])
            self.assertEqual("exactRadioTableLine", radio["evidence"]["owner"])
            self.assertEqual("/audio/radio.flac", radio["mediaRefs"][0]["src"])

            envtalk = by_kind["envTalk"]
            self.assertEqual(["proxy_fixture"], envtalk["situation"]["proxyIds"])
            self.assertEqual("map01_lv001", envtalk["situation"]["levelIds"][0])
            self.assertEqual("npc_slot", envtalk["owner"]["slotActorId"])
            self.assertEqual("proxyHintDoesNotMatchLineActor", envtalk["owner"]["slotActorMatchStatus"])
            self.assertEqual("man_fixture", envtalk["owner"]["speakerChannel"])
            self.assertEqual("runtimeSlotSelectionUnobserved", envtalk["selection"]["slotSelectionStatus"])
            self.assertEqual("fixture env line", envtalk["meaning"]["text"])

            timeline = by_kind["timelineAudio"]
            self.assertEqual("fixture_Audio", timeline["situation"]["timelineAssetName"])
            self.assertEqual("timelineParentNotLevelSequence", timeline["selection"]["triggerBindingStatus"])
            self.assertEqual("audioEventRuntimePlaybackUnobserved", timeline["runtimeActivationStatus"])
            self.assertEqual("/audio/timeline.flac", timeline["mediaRefs"][0]["src"])

    def test_trigger_context_catalog_includes_cutscene_timeline_media_context(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            catalog = audio_semantics.build_trigger_context_catalog(
                [{
                    "id": "au_cutscene_fixture",
                    "category": "sfx",
                    "runtimeSelection": "singlePossibleMedia",
                    "media": [{"id": "au_cutscene_fixture", "src": "/audio/cutscene.flac"}],
                    "contexts": [{
                        "kind": "cutsceneTimeline",
                        "storyKey": "cutscene_fixture",
                        "evidence": "authoredTimelineOrLevelSequence",
                    }],
                }],
                [],
                webui_root,
                "CN",
            )
            self.assertEqual({"timelineAudio": 1}, catalog["counts"]["bySemanticKind"])
            row = catalog["contexts"][0]
            self.assertEqual("cutscene_fixture", row["situation"]["storyKey"])
            self.assertEqual("CutsceneTimelineAudio", row["triggerRole"])
            self.assertEqual("authoredTimelineOrLevelSequence", row["evidence"]["owner"])
            self.assertEqual("cutsceneTimelineRuntimeExecutionNotObserved", row["runtimeActivationStatus"])
            self.assertEqual("storyCutsceneAudioReferenceOnly", row["owner"]["runtimeCarrierStatus"])
            self.assertEqual(["storyCutsceneAudioEventList"], row["evidence"]["requestEvidence"])
            self.assertEqual("/audio/cutscene.flac", row["mediaRefs"][0]["src"])

    def test_cutscene_event_maps_preserve_cached_binary_placements(self) -> None:
        merged = audio_semantics.merge_cutscene_event_maps(
            {
                "cutscene_binary_only": ["au_sfx_binary_only"],
                "cutscene_shared": ["AU_SFX_SHARED"],
            },
            {
                "cutscene_story_only": ["au_sfx_story_only"],
                "cutscene_shared": ["au_sfx_shared", "au_sfx_story_extra"],
            },
        )
        self.assertEqual(["au_sfx_binary_only"], merged["cutscene_binary_only"])
        self.assertEqual(["au_sfx_story_only"], merged["cutscene_story_only"])
        self.assertEqual(
            ["AU_SFX_SHARED", "au_sfx_story_extra"],
            merged["cutscene_shared"],
        )

    def test_cutscene_audio_reference_marks_event_id_carrier_match_without_claiming_exact_join(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            catalog = audio_semantics.build_trigger_context_catalog(
                [{
                    "id": "au_cutscene_match_fixture",
                    "category": "music",
                    "foundInWwise": True,
                    "media": [],
                    "contexts": [
                        {
                            "kind": "cutsceneTimeline",
                            "storyKey": "cutscene_match_fixture",
                            "evidence": "authoredTimelineOrLevelSequence",
                        },
                        {
                            "kind": "levelSequenceAudio",
                            "timelineAssetName": "cutscene_match_fixture_Audio",
                            "timelineAssetPathId": 10,
                            "timelineTrackPathId": 11,
                            "audioPlayableRuntimeContractId": "timelineMusicEventKey.audioMusic",
                            "audioPlayableType": "AudioMusicPlayable",
                            "evidence": "exactSerializedTimelineCarrier",
                        },
                    ],
                }],
                [],
                webui_root,
                "CN",
            )
            rows = catalog["contexts"]
            generic = next(row for row in rows if row["situation"]["contextKind"] == "cutsceneTimeline")
            self.assertEqual(
                "eventIdAlsoHasSerializedTimelineCarrier",
                generic["owner"]["runtimeCarrierStatus"],
            )
            self.assertEqual(["storyCutsceneAudioEventList"], generic["evidence"]["requestEvidence"])
            self.assertEqual(
                {
                    "eventIdAlsoHasSerializedTimelineCarrier": 1,
                    "serializedPlayableCarrier": 1,
                },
                catalog["coverage"]["timelineAudio"]["rowsByCarrierEvidence"],
            )

    def test_trigger_context_catalog_keeps_greet_envtalk_as_separate_kind(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            conv_root = webui_root / "data/lang/CN/conv"
            conv_root.mkdir(parents=True)
            (conv_root / "env_greetEnvTalk_fixture.json").write_text(
                json.dumps({
                    "kind": "misc",
                    "title": "greetEnvTalk_fixture",
                    "mission": "greet",
                    "lines": [{
                        "id": "greetEnvTalk_fixture",
                        "audio": "au_greetEnvTalk_fixture",
                        "duration": 5.0,
                        "slot": 1,
                    }, {
                        "id": "greetEnvTalk_fixture",
                        "audio": "au_greetEnvTalk_fixture",
                        "duration": 5.0,
                        "slot": 1,
                    }],
                }),
                encoding="utf-8",
            )
            catalog = audio_semantics.build_trigger_context_catalog(
                [],
                [{
                    "id": "au_greetEnvTalk_fixture",
                    "src": "/audio/greet.flac",
                    "speakerChannel": "fixture",
                }],
                webui_root,
                "CN",
            )
            self.assertEqual({"envTalkGreeting": 2}, catalog["counts"]["bySemanticKind"])
            self.assertEqual(2, len({row["triggerId"] for row in catalog["contexts"]}))
            row = catalog["contexts"][0]
            self.assertEqual("envTalkGreeting", row["semanticKind"])
            self.assertEqual("greetEnvTalk", row["situation"]["envTalkVariant"])
            self.assertEqual("exactEnvTalkTableGreeting", row["evidence"]["definition"])
            self.assertEqual("/audio/greet.flac", row["mediaRefs"][0]["src"])

    def test_trigger_context_catalog_recovers_remote_common_auto_play_event(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            table_path = root / "export_full/structured/Persistent/Table/RemoteCommonTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(
                json.dumps({
                    "remotecomm_fixture": {
                        "autoPlay": True,
                        "startAudioEvent": "",
                        "endAudioEvent": "",
                        "remoteCommSingleDataList": [{
                            "singleId": "remotecomm_fixture_001",
                            "index": 1,
                            "middleId": "npc_fixture",
                            "actorList": ["npc_fixture"],
                            "audioId": "au_sfx_remotecomm_fixture",
                            "voiceId": "au_remotecomm_fixture_001",
                            "autoPlayTime": -1.0,
                        }],
                    },
                }),
                encoding="utf-8",
            )
            catalog = audio_semantics.build_trigger_context_catalog(
                [{
                    "id": "au_sfx_remotecomm_fixture",
                    "hash": 123,
                    "category": "sfx",
                    "foundInWwise": True,
                    "possibleMediaCount": 1,
                    "playRootCount": 1,
                    "runtimeSelection": "singlePossibleMedia",
                    "mediaRelationTypes": ["directSound"],
                    "media": [{
                        "id": "au_sfx_remotecomm_fixture",
                        "src": "/audio/remote.flac",
                    }],
                }],
                [],
                webui_root,
                "CN",
                export_root=root / "export_full",
            )
            self.assertEqual({"remoteCommonAudio": 1}, catalog["counts"]["bySemanticKind"])
            row = catalog["contexts"][0]
            self.assertEqual("remotecomm_fixture", row["situation"]["remoteCommonId"])
            self.assertEqual("remotecomm_fixture_001", row["situation"]["singleId"])
            self.assertEqual("au_sfx_remotecomm_fixture", row["meaning"]["eventId"])
            self.assertEqual("au_remotecomm_fixture_001", row["owner"]["voiceId"])
            self.assertEqual("separateRemoteCommonVoiceId", row["owner"]["voiceLinkStatus"])
            self.assertEqual("/audio/remote.flac", row["mediaRefs"][0]["src"])
            self.assertEqual("exactRemoteCommonAudioId", row["selection"]["audioSelectionStatus"])
            self.assertEqual("remoteCommonAutoPlayExecutionNotObserved", row["runtimeActivationStatus"])

    def test_trigger_context_catalog_includes_dialog_timeline_voice_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            conv_root = webui_root / "data/lang/CN/conv"
            conv_root.mkdir(parents=True)
            (conv_root / "dlg_fixture.json").write_text(
                json.dumps({
                    "kind": "dlg",
                    "key": "dlg_fixture",
                    "_debug": {
                        "lineOrder": {
                            "mode": "dialogTimeline",
                            "sources": [{
                                "kind": "dialogTimeline",
                                "sourceKey": "dlgtl_fixture_sub_1",
                                "file": "export_full/recovered/fixture",
                            }],
                        },
                    },
                    "lines": [{
                        "id": "dlg_fixture_001",
                        "aid": "npc_fixture",
                        "actor": "Fixture NPC",
                        "text": "fixture dialog line",
                        "audio": "au_dlg_fixture_001",
                        "duration": -1.0,
                        "_debug": {
                            "table": "DialogTable.dialogDataList",
                            "timelineTiming": {
                                "timeline": "dlgtl_fixture_sub_1",
                                "start": 4.5,
                                "duration": 2.75,
                            },
                        },
                    }],
                }),
                encoding="utf-8",
            )
            catalog = audio_semantics.build_trigger_context_catalog(
                [],
                [{
                    "id": "au_dlg_fixture_001",
                    "src": "/audio/dialog.flac",
                    "duration": 2.5,
                    "speakerChannel": "npc_fixture",
                    "audioCategory": "story_voice",
                }],
                webui_root,
                "CN",
            )
            self.assertEqual({"dialogTimeline": 1}, catalog["counts"]["bySemanticKind"])
            row = catalog["contexts"][0]
            self.assertEqual("dlg_fixture", row["situation"]["dialogKey"])
            self.assertEqual("dlgtl_fixture_sub_1", row["situation"]["timelineId"])
            self.assertEqual(4.5, row["selection"]["timelineStartSec"])
            self.assertEqual("npc_fixture", row["owner"]["speakerActorId"])
            self.assertEqual("exactDialogTimelineTiming", row["selection"]["lineScheduleStatus"])
            self.assertEqual("/audio/dialog.flac", row["mediaRefs"][0]["src"])
            self.assertEqual("dialogTimelineRuntimeExecutionNotObserved", row["runtimeActivationStatus"])

    def test_trigger_context_catalog_includes_dialog_lifecycle_hook(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root) / "webui"
            catalog = audio_semantics.build_trigger_context_catalog(
                [{
                    "id": "hashed-event:0x4cd598ce",
                    "name": "hashed-event:0x4cd598ce",
                    "hash": 0x4CD598CE,
                    "category": "unknown",
                    "foundInWwise": True,
                    "possibleMediaCount": 0,
                    "playRootCount": 0,
                    "runtimeSelection": "unresolved",
                    "mediaRelationTypes": [],
                    "traversalStatus": "complete",
                    "media": [],
                    "contexts": [{
                        "kind": "tableEventHash",
                        "table": "AudioDialogCustomEventTable",
                        "path": "dlg_fixture.postEnterEvents[0]",
                        "source": "structured/Persistent/Table/AudioDialogCustomEventTable.json",
                        "signedValue": 1289066702,
                        "eventHash": 0x4CD598CE,
                        "evidence": "authoredUint32EventId",
                    }],
                }],
                [],
                webui_root,
                "CN",
            )
            self.assertEqual({"dialogLifecycle": 1}, catalog["counts"]["bySemanticKind"])
            self.assertEqual(1, catalog["counts"]["dialogLifecycleRowsWithNoDecodedMediaLeaf"])
            row = catalog["contexts"][0]
            self.assertEqual("dlg_fixture", row["situation"]["dialogId"])
            self.assertEqual("postEnterEvents", row["situation"]["lifecyclePhase"])
            self.assertEqual("DialogPostEnterAudioEvent", row["triggerRole"])
            self.assertEqual("_OnPostEnterDialog", row["action"]["runtimeMethod"])
            self.assertEqual("0x060099e8", row["action"]["runtimeMethodToken"])
            self.assertEqual("wwiseEventHasNoDecodedMedia", row["selection"]["mediaSelectionStatus"])
            self.assertEqual("dialogLifecycleRuntimeExecutionNotObserved", row["runtimeActivationStatus"])
            self.assertEqual([], row["mediaRefs"])

    def test_levelsequence_id_normalization_requires_exact_audio_suffix(self) -> None:
        self.assertEqual(
            audio_semantics.normalize_levelsequence_audio_id("levelseq_fixture_Audio"),
            "levelseq_fixture",
        )
        self.assertEqual(
            audio_semantics.normalize_levelsequence_audio_id("levelseq_fixture_audio"),
            "",
        )
        self.assertEqual(
            audio_semantics.normalize_levelsequence_audio_id("f_levelseq_fixture_Audio"),
            "",
        )

    def test_levelsequence_contexts_separate_exact_inferred_and_gap(self) -> None:
        ownership = {
            "occurrencesByEvent": {
                "au_exact": [{
                    "timelineAssetName": "levelseq_exact_Audio",
                    "timelineAssetNameBase": "levelseq_exact",
                    "timelineAssetSerializedFile": "CAB-a",
                    "timelineAssetPathId": 20,
                    "timelineTrackName": "Audio Track",
                    "audioPlayableType": "AudioEventPlayable",
                    "playableDirectors": [{"playableDirectorName": "PlayableDirector"}],
                    "evidence": "fixtureCarrier",
                }],
                "au_inferred": [{
                    "timelineAssetName": "levelseq_inferred_Audio",
                    "timelineAssetNameBase": "levelseq_inferred",
                    "timelineAssetSerializedFile": "CAB-b",
                    "timelineAssetPathId": 21,
                    "timelineTrackName": "Audio Track",
                    "audioPlayableType": "AudioEventPlayable",
                    "playableDirectors": [],
                    "evidence": "fixtureCarrier",
                }],
            }
        }
        actions = {
            "actionsByLevelSequenceId": {
                "levelseq_exact": [{
                    "action": "PlayLevelSequence",
                    "levelSequenceId": "levelseq_exact",
                    "levelScriptId": "map/1",
                }]
            }
        }
        result = audio_semantics.build_levelsequence_audio_contexts(
            ["au_exact", "au_inferred", "au_gap"], ownership, actions
        )
        exact = result["eventContexts"]["au_exact"][0]
        inferred = result["eventContexts"]["au_inferred"][0]
        gap = result["eventContexts"]["au_gap"][0]
        self.assertEqual(exact["confidence"], "exact")
        self.assertEqual(exact["triggerBindingStatus"], "exactLevelSequenceIdJoin")
        self.assertEqual(inferred["confidence"], "inferred")
        self.assertEqual(inferred["triggerEvidenceLevel"], "inferred")
        self.assertEqual(gap["confidence"], "gap")
        self.assertEqual(
            gap["triggerBindingStatus"],
            "timelineCarrierMissingFromCurrentObjectIndex",
        )
        self.assertEqual(result["stats"]["eventsWithoutTimelineCarrier"], 1)

    def test_timeline_object_index_joins_playable_track_parent_and_director(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            export_root.mkdir()
            mono_path = export_root / "mono.jsonl"
            director_path = export_root / "director.jsonl"
            def object_row(path_id, name, scalars=None, pptrs=None):
                return {
                    "recordType": "object",
                    "object": {
                        "serializedFile": "CAB-fixture",
                        "source": "fixture.chk",
                        "sourceOffset": path_id * 10,
                        "pathId": path_id,
                    },
                    "type": "MonoBehaviour",
                    "name": name,
                    "scalars": scalars or [],
                    "pptrs": pptrs or [],
                }
            playable = object_row(
                101,
                "AudioEventPlayable",
                [["$._audioEventKey", "s", "au_fixture"]],
            )
            track = object_row(
                102,
                "Audio Track",
                [["$.m_Clips[2].m_DisplayName", "s", "au_fixture"]],
                [
                    {
                        "path": "$.m_Parent",
                        "target": {
                            "serializedFile": "CAB-fixture",
                            "pathId": 201,
                            "source": "fixture.chk",
                            "sourceOffset": 2010,
                            "type": "MonoBehaviour",
                            "name": "levelseq_fixture_Audio",
                        },
                    },
                    {
                        "path": "$.m_Clips[2].m_Asset",
                        "target": {
                            "serializedFile": "CAB-fixture",
                            "pathId": 101,
                            "name": "AudioEventPlayable",
                        },
                    },
                ],
            )
            director = {
                "recordType": "object",
                "object": {"serializedFile": "CAB-fixture", "pathId": 301},
                "type": "PlayableDirector",
                "name": "fixture director",
                "pptrs": [{
                    "path": "$.m_PlayableAsset",
                    "target": {
                        "serializedFile": "CAB-fixture",
                        "pathId": 201,
                        "name": "levelseq_fixture_Audio",
                    },
                }],
            }
            mono_path.write_text(
                "".join(json.dumps(row) + "\n" for row in [playable, track]),
                encoding="utf-8",
            )
            director_path.write_text(json.dumps(director) + "\n", encoding="utf-8")
            result = audio_semantics.collect_timeline_audio_ownership(
                export_root,
                event_ids=["au_fixture"],
                mono_path=mono_path,
                director_path=director_path,
            )
            occurrence = result["occurrencesByEvent"]["au_fixture"][0]
            self.assertEqual(occurrence["timelineAssetNameBase"], "levelseq_fixture")
            self.assertEqual(occurrence["timelineTrackPathId"], 102)
            self.assertEqual(occurrence["timelineClipIndex"], 2)
            self.assertEqual(occurrence["audioPlayablePathId"], 101)
            self.assertEqual(occurrence["playableDirectors"][0]["playableDirectorPathId"], 301)
            self.assertEqual(result["stats"]["exactTimelineCarriers"], 1)
            self.assertEqual(result["stats"]["exactPlayableDirectorLinks"], 1)

    def test_timeline_object_index_recovers_typed_dialog_audio_id_and_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            export_root.mkdir()
            mono_path = export_root / "mono.jsonl"
            director_path = export_root / "director.jsonl"

            def object_row(path_id, name, scalars=None, pptrs=None):
                return {
                    "recordType": "object",
                    "object": {
                        "serializedFile": "CAB-dialog-audio",
                        "source": "fixture.chk",
                        "sourceOffset": 100,
                        "pathId": path_id,
                    },
                    "type": "MonoBehaviour",
                    "name": name,
                    "scalars": scalars or [],
                    "pptrs": pptrs or [],
                }

            event_hash = identifiers.audio_hash_generator_compute(
                "au_dlg_foley_stop_chr"
            )
            playable = object_row(
                101,
                "DialogAudioEventPlayableAsset",
                [["$.audioEvent._id", "i", event_hash - (1 << 32)]],
            )
            track = object_row(
                102,
                "Dialog Audio Entity Bindable Track",
                [[
                    "$.m_Clips[0].m_DisplayName",
                    "s",
                    "Post Event <au_dlg_foley_stop_chr>",
                ]],
                [
                    {
                        "path": "$.m_Parent",
                        "target": {
                            "serializedFile": "CAB-dialog-audio",
                            "pathId": 201,
                            "source": "fixture.chk",
                            "sourceOffset": 100,
                            "name": "dlgtl_fixture_Audio",
                        },
                    },
                    {
                        "path": "$.m_Clips[0].m_Asset",
                        "target": {
                            "serializedFile": "CAB-dialog-audio",
                            "pathId": 101,
                            "name": "DialogAudioEventPlayableAsset",
                        },
                    },
                ],
            )
            mono_path.write_text(
                "".join(json.dumps(row) + "\n" for row in [playable, track]),
                encoding="utf-8",
            )
            director_path.write_text("", encoding="utf-8")

            result = audio_semantics.collect_timeline_audio_ownership(
                export_root,
                event_ids=[f"hashed-event:0x{event_hash:08x}"],
                mono_path=mono_path,
                director_path=director_path,
            )
            event_id = f"hashed-event:0x{event_hash:08x}"
            occurrence = result["occurrencesByEvent"][event_id][0]
            self.assertEqual(occurrence["authoredEventName"], "au_dlg_foley_stop_chr")
            self.assertEqual(
                occurrence["authoredEventNameEvidence"],
                "exactTimelineDisplayNameHashEqualsSerializedAudioId",
            )
            self.assertEqual(
                occurrence["audioPlayableKeyStatus"],
                "exactDialogAudioEventPlayableAudioIdScalar",
            )
            self.assertEqual(
                occurrence["audioPlayableRuntimeContractId"],
                "timelineAudioId.dialogAudioEvent",
            )

            track["scalars"][0][2] = "Post Event <au_wrong_name>"
            mono_path.write_text(
                "".join(json.dumps(row) + "\n" for row in [playable, track]),
                encoding="utf-8",
            )
            mismatch = audio_semantics.collect_timeline_audio_ownership(
                export_root,
                event_ids=[event_id],
                mono_path=mono_path,
                director_path=director_path,
            )
            mismatch_occurrence = mismatch["occurrencesByEvent"][event_id][0]
            self.assertIsNone(mismatch_occurrence["authoredEventName"])
            self.assertIsNone(mismatch_occurrence["authoredEventNameEvidence"])

    def test_timeline_dialog_audio_clip_survives_compact_display_name_omission(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            export_root.mkdir()
            mono_path = export_root / "mono.jsonl"
            director_path = export_root / "director.jsonl"
            raw_dir = (
                export_root / "recovered" / "AnimeStudio-cli" / "StreamingAssets"
                / "json_by_type" / "MonoBehaviour"
            )
            raw_dir.mkdir(parents=True)
            event_hash = identifiers.audio_hash_generator_compute("au_dialog_exact")
            playable = {
                "recordType": "object",
                "object": {"serializedFile": "CAB-compact", "pathId": 11},
                "name": "DialogAudioEventPlayableAsset",
                "scalars": [["$.audioEvent._id", "i", event_hash]],
            }
            track = {
                "recordType": "object",
                "object": {"serializedFile": "CAB-compact", "pathId": 12},
                "name": "Dialog Audio Entity Bindable Track",
                "scalars": [],
                "pptrs": [
                    {
                        "path": "$.m_Parent",
                        "target": {
                            "serializedFile": "CAB-compact",
                            "pathId": 13,
                            "name": "dlgtl_compact_Audio",
                        },
                    },
                    {
                        "path": "$.m_Clips[0].m_Asset",
                        "target": {
                            "serializedFile": "CAB-compact",
                            "pathId": 11,
                            "name": "DialogAudioEventPlayableAsset",
                        },
                    },
                ],
            }
            mono_path.write_text(
                "".join(json.dumps(row) + "\n" for row in (playable, track)),
                encoding="utf-8",
            )
            director_path.write_text("", encoding="utf-8")
            suffix = f"{12:016X}"
            (raw_dir / f"Dialog Audio Entity Bindable Track_p{suffix}.json").write_text(
                json.dumps({
                    "$animestudio": {"sourceFile": "CAB-compact", "pathId": 12},
                    "m_Clips": [{
                        "m_Start": 4.0,
                        "m_Duration": 5.0,
                        "m_DisplayName": "Post Event <au_dialog_exact>",
                    }],
                }),
                encoding="utf-8",
            )
            ownership = audio_semantics.collect_timeline_audio_ownership(
                export_root,
                event_ids=[f"hashed-event:0x{event_hash:08x}"],
                mono_path=mono_path,
                director_path=director_path,
            )
            event_id = f"hashed-event:0x{event_hash:08x}"
            self.assertEqual(len(ownership["occurrencesByEvent"][event_id]), 1)
            enriched = audio_semantics.enrich_timeline_audio_ownership_from_raw_json(
                export_root, ownership
            )
            occurrence = enriched["occurrencesByEvent"][event_id][0]
            self.assertEqual(occurrence["timelineClipDisplayName"], "Post Event <au_dialog_exact>")
            self.assertEqual(occurrence["authoredEventName"], "au_dialog_exact")

    def test_timeline_raw_json_adds_clip_timing_and_playable_controls(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            export_root.mkdir()
            mono_path = export_root / "mono.jsonl"
            director_path = export_root / "director.jsonl"
            raw_dir = (
                export_root / "recovered" / "AnimeStudio-cli" / "Persistent"
                / "json_by_type" / "MonoBehaviour"
            )
            raw_dir.mkdir(parents=True)

            def object_row(path_id, name, scalars=None, pptrs=None):
                return {
                    "recordType": "object",
                    "object": {
                        "serializedFile": "CAB-raw-fixture",
                        "source": "fixture.chk",
                        "sourceOffset": 100,
                        "pathId": path_id,
                    },
                    "type": "MonoBehaviour",
                    "name": name,
                    "scalars": scalars or [],
                    "pptrs": pptrs or [],
                }

            playable = object_row(
                101,
                "AudioDlgEventPlayable",
                [["$._audioEventKey", "s", "au_raw_fixture"]],
            )
            track = object_row(
                102,
                "Audio Track",
                [["$.m_Clips[0].m_DisplayName", "s", "au_raw_fixture"]],
                [
                    {
                        "path": "$.m_Parent",
                        "target": {
                            "serializedFile": "CAB-raw-fixture",
                            "pathId": 201,
                            "source": "fixture.chk",
                            "sourceOffset": 100,
                            "name": "dlgtl_raw_fixture_Audio",
                        },
                    },
                    {
                        "path": "$.m_Clips[0].m_Asset",
                        "target": {
                            "serializedFile": "CAB-raw-fixture",
                            "pathId": 101,
                            "name": "AudioDlgEventPlayable",
                        },
                    },
                ],
            )
            mono_path.write_text(
                "".join(json.dumps(row) + "\n" for row in [playable, track]),
                encoding="utf-8",
            )
            director_path.write_text("", encoding="utf-8")

            def raw_path(path_id, name):
                suffix = f"{path_id & ((1 << 64) - 1):016X}"
                return raw_dir / f"{name}_p{suffix}.json"

            raw_path(102, "Audio Track").write_text(
                json.dumps({
                    "$animestudio": {
                        "pathId": 102,
                        "sourceFile": "CAB-raw-fixture",
                    },
                    "m_Clips": [{
                        "m_Start": 12.5,
                        "m_Duration": 3.25,
                        "m_ClipIn": 0.25,
                        "m_TimeScale": 1.0,
                        "m_EaseInDuration": 0.1,
                        "m_EaseOutDuration": 0.2,
                        "m_DisplayName": "au_raw_fixture",
                        "optionIndex": 4,
                    }],
                }),
                encoding="utf-8",
            )
            raw_path(101, "AudioDlgEventPlayable").write_text(
                json.dumps({
                    "$animestudio": {
                        "pathId": 101,
                        "sourceFile": "CAB-raw-fixture",
                    },
                    "_audioEventKey": "au_raw_fixture",
                    "_isCue": 0,
                    "_stopEventAtClipEnd": 1,
                    "_fadeOutTime": 500,
                    "_enableSeek": 1,
                    "_useBindingObj": 0,
                    "_is2D": 1,
                }),
                encoding="utf-8",
            )

            ownership = audio_semantics.collect_timeline_audio_ownership(
                export_root,
                event_ids=["au_raw_fixture"],
                mono_path=mono_path,
                director_path=director_path,
            )
            enriched = audio_semantics.enrich_timeline_audio_ownership_from_raw_json(
                export_root,
                ownership,
            )
            occurrence = enriched["occurrencesByEvent"]["au_raw_fixture"][0]
            self.assertEqual(occurrence["timelineClipStartSec"], 12.5)
            self.assertEqual(occurrence["timelineClipEndSec"], 15.75)
            self.assertEqual(occurrence["timelineClipOptionIndex"], 4)
            self.assertEqual(occurrence["audioPlayableStopEventAtClipEnd"], 1)
            self.assertEqual(occurrence["audioPlayableFadeOutMs"], 500)
            self.assertEqual(
                occurrence["audioPlayableRuntimeContractId"],
                "timelineStringEventKey.audioDlg",
            )
            self.assertEqual(
                occurrence["timelineClipTimingEvidence"],
                "exactSerializedTimelineClip",
            )
            self.assertEqual(
                occurrence["audioPlayableControlEvidence"],
                "exactSerializedAudioPlayableFields",
            )
            self.assertEqual(enriched["stats"]["timelineRawClipTimings"], 1)
            self.assertEqual(enriched["stats"]["timelineRawPlayableControls"], 1)

    def test_timeline_runtime_contract_normalizes_clone_suffix(self) -> None:
        self.assertEqual(
            audio_semantics._timeline_audio_runtime_contract_id(
                "AudioDlgEventPlayable(Clone)(Clone)"
            ),
            "timelineStringEventKey.audioDlg",
        )
        self.assertEqual(
            audio_semantics._timeline_audio_runtime_contract_id(
                "AudioEventPlayable"
            ),
            "timelineStringEventKey.audioEvent",
        )
        self.assertEqual(
            audio_semantics._timeline_audio_runtime_contract_id(
                "AudioMusicPlayable(Clone)(Clone)"
            ),
            "timelineMusicEventKey.audioMusic",
        )
        self.assertIsNone(
            audio_semantics._timeline_audio_runtime_contract_id(
                "AudioCuePlayable"
            )
        )

    def test_timeline_audio_cue_playable_keeps_cue_namespace_separate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            export_root.mkdir()
            mono_path = export_root / "mono.jsonl"
            director_path = export_root / "director.jsonl"

            def object_row(path_id, name, scalars=None, pptrs=None):
                return {
                    "recordType": "object",
                    "object": {"serializedFile": "CAB-cue", "pathId": path_id},
                    "type": "MonoBehaviour",
                    "name": name,
                    "scalars": scalars or [],
                    "pptrs": pptrs or [],
                }

            cue = object_row(
                401,
                "AudioCuePlayable",
                [
                    ["$._startCueName", "s", "cue_fixture_start"],
                    ["$._endCueName", "s", "cue_fixture_end"],
                ],
            )
            track = object_row(
                402,
                "Audio Track",
                [["$.m_Clips[0].m_DisplayName", "s", "cue_fixture_start"]],
                [
                    {"path": "$.m_Parent", "target": {"serializedFile": "CAB-cue", "pathId": 501, "name": "seq_fixture_Audio"}},
                    {"path": "$.m_Clips[0].m_Asset", "target": {"serializedFile": "CAB-cue", "pathId": 401, "name": "AudioCuePlayable"}},
                ],
            )
            director = {
                "recordType": "object",
                "object": {"serializedFile": "CAB-cue", "pathId": 601},
                "type": "PlayableDirector",
                "name": "cue director",
                "pptrs": [{"path": "$.m_PlayableAsset", "target": {"serializedFile": "CAB-cue", "pathId": 501, "name": "seq_fixture_Audio"}}],
            }
            mono_path.write_text("".join(json.dumps(row) + "\n" for row in [cue, track]), encoding="utf-8")
            director_path.write_text(json.dumps(director) + "\n", encoding="utf-8")
            ownership = audio_semantics.collect_timeline_audio_ownership(
                export_root, mono_path=mono_path, director_path=director_path
            )
            self.assertIn("cue_fixture_start", ownership["occurrencesByCue"])
            self.assertIn("cue_fixture_end", ownership["occurrencesByCue"])
            self.assertEqual(ownership["stats"]["exactTimelineCueCarriers"], 2)
            cue_id = identifiers.audio_hash_generator_compute("cue_fixture_start")
            cue_semantics = {"cueDefinitions": {cue_id: {
                "handlerCount": 1,
                "directHandlerCount": 1,
                "levelHandlerCount": 0,
                "behaviorEvents": [{
                    "eventId": "au_fixture_cue_event",
                    "handlerScope": "direct",
                    "handlerIndex": 0,
                    "expressionSide": "behavior",
                    "expressionPath": "fixture.behaviourExpr",
                    "exprType": 3,
                }],
                "expressionOperands": [],
            }}}
            result = audio_semantics.build_timeline_audio_cue_contexts(ownership, cue_semantics)
            context = result["eventContexts"]["au_fixture_cue_event"][0]
            self.assertEqual(context["kind"], "timelineAudioCueBehaviorEvent")
            self.assertEqual(context["cueName"], "cue_fixture_start")
            self.assertEqual(context["definitionStatus"], "resolved")
            self.assertEqual(result["stats"]["timelineCueInvocations"], 2)

    def test_timeline_music_playable_joins_when_asset_record_follows_track(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            export_root.mkdir()
            mono_path = export_root / "mono.jsonl"
            director_path = export_root / "director.jsonl"
            raw_dir = (
                export_root / "recovered" / "AnimeStudio-cli" / "Persistent"
                / "json_by_type" / "MonoBehaviour"
            )
            raw_dir.mkdir(parents=True)

            def object_row(path_id, name, scalars=None, pptrs=None):
                return {
                    "recordType": "object",
                    "object": {"serializedFile": "CAB-music", "pathId": path_id},
                    "type": "MonoBehaviour",
                    "name": name,
                    "scalars": scalars or [],
                    "pptrs": pptrs or [],
                }

            # The production object-index order can put a Track before the
            # referenced playable asset.  The clip display name is the class
            # label, while _audioEventKey is the actual Wwise Event identity.
            track = object_row(
                102,
                "Audio Track",
                [["$.m_Clips[0].m_DisplayName", "s", "AudioMusicPlayable"]],
                [
                    {"path": "$.m_Parent", "target": {"serializedFile": "CAB-music", "pathId": 201, "name": "levelseq_music_Audio"}},
                    {"path": "$.m_Clips[0].m_Asset", "target": {"serializedFile": "CAB-music", "pathId": 101, "name": "AudioMusicPlayable"}},
                ],
            )
            playable = object_row(
                101,
                "AudioMusicPlayable",
                [["$._audioEventKey", "s", "au_music_fixture"]],
            )
            mono_path.write_text(
                "".join(json.dumps(row) + "\n" for row in [track, playable]),
                encoding="utf-8",
            )
            director_path.write_text("", encoding="utf-8")
            (raw_dir / "AudioMusicPlayable_p0000000000000065.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "pathId": 101,
                        "sourceFile": "CAB-music",
                    },
                    "_audioEventKey": "au_music_fixture",
                    "musicActionType": 2,
                    "triggerOnSkip": 1,
                }),
                encoding="utf-8",
            )

            result = audio_semantics.collect_timeline_audio_ownership(
                export_root,
                event_ids=["au_music_fixture"],
                mono_path=mono_path,
                director_path=director_path,
            )
            occurrence = result["occurrencesByEvent"]["au_music_fixture"][0]
            self.assertEqual(occurrence["timelineClipDisplayName"], "audiomusicplayable")
            self.assertEqual(occurrence["eventId"], "au_music_fixture")
            self.assertEqual(occurrence["audioPlayableType"], "AudioMusicPlayable")
            self.assertEqual(result["stats"]["exactTimelineMusicCarriers"], 1)
            self.assertEqual(
                result["stats"]["timelineCarrierMusicDisplayNameMismatchAccepted"],
                1,
            )
            enriched = audio_semantics.enrich_timeline_audio_ownership_from_raw_json(
                export_root, result
            )
            occurrence = enriched["occurrencesByEvent"]["au_music_fixture"][0]
            self.assertEqual(occurrence["audioMusicActionType"], 2)
            self.assertEqual(occurrence["audioMusicActionTypeLabel"], "CUSTOM_MUSIC")
            self.assertEqual(occurrence["audioMusicTriggerOnSkip"], 1)
            self.assertEqual(occurrence["audioMusicTriggerOnSkipLabel"], "triggeredOnSkip")

    def test_levelsequence_play_action_helper_keeps_active_overlay_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            path = (
                export_root / "structured/StreamingAssets/Data/Json/LevelScriptData"
                / "fixture/1.json"
            )
            path.parent.mkdir(parents=True)
            path.write_bytes(b"fixture")

            def decode_file(_path, _data):
                return {
                    "targetCount": 1,
                    "rows": [{
                        "record": {
                            "start": 12,
                            "uid": "uid",
                            "localId": 4,
                            "unionTag": 0x0360,
                            "serializedMemberCount": 15,
                        },
                        "recordIndex": 2,
                        "definition": audio_semantics.LEVELSEQUENCE_PLAY_ACTION_DEFINITIONS[(0x0360, 0x0F)],
                        "levelSequenceId": "levelseq_fixture",
                    }],
                }

            result = audio_semantics.collect_levelsequence_play_actions(
                export_root, decode_file=decode_file
            )
            row = result["actionsByLevelSequenceId"]["levelseq_fixture"][0]
            self.assertEqual(row["action"], "PlayLevelSequence")
            self.assertEqual(row["levelScriptId"], "fixture/1")
            self.assertEqual(row["serializedMemberCount"], 15)
            self.assertEqual(row["runtimeActivationStatus"], "playLevelSequenceActionExecutionNotObserved")

    def test_event_summary_preserves_non_media_source_taxonomy(self) -> None:
        row = {
            "id": "au_music_placeholder_fixture",
            "name": "au_music_placeholder_fixture",
            "hash": 1,
            "category": "music",
            "foundInWwise": True,
            "possibleMediaCount": 0,
            "candidateCount": 0,
            "contexts": [],
            "media": [],
            "evidence": [{
                "sourceObjectSummary": {
                    "sourceReferenceCount": 2,
                    "sourceKindCounts": {
                        "externalSourceCodec": 1,
                        "synthesizedSource": 1,
                    },
                    "pluginCounts": {"0x00080001": 1, "0x00650002": 1},
                },
                "nonMediaSourceEvidence": [{
                    "pluginIdHex": "0x00080001",
                    "pluginName": "Wwise External Source",
                    "sourceKind": "externalSourceCodec",
                    "streamTypeLabel": "streamedZeroLatency",
                    "mediaLocationStatus": "unresolvedExternalSource",
                }],
            }],
        }
        summary = event_summary.event_summary_row(row, "event_details/00.json")
        self.assertEqual(
            summary["sourceKinds"],
            ["externalSourceCodec", "synthesizedSource"],
        )
        self.assertEqual(
            summary["sourcePluginIds"],
            ["0x00080001", "0x00650002"],
        )
        self.assertEqual(summary["nonMediaSourceCount"], 1)
        self.assertIn("Wwise External Source", summary["contextSearch"])

    def test_scene_global_compact_fields_project_without_promoting_definition_only(self) -> None:
        row = {
            "id": "au_amb_scene_fixture",
            "name": "au_amb_scene_fixture",
            "hash": 7,
            "category": "ambience",
            "foundInWwise": False,
            "possibleMediaCount": 0,
            "candidateCount": 0,
            "sceneGlobalSceneIds": ["map01_lv001", "map02_lv002"],
            "sceneGlobalSemanticRoles": ["levelExitEvents", "levelInitEvents"],
            "sceneGlobalContextStatus": "exact",
            "contexts": [{
                "kind": "sceneGlobalAudioEvent",
                "sceneId": "map01_lv001",
                "semanticRole": "levelInitEvents",
            }],
            "media": [],
            "evidence": [],
        }
        summary = event_summary.event_summary_row(row, "event_details/00.json")
        self.assertEqual(summary["sceneGlobalSceneIds"], ["map01_lv001", "map02_lv002"])
        self.assertEqual(summary["sceneGlobalSemanticRoles"], ["levelExitEvents", "levelInitEvents"])
        self.assertEqual(summary["sceneGlobalContextStatus"], "exact")
        self.assertIn("map02_lv002", summary["contextSearch"])
        self.assertFalse(summary["foundInWwise"])
        self.assertEqual(summary["category"], "ambience")

    def test_media_playback_location_statuses_keep_evidence_boundaries(self) -> None:
        media = [
            {"id": "dialog", "audioDialogPath": "dialog/path", "storyLineBindingCount": 2},
            {"id": "placed", "eventIds": ["au_placed"]},
            {"id": "event_only", "eventIds": ["au_contextless"]},
            {"id": "literal_only", "eventIds": ["au_literal"]},
            {"id": "unknown"},
        ]
        events = [
            {"id": "au_placed", "contexts": [{"kind": "table"}]},
            {"id": "au_contextless", "contexts": []},
            {"id": "au_literal", "contexts": [{
                "kind": "binaryManagedLiteral",
                "playbackPlacementStatus": "identityOnlyManagedStringLiteral",
            }]},
        ]

        counts = purpose.annotate_media_playback_locations(media, events)

        self.assertEqual(
            [row["playbackLocationStatus"] for row in media],
            ["directDialogMedia", "authoredEventContext", "eventRelationOnly", "eventRelationOnly", "unknown"],
        )
        self.assertEqual(counts, {
            "directDialogMedia": 1,
            "authoredEventContext": 1,
            "eventRelationOnly": 2,
            "unknown": 1,
        })
        self.assertEqual(
            [row["purposeInvestigationPriority"] for row in media],
            ["resolvedTerminal", "resolved", "secondary", "secondary", "highest"],
        )
        self.assertEqual(media[0]["purposeKnowledgeStatus"], "exactStoryLineBinding")

    def test_unresolved_event_records_scanned_bank_fingerprint_and_exact_hash(self) -> None:
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": ["Au_Sfx_Fixture_Missing"],
            "events": [],
            "eventEvidence": [],
            "hircSummary": {
                "packageCount": 5,
                "packageFingerprint": "a" * 64,
            },
        }, {"au_sfx_fixture_missing": [{"kind": "table"}]})

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["audioLibraryResolutionStatus"], "eventHashAbsentFromScannedBankSet")
        self.assertEqual(row["authoredEventHash"], identifiers.audio_hash_generator_compute("Au_Sfx_Fixture_Missing"))
        self.assertEqual(row["scannedBankPackageCount"], 5)
        self.assertEqual(row["scannedBankPackageFingerprint"], "a" * 64)
        self.assertEqual(row["purposeKnowledgeStatus"], "authoredContextKnown")
        self.assertEqual(row["purposeInvestigationPriority"], "resolved")

    def test_anonymous_wwise_event_is_high_priority_unknown_use(self) -> None:
        event_hash = 0x12345678
        rows, _, _ = event_projection.build_event_rows(
            {
                "eventNames": [],
                "events": [],
                "eventEvidence": [],
                "wwiseEventInventory": [
                    {
                        "eventHash": event_hash,
                        "bankId": 7,
                        "bank": "default_banks.pck",
                        "actionEvidence": [],
                        "mediaIds": [],
                        "traversalStatus": "complete",
                    }
                ],
            },
            {},
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["eventIdentityStatus"], "wwiseObjectWithoutRecoveredTriggerName")
        self.assertEqual(rows[0]["playbackLocationStatus"], "unknown")
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "unknownUse")
        self.assertEqual(rows[0]["purposeInvestigationPriority"], "highest")

    def test_metadata_event_symbol_alias_recovers_hash_identity_without_trigger(self) -> None:
        event_name = "AU_INT_BELT_START"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, banks = event_projection.build_event_rows(
            {
                "eventNames": [],
                "events": [],
                "eventEvidence": [],
                "wwiseEventInventory": [{
                    "eventHash": event_hash,
                    "bankId": 7,
                    "bankVersion": 150,
                    "bank": "default_banks.pck",
                    "mediaIds": [],
                    "traversalStatus": "complete",
                }],
            },
            {},
            metadata_event_symbols=[{
                "eventHash": event_hash,
                "name": event_name,
                "metadataField": event_name,
                "metadataDeclaringType": "Beyond.Gameplay.Audio.AudioGameplayConstants+GameplayConveyor",
                "metadataFieldToken": "0x04001234",
                "evidence": "exactIl2CppMetadataFieldNameAudioHashAndCurrentWwiseEvent",
            }],
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], event_name.lower())
        self.assertEqual(row["name"], event_name)
        self.assertEqual(row["eventIdentityStatus"], "recoveredIl2CppMetadataEventSymbol")
        self.assertEqual(row["eventNameSourceKind"], "il2CppMetadataField")
        self.assertEqual(row["eventNameMetadataField"], event_name)
        self.assertEqual(row["eventNameMetadataDeclaringType"], "Beyond.Gameplay.Audio.AudioGameplayConstants+GameplayConveyor")
        self.assertEqual(row["category"], "sfx")
        self.assertEqual(row["categoryEvidence"], "exactIl2CppMetadataFieldNamePrefix")
        self.assertEqual(row["contextCount"], 0)
        self.assertEqual(banks[0]["namedEventCount"], 1)

    def test_native_custom_state_callsite_requires_authored_interactive_state_join(self) -> None:
        event_name = "au_int_rotateplatform_port_extense"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        audio_index = {
            "eventNames": [event_name],
            "events": [{"eventId": event_name, "eventHash": event_hash}],
            "eventEvidence": [],
            "wwiseEventInventory": [{"eventHash": event_hash}],
        }
        native = {
            "kind": "nativeCustomStateCallsite",
            "customStateName": "PortExtense",
            "callsiteVa": "0x1871fe1cd",
        }
        rows, _, _ = event_projection.build_event_rows(
            audio_index,
            {event_name: [native]},
        )
        self.assertEqual(rows[0]["contextCount"], 0)
        rows, _, _ = event_projection.build_event_rows(
            audio_index,
            {event_name: [
                {"kind": "interactiveComponentTrigger", "triggerCustomState": "PortExtense"},
                native,
            ]},
        )
        self.assertEqual(rows[0]["contextCount"], 2)
        self.assertEqual(rows[0]["contexts"][1]["kind"], "nativeCustomStateCallsite")

    def test_metadata_event_symbol_catalog_matches_only_current_hashes(self) -> None:
        from types import SimpleNamespace

        class FakeMetadata:
            version = 29
            types = [SimpleNamespace(index=1)]

            def type_full_name(self, _type_def):
                return "Fixture.AudioConstants"

            def fields_for(self, _type_def):
                return [
                    SimpleNamespace(index=3, name_index=1, token=0x04000003),
                    SimpleNamespace(index=4, name_index=2, token=0x04000004),
                ]

            def string(self, index):
                return {1: "AU_INT_FIXTURE", 2: "AU_INT_OTHER"}[index]

        fake_module = SimpleNamespace(Metadata=lambda _path: FakeMetadata())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global-metadata.dat"
            path.write_bytes(b"fixture")
            with patch.object(audio_semantics, "_metadata_module", return_value=fake_module):
                payload = audio_semantics.collect_metadata_event_symbol_aliases(
                    path,
                    {identifiers.audio_hash_generator_compute("AU_INT_FIXTURE")},
                )

        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["matchCount"], 1)
        self.assertEqual(payload["entries"][0]["name"], "AU_INT_FIXTURE")
        self.assertEqual(payload["entries"][0]["metadataDeclaringType"], "Fixture.AudioConstants")

    def test_action_control_ids_join_only_exact_selector_catalog_values(self) -> None:
        evidence_by_event = {
            "au_global_fixture": [{
                "actionEvidence": [
                    {
                        "operation": "setState",
                        "actionControlParserStatus": "typedExactV150",
                        "groupIdHex": "0x11111111",
                        "stateIdHex": "0x22222222",
                    },
                    {
                        "operation": "setSwitch",
                        "actionControlParserStatus": "typedExactV150",
                        "groupIdHex": "0x99999999",
                        "switchIdHex": "0x33333333",
                    },
                ],
            }],
        }
        catalog = [{
            "groupIdHex": "0x11111111",
            "groupType": "state",
            "semanticRole": "fixtureState",
            "semanticLabel": "Fixture state",
            "semanticEvidence": "exactNativeFixture",
            "runtimeObservationStatus": "staticOnly",
            "values": [{
                "valueIdHex": "0x22222222",
                "semanticName": "Ready",
                "semanticEvidence": "exactNativeFixture",
            }],
        }]

        summary = event_projection.annotate_wwise_action_control_evidence(
            evidence_by_event, catalog
        )
        rows = evidence_by_event["au_global_fixture"][0]["actionEvidence"]
        self.assertEqual(summary["actionCount"], 2)
        self.assertEqual(summary["typedExactActionCount"], 2)
        self.assertEqual(summary["groupSemanticMatchCount"], 1)
        self.assertEqual(summary["valueSemanticMatchCount"], 1)
        self.assertEqual(rows[0]["controlGroupSemantic"]["semanticLabel"], "Fixture state")
        self.assertEqual(rows[0]["controlValueSemantic"]["semanticName"], "Ready")
        self.assertEqual(rows[1]["controlGroupSemanticStatus"], "unresolvedGroupId")

    def test_music_state_catalog_joins_exact_action_enum_members(self) -> None:
        evidence_by_event = {
            "au_music_fixture": [{
                "actionEvidence": [{
                    "operation": "setState",
                    "actionControlParserStatus": "typedExactV150",
                    "groupIdHex": "0xe414d158",
                    "stateIdHex": "0x468283e1",
                }],
            }],
        }

        catalog = audio_semantics.wwise_selector_group_catalog()
        summary = event_projection.annotate_wwise_action_control_evidence(
            evidence_by_event, catalog
        )
        row = evidence_by_event["au_music_fixture"][0]["actionEvidence"][0]

        self.assertGreaterEqual(summary["groupSemanticMatchCount"], 1)
        self.assertGreaterEqual(summary["valueSemanticMatchCount"], 1)
        self.assertEqual(
            row["controlGroupSemantic"]["semanticLabel"],
            "Music state / music_state",
        )
        self.assertEqual(row["controlValueSemantic"]["semanticName"], "CUTSCENE")
        self.assertEqual(
            row["controlValueSemantic"]["semanticEvidence"],
            "exactCurrentMetadataEnumMemberFNV1Utf16Hash",
        )

    def test_selector_package_compaction_keeps_native_value_semantics(self) -> None:
        rows = [{
            "objectType": 6,
            "edgeKind": "switchCandidate",
            "childCount": 2,
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "state",
                "groupId": 0xF6699CF4,
                "defaultValueId": 0x2CA33BDB,
                "packages": [
                    {"valueId": 0x1A9FC91F, "childIds": [1]},
                    {"valueId": 0x2CA33BDB, "childIds": [2]},
                ],
                "associations": [],
            },
        }]

        compact = event_projection.compact_container_evidence(
            rows, audio_semantics.wwise_selector_group_catalog()
        )
        selector = compact[0]

        self.assertEqual(selector["selectorSemanticGroupMatchCount"], 1)
        self.assertEqual(selector["selectorSemanticValueMatchCount"], 1)
        self.assertEqual(selector["selectorSemanticValueCount"], 1)
        self.assertEqual(
            selector["selectorSemanticValues"][0]["semanticName"],
            "XInput",
        )

    def test_game_parameter_action_joins_same_event_initial_rtpc_id(self) -> None:
        evidence_by_event = {
            "au_rtpc_fixture": [{
                "postProcessSummary": {
                    "rtpcIds": [{
                        "rtpcId": 0x379123CC,
                        "rtpcIdHex": "0x379123cc",
                        "curveCount": 2,
                    }],
                },
                "actionEvidence": [{
                    "operation": "setGameParameter",
                    "actionControlParserStatus": "typedExactV150",
                    "idExt": 0x379123CC,
                    "idExtHex": "0x379123cc",
                    "valueRange": {"base": 100.0},
                }],
            }],
        }

        summary = event_projection.annotate_wwise_action_control_evidence(
            evidence_by_event,
            [],
            {"0x379123cc": "au_rtpc_fixture"},
        )
        row = evidence_by_event["au_rtpc_fixture"][0]["actionEvidence"][0]

        self.assertEqual(summary["sharedRtpcParameterIdMatchCount"], 1)
        self.assertEqual(summary["sharedRtpcParameterIdCount"], 1)
        self.assertEqual(row["initialRtpcSemantic"]["rtpcIdHex"], "0x379123cc")
        self.assertEqual(row["initialRtpcSemantic"]["curveCount"], 2)
        self.assertEqual(
            row["initialRtpcSemantic"]["semanticNameStatus"],
            "exactManagedStringLiteralFNV1Utf16Hash",
        )
        self.assertEqual(
            row["initialRtpcSemantic"]["parameterName"],
            "au_rtpc_fixture",
        )
        self.assertEqual(summary["namedInitialRtpcMatchCount"], 1)

    def test_event_projection_names_initial_rtpc_from_exact_metadata_hash(self) -> None:
        rows, _, _ = event_projection.build_event_rows(
            {
                "events": [],
                "eventEvidence": [{
                    "eventId": "au_rtpc_fixture",
                    "eventHash": 0x12345678,
                    "bankId": 1,
                    "bank": "fixture.bnk",
                    "traversalStatus": "complete",
                    "postProcessSummary": {
                        "rtpcIds": [{
                            "rtpcId": 0x80560CC1,
                            "rtpcIdHex": "0x80560cc1",
                            "curveCount": 2,
                        }],
                    },
                }],
            },
            {},
            rtpc_names_by_hex={"0x80560cc1": "au_rtpc_fixture_speed"},
        )

        rtpc_row = rows[0]["evidence"][0]["postProcessSummary"]["rtpcIds"][0]
        self.assertEqual(rtpc_row["parameterName"], "au_rtpc_fixture_speed")
        self.assertEqual(
            rtpc_row["semanticEvidence"],
            "exactInitialRtpcIdAndManagedStringLiteral",
        )

    def test_named_initial_rtpc_catalog_preserves_trigger_and_postprocess_semantics(self) -> None:
        catalog = event_projection.build_initial_rtpc_parameter_catalog([{
            "id": "au_seesaw_start",
            "contexts": [{
                "kind": "binaryManagedLiteralCallsite",
                "triggerRole": "seesawStart",
            }],
            "evidence": [{
                "postProcessSummary": {
                    "rtpcIds": [{
                        "rtpcId": 0x2B99882E,
                        "rtpcIdHex": "0x2b99882e",
                        "curveCount": 1,
                        "parameterName": "au_rtpc_angular_velocity",
                        "semanticNameStatus": "exactManagedStringLiteralFNV1Utf16Hash",
                        "semanticEvidence": "exactInitialRtpcIdAndManagedStringLiteral",
                    }],
                    "stateRtpcNodes": [{
                        "rtpcCurves": [{
                            "rtpcId": 0x2B99882E,
                            "rtpcIdHex": "0x2b99882e",
                            "parameterLabel": "BusVolume",
                            "points": [
                                {"interpolationLabel": "Linear"},
                                {"interpolationLabel": "Linear"},
                            ],
                        }],
                    }],
                },
            }],
        }])

        self.assertEqual(len(catalog), 1)
        row = catalog[0]
        self.assertEqual(row["parameterName"], "au_rtpc_angular_velocity")
        self.assertEqual(row["eventIds"], ["au_seesaw_start"])
        self.assertEqual(row["triggerRoles"], ["seesawStart"])
        self.assertEqual(row["controlledProperties"], {"BusVolume": 1})
        self.assertEqual(row["pointCount"], 2)
        self.assertEqual(row["interpolationLabels"], {"Linear": 2})

    def test_shared_wwise_play_target_recovers_output_category_not_trigger(self) -> None:
        bank = "default_banks.pck"
        known = {
            "id": "au_ui_known",
            "category": "ui",
            "purposeKnowledgeStatus": "authoredContextKnown",
            "purposeInvestigationPriority": "resolved",
            "evidence": [{
                "bank": bank,
                "actionEvidence": [
                    {"actionId": 10, "operation": "play", "targetId": 100},
                    {"actionId": 11, "operation": "play", "targetId": 200},
                ],
            }],
        }
        anonymous = {
            "id": "hashed-event:0x12345678",
            "category": "unknown",
            "categoryEvidence": "unclassified",
            "purposeKnowledgeStatus": "unknownUse",
            "purposeInvestigationPriority": "highest",
            "evidence": [{
                "bank": bank,
                "actionEvidence": [
                    {"actionId": 20, "operation": "play", "targetId": 200},
                    {"actionId": 21, "operation": "play", "targetId": 100},
                ],
            }],
        }

        count = purpose.annotate_shared_wwise_play_targets([known, anonymous])

        self.assertEqual(count, 1)
        self.assertEqual(anonymous["category"], "ui")
        self.assertEqual(anonymous["categoryEvidence"], "exactSharedWwisePlayTargetSet")
        self.assertEqual(anonymous["audioLibraryEquivalentEventIds"], ["au_ui_known"])
        self.assertEqual(anonymous["purposeKnowledgeStatus"], "unknownUse")
        self.assertEqual(anonymous["purposeInvestigationPriority"], "highest")

    def test_partial_shared_wwise_play_target_does_not_equate_output(self) -> None:
        known = {
            "id": "au_sfx_known",
            "category": "sfx",
            "purposeKnowledgeStatus": "authoredContextKnown",
            "purposeInvestigationPriority": "resolved",
            "evidence": [{
                "bank": "default_banks.pck",
                "actionEvidence": [
                    {"operation": "play", "targetId": 100},
                    {"operation": "play", "targetId": 200},
                ],
            }],
        }
        anonymous = {
            "id": "hashed-event:0x87654321",
            "category": "unknown",
            "purposeKnowledgeStatus": "unknownUse",
            "purposeInvestigationPriority": "highest",
            "evidence": [{
                "bank": "default_banks.pck",
                "actionEvidence": [{"operation": "play", "targetId": 100}],
            }],
        }

        self.assertEqual(
            purpose.annotate_shared_wwise_play_targets([known, anonymous]),
            0,
        )
        self.assertNotIn("audioLibraryPlaybackTargetStatus", anonymous)

    def test_complete_shared_wwise_media_set_recovers_uniform_category_only(self) -> None:
        known = {
            "id": "au_ui_known",
            "category": "ui",
            "purposeKnowledgeStatus": "authoredContextKnown",
            "purposeInvestigationPriority": "resolved",
            "media": [
                {"mediaId": 100, "bank": "vfs/audio/default_banks.pck"},
                {"mediaId": 200, "bank": "vfs/audio/default_banks.pck"},
            ],
        }
        unknown = {
            "id": "hashed-event:0x12345678",
            "category": "unknown",
            "purposeKnowledgeStatus": "unknownUse",
            "purposeInvestigationPriority": "highest",
            "media": [
                {"mediaId": 200, "bank": "vfs/audio/default_banks.pck"},
                {"mediaId": 100, "bank": "vfs/audio/default_banks.pck"},
            ],
        }

        count = purpose.annotate_shared_wwise_media_leaves([known, unknown])

        self.assertEqual(count, 1)
        self.assertEqual(
            unknown["audioLibraryMediaLeafStatus"],
            "exactCompleteWwiseMediaIdSetWithAuthoredEvent",
        )
        self.assertEqual(unknown["audioLibraryMediaEquivalentEventIds"], ["au_ui_known"])
        self.assertEqual(unknown["audioLibrarySharedMediaIds"], [100, 200])
        self.assertEqual(unknown["category"], "ui")
        self.assertEqual(
            unknown["categoryEvidence"],
            "exactCompleteWwiseMediaLeafSetCategory",
        )
        self.assertEqual(unknown["purposeKnowledgeStatus"], "unknownUse")
        self.assertEqual(unknown["purposeInvestigationPriority"], "highest")

    def test_partial_shared_wwise_media_set_does_not_equate_leaf_output(self) -> None:
        known = {
            "id": "au_sfx_known",
            "purposeKnowledgeStatus": "authoredContextKnown",
            "media": [
                {"mediaId": 100, "bank": "default_banks.pck"},
                {"mediaId": 200, "bank": "default_banks.pck"},
            ],
        }
        unknown = {
            "id": "hashed-event:0x87654321",
            "purposeKnowledgeStatus": "unknownUse",
            "purposeInvestigationPriority": "highest",
            "media": [{"mediaId": 100, "bank": "default_banks.pck"}],
        }

        self.assertEqual(
            purpose.annotate_shared_wwise_media_leaves([known, unknown]),
            0,
        )
        self.assertNotIn("audioLibraryMediaLeafStatus", unknown)

    def test_complete_shared_wwise_media_set_does_not_choose_mixed_category(self) -> None:
        known_ui = {
            "id": "au_ui_known",
            "category": "ui",
            "purposeKnowledgeStatus": "authoredContextKnown",
            "purposeInvestigationPriority": "resolved",
            "media": [{"mediaId": 100, "bank": "default_banks.pck"}],
        }
        known_sfx = {
            "id": "au_sfx_known",
            "category": "sfx",
            "purposeKnowledgeStatus": "authoredContextKnown",
            "purposeInvestigationPriority": "resolved",
            "media": [{"mediaId": 100, "bank": "default_banks.pck"}],
        }
        unknown = {
            "id": "hashed-event:0x12345679",
            "category": "unknown",
            "purposeKnowledgeStatus": "unknownUse",
            "purposeInvestigationPriority": "highest",
            "media": [{"mediaId": 100, "bank": "default_banks.pck"}],
        }

        self.assertEqual(
            purpose.annotate_shared_wwise_media_leaves(
                [known_ui, known_sfx, unknown]
            ),
            1,
        )
        self.assertEqual(unknown["category"], "unknown")
        self.assertNotIn("categoryEvidence", unknown)

    def test_managed_literal_without_wwise_object_or_consumer_is_not_an_event(self) -> None:
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": ["au_music_", "au_real_missing"],
            "binaryManagedEventNames": ["au_music_"],
            "events": [],
            "eventEvidence": [],
            "wwiseEventInventory": [],
        }, {
            "au_real_missing": [{"kind": "table"}],
        })

        self.assertEqual([row["id"] for row in rows], ["au_real_missing"])

    def test_authored_event_name_joins_matching_raw_wwise_inventory(self) -> None:
        event_name = "au_sfx_levelscript_fixture"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, banks = event_projection.build_event_rows({
            # LevelScript/Timeline names are collected after the base audio
            # index and may exist only as semantic context keys.
            "eventNames": [],
            "events": [],
            "eventEvidence": [],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": event_hash,
                "bankVersion": 150,
                "bank": "default_banks.pck",
                "actionIds": [9],
                "actionEvidence": [{"rootActionId": 9, "operation": "play"}],
                "rootPlayActionCount": 1,
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }, {event_name: [{"kind": "levelScriptAudioAction"}]})

        self.assertEqual([row["id"] for row in rows], [event_name])
        self.assertTrue(rows[0]["foundInWwise"])
        self.assertEqual(
            rows[0]["audioLibraryResolutionStatus"],
            "resolvedWwiseEventObject",
        )
        self.assertEqual(rows[0]["eventIdentityStatus"], "recoveredAuthoredName")
        self.assertEqual(rows[0]["evidence"][0]["bank"], "default_banks.pck")
        self.assertEqual(banks[0]["namedEventCount"], 1)

    def test_context_name_replaces_preexisting_hash_only_event_evidence(self) -> None:
        event_name = "au_music_levelscript_fixture"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        hashed_key = f"hashed-event:0x{event_hash:08x}"
        evidence = {
            "eventId": hashed_key,
            "eventHash": event_hash,
            "bankId": 7,
            "bankVersion": 150,
            "bank": "default_banks.pck",
            "actionIds": [9],
            "actionEvidence": [{"rootActionId": 9, "operation": "play"}],
            "rootPlayActionCount": 1,
            "mediaIds": [],
            "traversalStatus": "complete",
        }
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": [],
            "events": [],
            "eventEvidence": [evidence],
            "wwiseEventInventory": [evidence],
        }, {
            event_name: [{"kind": "levelScriptAudioAction"}],
            hashed_key: [{"kind": "tableEventHash"}],
        })

        self.assertEqual([row["id"] for row in rows], [event_name])
        self.assertTrue(rows[0]["foundInWwise"])
        self.assertEqual(
            sorted(context["kind"] for context in rows[0]["contexts"]),
            ["levelScriptAudioAction", "tableEventHash"],
        )
        self.assertEqual(len(rows[0]["evidence"]), 1)

    def test_unnamed_wwise_event_inventory_recovers_media_without_inventing_trigger(self) -> None:
        inventory_row = {
            "eventHash": 0x1EFEFA3C,
            "eventIdentityStatus": "wwiseObjectWithoutRecoveredTriggerName",
            "bankId": 7,
            "bankVersion": 150,
            "bank": "vfs/StreamingAssets/Audio/default_banks.pck",
            "actionIds": [9],
            "actionEvidence": [{"rootActionId": 9, "operation": "play"}],
            "rootPlayActionCount": 1,
            "mediaIds": [212418017],
            "mediaRelationTypes": ["layerChild"],
            "traversalStatus": "complete",
            "selectionObjectTypes": [9],
        }
        rows, _, banks = event_projection.build_event_rows({
            "eventNames": [],
            "events": [],
            "eventEvidence": [],
            "entries": [{
                "id": "212418017",
                "rel": "wwise/unknown/212418017.flac",
                "src": "/export_full/structured/Audio/shared/wwise/unknown/212418017.flac",
                "format": "flac",
                "bytes": 123,
                "storageRoot": "shared",
            }],
            "wwiseEventInventory": [inventory_row, {**inventory_row, "bankId": 8}],
        }, {})

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], "hashed-event:0x1efefa3c")
        self.assertTrue(row["foundInWwise"])
        self.assertEqual(
            row["eventIdentityStatus"],
            "wwiseObjectWithoutRecoveredTriggerName",
        )
        self.assertEqual(row["possibleMediaCount"], 1)
        self.assertEqual(row["media"][0]["mediaId"], 212418017)
        self.assertEqual(row["mediaRelationTypes"], ["layerChild"])
        self.assertEqual(len(row["evidence"]), 2)
        self.assertEqual(len(banks), 2)
        self.assertEqual([bank["namedEventCount"] for bank in banks], [0, 0])

    def test_hotfix_same_media_id_replacement_inherits_exact_event_relation(self) -> None:
        event_name = "au_music_main"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        base_src = "/export_full/structured/Audio/shared/wwise/music/291650974.flac"
        hotfix_src = "/export_full/structured/Audio/shared/wwise/unknown/291650974.flac"
        audio_index = {
            "eventNames": [event_name],
            "events": [{
                "id": event_name,
                "eventId": event_name,
                "eventHash": event_hash,
                "mediaId": 291650974,
                "rel": "wwise/music/291650974.flac",
                "src": base_src,
                "bytes": 100,
                "storageRoot": "shared",
                "sourceBlock": "audit",
                "wwiseMediaEvidence": [{"rootActionIds": [7], "relationTypes": ["musicTrackSource"]}],
            }],
            "eventEvidence": [{
                "eventId": event_name,
                "eventHash": event_hash,
                "bankId": 1,
                "bank": "audit_banks.pck",
                "mediaIds": [291650974],
                "rootPlayActionCount": 1,
            }],
            "entries": [{
                "id": "291650974",
                "rel": "wwise/music/291650974.flac",
                "src": base_src,
                "bytes": 100,
                "storageRoot": "shared",
                "sourceBlock": "audit",
            }, {
                "id": "291650974",
                "rel": "wwise/unknown/291650974.flac",
                "src": hotfix_src,
                "bytes": 120,
                "storageRoot": "shared",
                "sourceBlock": "hotfix-audio",
                "sourceBlockLabel": "HotfixAudio",
            }],
        }

        events, media_to_events, _ = event_projection.build_event_rows(
            audio_index, {event_name: [{"kind": "typedTableEvent"}]}
        )
        media = audio_semantics.build_media_rows(audio_index, media_to_events)
        counts = purpose.annotate_media_playback_locations(media, events)

        self.assertEqual(len(events[0]["media"]), 2)
        replacement = next(row for row in events[0]["media"] if row.get("hotfixMediaReplacement"))
        self.assertEqual(replacement["src"], hotfix_src)
        self.assertEqual(
            replacement["mediaResolutionEvidence"],
            "hotfixPackageMediaIdReplacesBaseMediaId",
        )
        self.assertEqual(media_to_events[hotfix_src], [event_name])
        self.assertEqual(counts["authoredEventContext"], 2)
        self.assertNotIn("unknown", counts)

    def test_definition_only_sound_object_stays_unknown_but_resolves_library_object(self) -> None:
        audio_index = {
            "entries": [{
                "id": "30151934",
                "rel": "wwise/unknown/30151934.flac",
                "src": "/export_full/structured/Audio/shared/wwise/unknown/30151934.flac",
                "storageRoot": "shared",
            }],
            "hircSummary": {"definitionOnlyDecodedSoundObjects": [{
                "mediaId": 30151934,
                "bank": "default_banks.pck",
                "bankId": 7,
                "soundObjectId": 10,
                "parentObjectId": 20,
                "parentObjectType": 5,
                "evidence": "exactTypedWwiseSoundCodecMediaObject",
            }]},
            "wwiseEventInventory": [{
                "eventId": "au_int_rolling_stone_big_rolling",
                "bank": "default_banks.pck",
                "bankId": 7,
            }],
        }

        media = audio_semantics.build_media_rows(audio_index, {})
        counts = purpose.annotate_media_playback_locations(media, [])

        self.assertEqual(counts["unknown"], 1)
        self.assertEqual(
            media[0]["audioLibraryObjectStatus"],
            "wwiseSoundDefinitionWithoutEventPath",
        )
        self.assertEqual(media[0]["wwiseDefinitionEvidence"][0]["soundObjectId"], 10)
        self.assertEqual(
            media[0]["audioLibraryBankEventIds"],
            ["au_int_rolling_stone_big_rolling"],
        )
        self.assertEqual(media[0]["purposeHintStatus"], "authoredEventBankColocationOnly")

    def test_media_rows_keep_media_purpose_separate_from_related_event_types(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/1.flac"
        audio_index = {"entries": [{
            "id": "1",
            "rel": "wwise/sfx/1.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_music_fixture", "au_sfx_fixture"]},
            {"au_music_fixture": "music", "au_sfx_fixture": "sfx"},
        )

        self.assertEqual(media[0]["audioCategory"], "sfx")
        self.assertEqual(media[0]["relatedEventCategories"], ["music", "sfx"])

    def test_media_rows_derive_unique_semantic_category_for_unknown_physical_path(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/unknown/2.flac"
        audio_index = {"entries": [{
            "id": "2",
            "rel": "wwise/unknown/2.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "unknown",
        }]}

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_ui_fixture"]},
            {"au_ui_fixture": "ui"},
        )

        self.assertEqual(media[0]["audioCategory"], "unknown")
        self.assertEqual(media[0]["semanticCategory"], "ui")
        self.assertEqual(
            media[0]["semanticCategoryEvidence"],
            "exactUniqueRelatedWwiseEventCategory",
        )

    def test_media_rows_do_not_choose_semantic_category_for_mixed_event_types(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/unknown/3.flac"
        audio_index = {"entries": [{
            "id": "3",
            "rel": "wwise/unknown/3.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "unknown",
        }]}

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_ui_fixture", "au_sfx_fixture"]},
            {"au_ui_fixture": "ui", "au_sfx_fixture": "sfx"},
        )

        self.assertNotIn("semanticCategory", media[0])

    def test_media_rows_project_exact_wwise_selection_path(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/6.flac"
        audio_index = {"entries": [{
            "id": "6",
            "rel": "wwise/sfx/6.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}
        events = [{
            "id": "hashed-event:0x12345678",
            "runtimeSelection": "runtimeBranchUnresolved",
            "media": [{
                "mediaId": 6,
                "src": src,
                "wwiseMediaEvidence": [{
                    "rootActionIds": [77],
                    "relationTypes": ["layerChild", "randomAlternative"],
                    "selectionPaths": [["layerChild", "randomAlternative"]],
                }],
            }],
            "evidence": [],
        }]

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["hashed-event:0x12345678"]},
            {"hashed-event:0x12345678": "sfx"},
            event_rows=events,
        )

        self.assertEqual(
            media[0]["wwiseMediaRelationTypes"],
            ["layerChild", "randomAlternative"],
        )
        self.assertEqual(
            media[0]["wwiseMediaSelectionPaths"],
            [["layerChild", "randomAlternative"]],
        )
        self.assertEqual(media[0]["wwiseMediaRootActionIds"], [77])
        self.assertEqual(
            media[0]["wwiseMediaGraphEvidence"],
            "exactSerializedWwiseEventMediaJoin",
        )

    def test_media_rows_project_event_context_to_possible_media_boundary(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/7.flac"
        audio_index = {"entries": [{
            "id": "7",
            "rel": "wwise/sfx/7.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}
        events = [{
            "id": "au_sfx_context_fixture",
            "runtimeSelection": "runtimeBranchUnresolved",
            "media": [{"mediaId": 7, "src": src}],
            "contexts": [{
                "kind": "characterSkill",
                "triggerRole": "skillCast",
                "ownerId": "chr_fixture",
                "skillId": "skill_fixture",
                "path": "SkillData.Audio",
            }],
            "evidence": [],
        }]

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_sfx_context_fixture"]},
            {"au_sfx_context_fixture": "sfx"},
            event_rows=events,
        )

        self.assertEqual(media[0]["eventContextCount"], 1)
        self.assertEqual(media[0]["eventContextKinds"], ["characterSkill"])
        self.assertEqual(media[0]["eventContextRoles"], ["skillCast"])
        self.assertEqual(media[0]["eventContextOwnerValues"], ["ownerId=chr_fixture", "skillId=skill_fixture"])
        self.assertEqual(media[0]["eventContextSituationValues"], ["path=SkillData.Audio"])
        self.assertEqual(
            media[0]["eventContextSummaryEvidence"],
            "exactSerializedEventContextToPossibleMediaJoin",
        )

    def test_media_rows_project_serialized_event_output_bus_routes(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/2.flac"
        audio_index = {"entries": [{
            "id": "2",
            "rel": "wwise/sfx/2.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}
        events = [{
            "id": "au_sfx_route_fixture",
            "runtimeSelection": "runtimeBranchUnresolved",
            "media": [{"mediaId": 2, "src": src}],
            "evidence": [{
                "bankId": 7,
                "postProcessSummary": {"outputBuses": [{
                    "busIdHex": "0x01020304",
                    "busPathIdHexes": ["0x01020304", "0x05060708"],
                    "effectBusIdHexes": ["0x05060708"],
                    "unresolvedBusProcessingIdHexes": ["0x01020304"],
                }]},
            }],
        }]

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_sfx_route_fixture"]},
            {"au_sfx_route_fixture": "sfx"},
            event_rows=events,
        )

        self.assertEqual(media[0]["postProcessRouteCount"], 1)
        self.assertEqual(
            media[0]["postProcessBusPaths"],
            [["0x01020304", "0x05060708"]],
        )
        self.assertEqual(media[0]["postProcessEffectBusIds"], ["0x05060708"])
        self.assertEqual(
            media[0]["postProcessUnresolvedBusProcessingIds"], ["0x01020304"]
        )
        self.assertEqual(
            media[0]["postProcessRouteEvidence"],
            "exactSerializedEventOutputBusJoin",
        )
        self.assertEqual(
            media[0]["postProcessRouteStatuses"],
            ["exactSerializedOutputBusPath"],
        )

    def test_media_rows_distinguish_no_explicit_output_bus_from_parse_failure(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/3.flac"
        audio_index = {"entries": [{
            "id": "3",
            "rel": "wwise/sfx/3.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}
        events = [{
            "id": "au_sfx_default_bus_fixture",
            "runtimeSelection": "singlePossibleMedia",
            "media": [{"mediaId": 3, "src": src}],
            "evidence": [{
                "bankId": 8,
                "postProcessSummary": {
                    "parserStatus": "typedExactV150NodeBaseProcessingPrefix",
                    "parsedNodeCount": 2,
                    "outputBusNodeCount": 0,
                    "outputBuses": [],
                },
            }],
        }]
        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_sfx_default_bus_fixture"]},
            {"au_sfx_default_bus_fixture": "sfx"},
            event_rows=events,
        )

        self.assertEqual(media[0]["postProcessRouteCount"], 0)
        self.assertEqual(
            media[0]["postProcessRouteStatuses"],
            ["noExplicitOutputBusSerialized"],
        )
        self.assertEqual(media[0]["postProcessEvidenceEventCount"], 1)
        self.assertEqual(media[0]["postProcessParsedNodeCount"], 2)
        self.assertEqual(media[0]["postProcessOutputBusNodeCount"], 0)

    def test_media_rows_project_direct_node_effects_separately_from_bus_effects(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/4.flac"
        audio_index = {"entries": [{
            "id": "4",
            "rel": "wwise/sfx/4.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}
        events = [{
            "id": "au_sfx_direct_effect_fixture",
            "runtimeSelection": "singlePossibleMedia",
            "media": [{"mediaId": 4, "src": src}],
            "evidence": [{
                "bankId": 9,
                "postProcessSummary": {
                    "parserStatus": "typedExactV150NodeBaseProcessingPrefix",
                    "parsedNodeCount": 1,
                    "outputBusNodeCount": 0,
                    "outputBuses": [],
                    "effectNodes": [{
                        "objectId": 44,
                        "effects": [{
                            "effectId": 0x12345678,
                            "effectIdHex": "0x12345678",
                            "slotIndex": 0,
                            "pluginName": "Parametric EQ",
                            "pluginClassIdHex": "0x008b0003",
                            "parameterSummary": "B1 High Pass 70 Hz",
                            "resolutionStatus": "exactUniquePluginDefinition",
                        }],
                    }],
                    "auxSendNodes": [{
                        "objectId": 44,
                        "objectType": 2,
                        "objectTypeLabel": "sound",
                        "parentId": 45,
                        "auxFlagsRaw": 8,
                        "overrideUserDefinedAuxSends": False,
                        "useGameDefinedAuxSends": False,
                        "userDefinedAuxSends": [{
                            "slotIndex": 0,
                            "busIdHex": "0x00000040",
                            "serializationStatus": "exactAuthoredUserDefinedAuxBusId",
                        }],
                    }],
                    "auxiliaryBuses": [{
                        "sendKind": "userDefined",
                        "busIdHex": "0x00000040",
                        "resolutionStatus": "exactGlobalAuxiliaryBusDefinition",
                        "busPathIdHexes": ["0x00000040", "0x00000050"],
                        "busPathResolutionStatus": "exactGlobalBusParentPath",
                        "effectBusIdHexes": ["0x00000040"],
                    }],
                    "propertyNodes": [{
                        "objectId": 44,
                        "objectType": 2,
                        "objectTypeLabel": "sound",
                        "properties": [{
                            "propertyIdHex": "0x00",
                            "propertyLabel": "Volume",
                            "rawU32": 3212836864,
                            "rawHex": "0xbf800000",
                            "floatValue": -1.0,
                            "valueEncoding": "float",
                        }],
                        "rangedProperties": [{
                            "propertyIdHex": "0x01",
                            "propertyLabel": "Pitch",
                            "minimumRawU32": 3259498496,
                            "minimumRawHex": "0xc2480000",
                            "minimumFloat": -50.0,
                            "maximumRawU32": 1112014848,
                            "maximumRawHex": "0x42480000",
                            "maximumFloat": 50.0,
                            "valueEncoding": "floatOrTypedUnionRawU32",
                        }],
                    }],
                },
            }],
        }]

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_sfx_direct_effect_fixture"]},
            {"au_sfx_direct_effect_fixture": "sfx"},
            event_rows=events,
        )

        self.assertEqual(media[0]["postProcessDirectEffectCount"], 1)
        self.assertEqual(media[0]["postProcessDirectEffectOccurrences"], 1)
        self.assertEqual(
            media[0]["postProcessDirectEffects"][0]["pluginName"],
            "Parametric EQ",
        )
        self.assertEqual(
            media[0]["postProcessDirectEffectEvidence"],
            "exactSerializedEventNodeEffectJoin",
        )

    def test_media_rows_project_compact_serialized_direct_and_bus_effect_chain(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/40.flac"
        audio_index = {
            "entries": [{
                "id": "40",
                "rel": "wwise/sfx/40.flac",
                "src": src,
                "storageRoot": "shared",
                "audioCategory": "sfx",
            }],
            "hircSummary": {"postProcessSummary": {"busDefinitions": [{
                "busIdHex": "0x00000010",
                "serializedStateAndRtpc": {
                    "parserStatus": "typedExactV150BusInitialRtpcAndState",
                    "rtpcCurveCount": 1,
                    "rtpcPointCount": 2,
                    "rtpcCurves": [{
                        "rtpcIdHex": "0x00000031",
                        "parameterId": 0,
                        "parameterLabel": "Volume",
                        "rtpcTypeLabel": "gameParameter",
                        "accumLabel": "additive",
                        "scalingLabel": "decibel",
                        "pointCount": 2,
                        "points": [
                            {"pointIndex": 0, "from": 0.0, "to": -1.0, "interpolationLabel": "Linear"},
                            {"pointIndex": 1, "from": 1.0, "to": 0.0, "interpolationLabel": "Linear"},
                        ],
                    }],
                    "stateGroupCount": 1,
                    "stateCount": 1,
                    "stateValueCount": 1,
                    "stateGroups": [{
                        "groupIdHex": "0x00000032",
                        "syncTypeLabel": "immediate",
                        "states": [{
                            "stateIdHex": "0x00000033",
                            "values": [{"parameterId": 4, "parameterLabel": "HPF", "value": -3.0}],
                        }],
                    }],
                },
                "serializedDuckCount": 1,
                "serializedMaxDuckVolumeDb": -96.0,
                "serializedDucks": [{
                    "duckIndex": 0,
                    "busIdHex": "0x00000040",
                    "duckVolumeDb": -6.0,
                    "fadeOutMs": 200,
                    "fadeInMs": 500,
                    "fadeCurve": 4,
                    "targetPropertyIdHex": "0x00",
                    "targetPropertyLabel": "Volume",
                }],
                "effects": [{
                    "slotIndex": 0,
                    "effectIdHex": "0x00000011",
                    "pluginName": "Compressor",
                    "pluginClassIdHex": "0x00820003",
                    "parameterSummary": "threshold -12 dB",
                    "effectBypass": False,
                    "effectShareSet": False,
                    "effectRendered": False,
                    "resolutionStatus": "exactUniquePluginDefinition",
                }],
            }, {
                "busIdHex": "0x00000020",
                "effects": [{
                    "slotIndex": 0,
                    "effectIdHex": "0x00000021",
                    "pluginName": "Parametric EQ",
                    "parameterSummary": "B1 +3 dB",
                    "resolutionStatus": "exactUniquePluginDefinition",
                }],
            }] }},
        }
        events = [{
            "id": "au_sfx_chain_fixture",
            "runtimeSelection": "singlePossibleMedia",
            "media": [{"mediaId": 40, "src": src}],
            "evidence": [{
                "bankId": 11,
                "postProcessSummary": {
                    "outputBuses": [{
                        "busIdHex": "0x00000010",
                        "busPathIdHexes": ["0x00000010", "0x00000020"],
                    }],
                    "effectNodes": [{
                        "objectId": 44,
                        "effects": [{
                            "effectId": 1,
                            "effectIdHex": "0x00000001",
                            "slotIndex": 0,
                            "pluginName": "Meter",
                            "parameterSummary": "RMS",
                            "resolutionStatus": "exactUniquePluginDefinition",
                        }],
                    }],
                    "auxiliaryBuses": [{
                        "sendKind": "userDefined",
                        "busIdHex": "0x00000040",
                        "resolutionStatus": "exactGlobalAuxiliaryBusDefinition",
                        "busPathIdHexes": ["0x00000040", "0x00000050"],
                        "busPathResolutionStatus": "exactGlobalBusParentPath",
                        "effectBusIdHexes": ["0x00000040"],
                    }],
                    "auxSendNodes": [{
                        "objectId": 44,
                        "objectType": 2,
                        "objectTypeLabel": "sound",
                        "parentId": 45,
                        "auxFlagsRaw": 8,
                        "overrideUserDefinedAuxSends": False,
                        "useGameDefinedAuxSends": False,
                        "userDefinedAuxSends": [{
                            "slotIndex": 0,
                            "busIdHex": "0x00000040",
                            "serializationStatus": "exactAuthoredUserDefinedAuxBusId",
                        }],
                    }],
                    "propertyNodes": [{
                        "objectId": 44,
                        "objectType": 2,
                        "objectTypeLabel": "sound",
                        "properties": [{
                            "propertyIdHex": "0x00",
                            "propertyLabel": "Volume",
                            "rawU32": 3212836864,
                            "rawHex": "0xbf800000",
                            "floatValue": -1.0,
                            "valueEncoding": "float",
                        }],
                        "rangedProperties": [{
                            "propertyIdHex": "0x01",
                            "propertyLabel": "Pitch",
                            "minimumRawU32": 3259498496,
                            "minimumRawHex": "0xc2480000",
                            "minimumFloat": -50.0,
                            "maximumRawU32": 1112014848,
                            "maximumRawHex": "0x42480000",
                            "maximumFloat": 50.0,
                            "valueEncoding": "floatOrTypedUnionRawU32",
                        }],
                    }],
                },
            }],
        }]

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_sfx_chain_fixture"]},
            {"au_sfx_chain_fixture": "sfx"},
            event_rows=events,
        )

        chain = media[0]["postProcessEffectChain"]
        self.assertEqual(media[0]["postProcessEffectChainCount"], 3)
        self.assertEqual([row["stage"] for row in chain], ["directNode", "bus", "bus"])
        self.assertEqual(chain[0]["objectId"], 44)
        self.assertEqual(chain[1]["busIdHex"], "0x00000010")
        self.assertEqual(chain[1]["pathDepth"], 0)
        self.assertEqual(chain[2]["busIdHex"], "0x00000020")
        self.assertEqual(chain[2]["pathDepth"], 1)
        self.assertEqual(media[0]["postProcessBusControlCount"], 1)
        self.assertEqual(media[0]["postProcessBusControls"][0]["busIdHex"], "0x00000010")
        self.assertEqual(
            media[0]["postProcessBusControls"][0]["rtpcIds"],
            ["0x00000031"],
        )
        self.assertEqual(
            media[0]["postProcessBusControls"][0]["rtpcParameterLabels"],
            ["Volume"],
        )
        self.assertNotIn("points", media[0]["postProcessBusControls"][0])
        self.assertEqual(
            media[0]["postProcessBusControls"][0]["stateControls"][0]["parameterLabel"],
            "HPF",
        )
        self.assertEqual(
            media[0]["postProcessBusControlEvidence"],
            "exactSerializedBusInitialRtpcAndStateJoin",
        )
        self.assertEqual(media[0]["postProcessBusDuckCount"], 1)
        self.assertEqual(
            media[0]["postProcessBusDucks"][0]["ducks"][0]["targetBusIdHex"],
            "0x00000040",
        )
        self.assertEqual(
            media[0]["postProcessBusDuckEvidence"],
            "exactSerializedBusDuckingJoin",
        )
        self.assertEqual(media[0]["postProcessAuxSendCount"], 1)
        self.assertEqual(
            media[0]["postProcessAuxSends"][0]["busIdHex"],
            "0x00000040",
        )
        self.assertEqual(
            media[0]["postProcessAuxSendEvidence"],
            "exactSerializedEventNodeUserDefinedAuxSendJoin",
        )
        self.assertEqual(
            media[0]["postProcessAuxSends"][0]["busRoutes"][0]["busPathIdHexes"],
            ["0x00000040", "0x00000050"],
        )
        self.assertEqual(media[0]["postProcessPropertyCount"], 1)
        self.assertEqual(media[0]["postProcessProperties"][0]["propertyLabel"], "Volume")
        self.assertEqual(media[0]["postProcessPropertyOccurrences"], 1)
        self.assertEqual(media[0]["postProcessRangeCount"], 1)
        self.assertEqual(media[0]["postProcessRanges"][0]["propertyLabel"], "Pitch")
        self.assertEqual(media[0]["postProcessRangeOccurrences"], 1)
        self.assertEqual(
            media[0]["postProcessPropertyEvidence"],
            "exactSerializedEventNodePropertyJoin",
        )
        self.assertEqual(
            media[0]["postProcessEffectChainEvidence"],
            "exactSerializedEventNodeAndBusEffectJoin",
        )

    def test_media_rows_project_serialized_state_and_rtpc_controls(self) -> None:
        src = "/export_full/structured/Audio/shared/wwise/sfx/5.flac"
        audio_index = {"entries": [{
            "id": "5",
            "rel": "wwise/sfx/5.flac",
            "src": src,
            "storageRoot": "shared",
            "audioCategory": "sfx",
        }]}
        events = [{
            "id": "au_sfx_control_fixture",
            "runtimeSelection": "runtimeBranchUnresolved",
            "media": [{"mediaId": 5, "src": src}],
            "evidence": [{
                "bankId": 10,
                "postProcessSummary": {
                    "stateRtpcNodes": [{
                        "objectId": 55,
                        "objectType": 7,
                        "objectTypeLabel": "Actor-Mixer",
                        "stateGroups": [{
                            "groupId": 0x01020304,
                            "groupIdHex": "0x01020304",
                            "syncTypeLabel": "gameObject",
                            "states": [{
                                "stateId": 0x05060708,
                                "stateIdHex": "0x05060708",
                                "values": [{
                                    "parameterId": 0x10,
                                    "parameterLabel": "BusVolume",
                                    "value": -3.5,
                                }],
                            }],
                        }],
                        "rtpcCurves": [{
                            "rtpcId": 0x11223344,
                            "rtpcIdHex": "0x11223344",
                            "parameterId": 0x0E,
                            "parameterLabel": "LPF",
                            "rtpcTypeLabel": "GameParameter",
                            "accumLabel": "Add",
                            "scalingLabel": "None",
                            "pointCount": 2,
                            "points": [
                                {"pointIndex": 0, "from": 0.0, "to": 1.0, "interpolationLabel": "Linear"},
                                {"pointIndex": 1, "from": 1.0, "to": 0.0, "interpolationLabel": "Linear"},
                            ],
                        }],
                    }],
                },
            }],
        }]

        events[0]["evidence"][0]["postProcessSummary"]["stateRtpcNodes"][0]["rtpcCurves"][0]["points"] = [
            {"pointIndex": index, "from": float(index), "to": float(index + 1), "interpolationLabel": "Linear"}
            for index in range(10)
        ]
        events[0]["evidence"][0]["postProcessSummary"]["stateRtpcNodes"][0]["rtpcCurves"][0]["pointCount"] = 10

        media = audio_semantics.build_media_rows(
            audio_index,
            {src: ["au_sfx_control_fixture"]},
            {"au_sfx_control_fixture": "sfx"},
            event_rows=events,
        )

        self.assertEqual(media[0]["postProcessRtpcControlCount"], 1)
        self.assertEqual(media[0]["postProcessRtpcControls"][0]["parameterLabel"], "LPF")
        self.assertEqual(media[0]["postProcessRtpcControls"][0]["points"][7]["to"], 8.0)
        self.assertEqual(len(media[0]["postProcessRtpcControls"][0]["points"]), 8)
        self.assertTrue(media[0]["postProcessRtpcControls"][0]["pointsTruncated"])
        self.assertEqual(media[0]["postProcessStateControlCount"], 1)
        self.assertEqual(media[0]["postProcessStateGroupIds"], ["0x01020304"])
        self.assertEqual(media[0]["postProcessStateControls"][0]["value"], -3.5)
        self.assertEqual(
            media[0]["postProcessControlEvidence"],
            "exactSerializedEventNodeStateRtpcJoin",
        )

    def test_media_trigger_context_summary_keeps_authored_selection_boundary(self) -> None:
        media = [{
            "id": "7",
            "src": "/audio/trigger.flac",
            "rel": "wwise/sfx/7.flac",
        }]
        catalog = {
            "contexts": [{
                "triggerId": "abilityVoiceTrigger:fixture",
                "semanticKind": "abilityVoiceTriggerAction",
                "triggerRole": "authoredAbilityVoiceResponseTrigger",
                "situation": {
                    "eventId": "au_voice_fixture",
                    "ownerId": "chr_fixture",
                    "triggerKey": "combat_attack",
                },
                "owner": {
                    "ownerId": "chr_fixture",
                    "configId": "skill_fixture",
                },
                "selection": {
                    "eventSelectionStatus": "uniqueEvent",
                    "runtimeSelectionStatus": "responsiveRuntimeSelectionUnobserved",
                },
                "runtimeActivationStatus": "abilityActionExecutionUnobserved",
                "mediaRefs": [{
                    "id": "7",
                    "src": "/audio/trigger.flac",
                    "rel": "wwise/sfx/7.flac",
                }],
            }],
        }

        counts = audio_semantics.annotate_media_trigger_contexts(media, catalog)

        self.assertEqual(
            counts,
            {"mediaWithTriggerContextSummary": 1, "triggerContextMediaRefs": 1},
        )
        self.assertEqual(media[0]["triggerContextCount"], 1)
        self.assertEqual(media[0]["triggerSemanticKinds"], ["abilityVoiceTriggerAction"])
        self.assertEqual(media[0]["triggerRoles"], ["authoredAbilityVoiceResponseTrigger"])
        self.assertEqual(media[0]["triggerOwnerValues"], ["chr_fixture", "skill_fixture"])
        self.assertEqual(
            media[0]["triggerSelectionStatuses"],
            ["responsiveRuntimeSelectionUnobserved", "uniqueEvent"],
        )
        self.assertEqual(
            media[0]["triggerContextSummaryEvidence"],
            "exactSerializedTriggerContextMediaJoin",
        )
        self.assertFalse(media[0]["triggerContextSummaryTruncated"])

    def test_trigger_context_event_category_recovers_unknown_media_semantics(self) -> None:
        media = [{
            "id": "8",
            "audioCategory": "unknown",
            "src": "/audio/voice.flac",
            "rel": "wwise/unknown/8.flac",
        }]
        catalog = {
            "contexts": [{
                "triggerId": "responsive:fixture",
                "semanticKind": "responsiveDialogVoice",
                "triggerRole": "authoredResponsiveVoiceCandidate",
                "meaning": {"category": "voice"},
                "mediaRefs": [{
                    "id": "8",
                    "src": "/audio/voice.flac",
                    "rel": "wwise/unknown/8.flac",
                }],
            }],
        }

        counts = audio_semantics.annotate_media_trigger_semantic_categories(media, catalog)

        self.assertEqual(
            counts,
            {
                "mediaWithSemanticCategoryFromTriggerContext": 1,
                "mediaSemanticCategoryFromTriggerEventCategory": 1,
                "mediaSemanticCategoryFromMonoBehaviourSfxField": 0,
            },
        )
        self.assertEqual(media[0]["semanticCategory"], "voice")
        self.assertEqual(
            media[0]["semanticCategoryEvidence"],
            "exactSerializedTriggerContextEventCategory",
        )
        self.assertEqual(media[0]["semanticCategoryContextCategories"], ["voice"])

    def test_mono_behaviour_audio_field_recovers_unknown_sfx_semantics(self) -> None:
        media = [{
            "id": "9",
            "audioCategory": "unknown",
            "src": "/audio/sfx.flac",
            "rel": "wwise/unknown/9.flac",
        }]
        catalog = {
            "contexts": [{
                "triggerId": "mono:fixture",
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": "soundSpawn",
                "meaning": {"category": "unknown"},
                "mediaRefs": [{
                    "id": "9",
                    "src": "/audio/sfx.flac",
                    "rel": "wwise/unknown/9.flac",
                }],
            }],
        }

        counts = audio_semantics.annotate_media_trigger_semantic_categories(media, catalog)

        self.assertEqual(counts["mediaWithSemanticCategoryFromTriggerContext"], 1)
        self.assertEqual(counts["mediaSemanticCategoryFromTriggerEventCategory"], 0)
        self.assertEqual(counts["mediaSemanticCategoryFromMonoBehaviourSfxField"], 1)
        self.assertEqual(media[0]["semanticCategory"], "sfx")
        self.assertEqual(
            media[0]["semanticCategoryEvidence"],
            "exactSerializedMonoBehaviourAudioIdFieldRole",
        )
        self.assertEqual(media[0]["semanticCategoryFieldRoles"], ["soundSpawn"])

    def test_mono_behaviour_mapped_role_keeps_sfx_gate_and_event_category(self) -> None:
        media = [{
            "id": "10",
            "audioCategory": "unknown",
            "src": "/audio/mapped-sfx.flac",
            "rel": "wwise/unknown/10.flac",
        }]
        catalog = {
            "contexts": [{
                "triggerId": "mono:mapped-fixture",
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": "componentSoundSpawn",
                "authoredFieldNameRaw": "_spawnAudioEvent",
                "serializedFieldPath": "$._spawnAudioEvent._id",
                "serializedFieldPathStatus": "exact",
                "meaning": {"category": "unknown"},
                "mediaRefs": [{
                    "id": "10",
                    "src": "/audio/mapped-sfx.flac",
                    "rel": "wwise/unknown/10.flac",
                }],
            }],
        }

        counts = audio_semantics.annotate_media_trigger_semantic_categories(media, catalog)

        self.assertEqual(counts["mediaSemanticCategoryFromMonoBehaviourSfxField"], 1)
        self.assertEqual(media[0]["audioCategory"], "unknown")
        self.assertEqual(media[0]["semanticCategory"], "sfx")
        self.assertEqual(media[0]["semanticCategoryFieldRoles"], ["componentSoundSpawn"])

        media_unknown = [{
            "id": "11",
            "audioCategory": "unknown",
            "src": "/audio/unknown.flac",
            "rel": "wwise/unknown/11.flac",
        }]
        unknown_catalog = {
            "contexts": [{
                "triggerId": "mono:unknown-fixture",
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": "componentSerializedAudioField",
                "meaning": {"category": "unknown"},
                "mediaRefs": [{
                    "id": "11",
                    "src": "/audio/unknown.flac",
                    "rel": "wwise/unknown/11.flac",
                }],
            }],
        }
        audio_semantics.annotate_media_trigger_semantic_categories(media_unknown, unknown_catalog)
        self.assertNotIn("semanticCategory", media_unknown[0])

        media_unsupported_water = [{
            "id": "12",
            "audioCategory": "unknown",
            "src": "/audio/water-unsupported.flac",
            "rel": "wwise/unknown/12.flac",
        }]
        unsupported_water_catalog = {
            "contexts": [{
                "triggerId": "mono:unsupported-water-fixture",
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": "componentSerializedAudioField",
                "situation": {
                    "authoredFieldNameRaw": "aimableSoundEvent",
                    "serializedFieldPath": "$.wrapper.aimableSoundEvent._id",
                    "serializedFieldPathStatus": "exact",
                },
                "meaning": {"category": "unknown"},
                "mediaRefs": [{
                    "id": "12",
                    "src": "/audio/water-unsupported.flac",
                    "rel": "wwise/unknown/12.flac",
                }],
            }],
        }
        audio_semantics.annotate_media_trigger_semantic_categories(
            media_unsupported_water,
            unsupported_water_catalog,
        )
        self.assertNotIn("semanticCategory", media_unsupported_water[0])

        media_water_interact = [{
            "id": "13",
            "audioCategory": "unknown",
            "src": "/audio/water-interact.flac",
            "rel": "wwise/unknown/13.flac",
        }]
        water_interact_catalog = {
            "contexts": [{
                "triggerId": "mono:water-interact-fixture",
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": "componentWaterInteractEnterSound",
                "situation": {
                    "authoredFieldNameRaw": "enterWaterSfx",
                    "serializedFieldPath": "$.enterWaterSfx._id",
                    "serializedFieldPathStatus": "exact",
                },
                "meaning": {"category": "unknown"},
                "mediaRefs": [{
                    "id": "13",
                    "src": "/audio/water-interact.flac",
                    "rel": "wwise/unknown/13.flac",
                }],
            }],
        }
        audio_semantics.annotate_media_trigger_semantic_categories(
            media_water_interact,
            water_interact_catalog,
        )
        self.assertNotIn("semanticCategory", media_water_interact[0])

    def test_control_only_event_role_uses_serialized_action_type(self) -> None:
        event_name = "au_ui_fixture_control"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": [event_name],
            "events": [],
            "eventEvidence": [],
            "typedUiTableWwiseEventAliases": [{
                "eventHash": event_hash,
                "name": event_name,
            }],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 7,
                "bank": "default_banks.pck",
                "actionEvidence": [
                    {"actionType": 0x1204, "operation": "operation0x1200"},
                    {"actionType": 0x1402, "operation": "operation0x1400"},
                ],
                "rootPlayActionCount": 0,
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }, {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["playbackRole"], "controlOnly")
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "audioLibraryControlKnown")
        self.assertEqual(rows[0]["purposeInvestigationPriority"], "secondary")
        self.assertEqual(
            rows[0]["playbackLocationStatus"],
            "libraryControlOnlyExternalCallerUnknown",
        )
        summary = event_summary.event_summary_row(rows[0], "event_details/00.json")
        self.assertEqual(summary["playbackRole"], "controlOnly")

    def test_typed_timeline_audio_id_name_replaces_anonymous_control_event(self) -> None:
        event_name = "au_dlg_foley_stop_chr"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        context = {
            "kind": "levelSequenceAudio",
            "authoredEventName": event_name,
            "authoredEventNameEvidence": (
                "exactTimelineDisplayNameHashEqualsSerializedAudioId"
            ),
        }
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": [],
            "events": [],
            "eventEvidence": [],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 7,
                "bank": "default_banks.pck",
                "actionEvidence": [{
                    "actionType": 0x0202,
                    "operation": "pause",
                }],
                "rootPlayActionCount": 0,
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }, {f"hashed-event:0x{event_hash:08x}": [context]})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], event_name)
        self.assertEqual(rows[0]["hash"], event_hash)
        self.assertEqual(rows[0]["playbackRole"], "controlOnly")
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "authoredContextKnown")
        self.assertEqual(rows[0]["purposeInvestigationPriority"], "resolved")
        self.assertEqual(
            rows[0]["eventNameCollectionSources"],
            ["exactTimelineDisplayNameHashEqualsSerializedAudioId"],
        )

    def test_unlabeled_typed_nonplay_action_is_control_only(self) -> None:
        profile = event_projection.wwise_event_action_profile([{
            "actionEvidence": [{"actionType": 0x3102, "operation": "operation0x3100"}],
            "rootPlayActionCount": 0,
            "traversalStatus": "complete",
        }])

        self.assertEqual(profile["role"], "controlOnly")
        self.assertEqual(profile["operationTypesHex"], ["0x3100"])
        self.assertEqual(profile["operationLabels"], ["operation0x3100"])
        self.assertEqual(profile["operationRows"], [{
            "operationType": 0x3100,
            "operationTypeHex": "0x3100",
            "operationLabels": ["operation0x3100"],
        }])

    def test_complete_zero_action_event_is_known_empty_library_definition(self) -> None:
        event_name = "au_global_fixture_empty"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": [event_name],
            "events": [],
            "eventEvidence": [],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 7,
                "bank": "default_banks.pck",
                "actionEvidence": [],
                "actionDispatchEvidence": {"serializedActionCount": 0},
                "rootPlayActionCount": 0,
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }, {})

        self.assertEqual(rows[0]["playbackRole"], "emptyEventDefinition")
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "audioLibraryEmptyEventKnown")
        self.assertEqual(rows[0]["purposeInvestigationPriority"], "secondary")
        self.assertEqual(
            rows[0]["playbackLocationStatus"],
            "libraryEmptyEventExternalCallerUnknown",
        )

    def test_audio_dialog_alias_names_raw_wwise_inventory_without_duplicate_hash_row(self) -> None:
        event_name = "eny_fixture_combat_taunt_sv"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, banks = event_projection.build_event_rows({
            "eventNames": [event_name],
            "events": [],
            "eventEvidence": [],
            "audioDialogWwiseEventAliases": [{
                "eventHash": event_hash,
                "name": event_name,
                "voiceId": event_hash,
            }],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 7,
                "bankVersion": 150,
                "bank": "default_chinese_banks.pck",
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }, {event_name: [{"kind": "responsiveDialogVoice"}]})

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], event_name)
        self.assertEqual(rows[0]["name"], event_name)
        self.assertTrue(rows[0]["foundInWwise"])
        self.assertEqual(rows[0]["eventIdentityStatus"], "recoveredAuthoredName")
        self.assertEqual(rows[0]["contexts"][0]["kind"], "responsiveDialogVoice")
        self.assertEqual(rows[0]["category"], "voice")
        self.assertEqual(rows[0]["categoryEvidence"], "exactAudioDialogVoiceIdentity")
        self.assertEqual(rows[0]["categoryNameEvidence"], "authoredEnemyEventNamePattern")
        self.assertEqual(banks[0]["namedEventCount"], 1)

    def test_voice_table_alias_names_inventory_and_preserves_unobserved_route(self) -> None:
        event_name = "vo_fixture_narrating"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        alias = {
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "name": event_name,
            "evidence": "typedVoiceTableEventFieldHashEqualsCurrentWwiseEventId",
            "usages": [{
                "table": "AudioDialogChannel.json",
                "field": "narratingWwiseEvent",
                "routeKind": "narratingChannelEvent",
                "runtimeRoute": "SelectWwiseEvent -> PlayVoice",
                "occurrenceCount": 3,
                "rowPathSamples": ["a", "b", "c"],
                "sources": ["StreamingAssets/AudioDialogChannel.json"],
            }],
        }
        audio_index = {
            "eventNames": [],
            "events": [],
            "eventEvidence": [],
            "voiceTableWwiseEventAliases": [alias],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 7,
                "bankVersion": 150,
                "bank": "default_banks.pck",
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }
        contexts = audio_semantics.voice_table_event_contexts(audio_index)
        rows, _, banks = event_projection.build_event_rows(audio_index, contexts)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], event_name)
        self.assertEqual(rows[0]["eventIdentityStatus"], "recoveredAuthoredName")
        self.assertEqual(rows[0]["categoryEvidence"], "exactTypedVoiceTableWwiseEventField")
        self.assertEqual(rows[0]["contexts"][0]["kind"], "voiceNarratingChannelEvent")
        self.assertEqual(rows[0]["contexts"][0]["occurrenceCount"], 3)
        self.assertEqual(
            rows[0]["contexts"][0]["runtimeSelectionStatus"],
            "authoredRoutePresentLiveVoiceAndBranchSelectionUnobserved",
        )
        self.assertEqual(banks[0]["namedEventCount"], 1)

    def test_cross_source_exact_alias_conflict_fails_closed(self) -> None:
        rows = event_projection.exact_wwise_event_aliases({
            "audioDialogWwiseEventAliases": [{"eventHash": 123, "name": "vo_fixture_a"}],
            "voiceTableWwiseEventAliases": [{"eventHash": 123, "name": "vo_fixture_b"}],
        })
        self.assertEqual(rows, [])

    def test_typed_ui_table_context_preserves_lua_execution_boundary(self) -> None:
        event_name = "au_ui_fixture_video"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        audio_index = {"typedUiTableWwiseEventAliases": [{
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "name": event_name,
            "evidence": "typedTableGetterAndLuaAudioConsumerHashEqualsCurrentWwiseEventId",
            "usages": [{
                "table": "GachaCharPoolTable.json",
                "field": "videoAudioKey",
                "routeKind": "uiVideoAudioEvent",
                "runtimeRoute": "VideoPlayer.PlayAudio -> AudioAdapter.PostEvent",
                "consumerEvidence": ["GachaPoolVideoCtrl.lua:93"],
                "occurrenceCount": 2,
                "rowPathSamples": ["pool_a", "pool_b"],
                "sources": ["GachaCharPoolTable.json"],
            }],
        }]}

        contexts = audio_semantics.typed_ui_table_event_contexts(audio_index)[event_name]

        self.assertEqual(contexts[0]["kind"], "uiVideoAudioEvent")
        self.assertEqual(contexts[0]["occurrenceCount"], 2)
        self.assertEqual(contexts[0]["consumerEvidence"], ["GachaPoolVideoCtrl.lua:93"])
        self.assertEqual(
            contexts[0]["runtimeExecutionStatus"],
            "authoredLuaAudioCallsiteBranchExecutionUnobserved",
        )
        self.assertEqual(contexts[0]["playbackPlacementStatus"], "authoredPossibleTrigger")

    def test_typed_ui_alias_names_raw_inventory_without_hash_duplicate(self) -> None:
        event_name = "au_ui_fixture_open"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": [],
            "events": [],
            "eventEvidence": [],
            "typedUiTableWwiseEventAliases": [{"eventHash": event_hash, "name": event_name}],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 1,
                "bankVersion": 150,
                "bank": "default_banks.pck",
                "mediaIds": [],
                "traversalStatus": "complete",
            }],
        }, {event_name: [{"kind": "uiAnimationOpenEvent"}]})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], event_name)
        self.assertEqual(rows[0]["eventIdentityStatus"], "recoveredAuthoredName")

    def test_sns_voice_context_preserves_click_and_stop_boundary(self) -> None:
        event_name = "au_ui_event_sns_fixture_voice"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        contexts = audio_semantics.sns_voice_event_contexts({
            "snsVoiceWwiseEventAliases": [{
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "name": event_name,
                "usages": [{
                    "table": "SNSDialogTable.json",
                    "dialogId": "dialog_fixture",
                    "contentId": 1,
                    "contentType": 5,
                    "contentTypeName": "Voice",
                    "contentParamIndex": 0,
                    "speaker": "fixture",
                    "durationSeconds": "4",
                    "sources": ["SNSDialogTable.json"],
                }],
            }],
        })[event_name]
        self.assertEqual(contexts[0]["kind"], "snsVoiceMessageEvent")
        self.assertIn("AudioAdapter.PostEvent", contexts[0]["runtimeRoute"])
        self.assertIn("StopByPlayingId", contexts[0]["runtimeRoute"])
        self.assertEqual(contexts[0]["runtimeExecutionStatus"], "authoredClickHandlerExecutionUnobserved")
        self.assertEqual(contexts[0]["playbackPlacementStatus"], "authoredPossibleTrigger")

    def test_skill_id_dictionary_alias_names_event_without_trigger_context(self) -> None:
        event_name = "eny_fixture_skill_audio_identity"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": [],
            "events": [],
            "eventEvidence": [],
            "skillIdDictionaryWwiseEventAliases": [{
                "eventHash": event_hash,
                "name": event_name,
                "dictionaryKind": "skill_id",
                "numericSkillIds": ["7"],
                "tableSources": ["NumIdStrTable.json"],
                "skillDataSources": [f"SkillData/{event_name}.json"],
                "evidence": "skillIdDictionaryNameAndSkillDataFileHashEqualsCurrentWwiseEventId",
                "playbackPlacementStatus": "identityOnlyNoAudioConsumer",
            }],
            "wwiseEventInventory": [{
                "eventHash": event_hash,
                "bankId": 1,
                "bank": "default_banks.pck",
                "mediaIds": [],
                "rootPlayActionCount": 1,
                "actionEvidence": [{"operation": "play"}],
                "traversalStatus": "complete",
            }],
        }, {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], event_name)
        self.assertEqual(rows[0]["category"], "sfx")
        self.assertEqual(rows[0]["categoryEvidence"], "exactSkillIdDictionaryEventIdentity")
        self.assertEqual(rows[0]["contexts"], [])
        self.assertEqual(rows[0]["identityOnlyPlaybackPlacementStatus"], "identityOnlyNoAudioConsumer")
        self.assertEqual(rows[0]["identityNumericSkillIds"], ["7"])
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "identityOnlyNoConsumer")
        self.assertEqual(rows[0]["purposeInvestigationPriority"], "highest")

    def test_responsive_voice_contexts_preserve_trigger_and_tone_selection_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            event_name = "eny_fixture_combat_taunt_sv"
            event_hash = identifiers.audio_hash_generator_compute(event_name)
            signed_hash = event_hash if event_hash < (1 << 31) else event_hash - (1 << 32)
            (table_root / "ResponsiveDialog.json").write_text(json.dumps({
                "1": {"speakers": {"eny_fixture": {"triggers": {
                    "combat_taunt": {
                        "response": [signed_hash],
                        "triggerTypeId": 149,
                        "weight": [100],
                    }
                }}}}
            }), encoding="utf-8")
            (table_root / "AIBark.json").write_text(json.dumps({
                "bark_battle_taunt": {"array": [{
                    "barkId": "bark_battle_taunt",
                    "barkOdd": [1],
                    "delay": 0.0,
                    "isEnabled": True,
                    "isShuffle": True,
                    "speakerType": 2,
                    "triggerKey": ["combat_taunt"],
                    "triggerOdd": 1,
                    "type": 1,
                    "voType": [0],
                }]},
            }), encoding="utf-8")
            (table_root / "AudioVoTone.json").write_text(json.dumps({
                str(signed_hash): {"toneList": [signed_hash]}
            }), encoding="utf-8")
            (table_root / "AudioVoiceExtraData.json").write_text(json.dumps({
                str(signed_hash): {
                    "devStageCN": 2,
                    "devStageEN": 1,
                    "devStageJP": 0,
                    "devStageKR": 0,
                    "durationCN": 1.25,
                    "durationEN": 0.0,
                    "durationJP": 0.0,
                    "durationKR": 0.0,
                }
            }), encoding="utf-8")
            contexts = responsive_voice.collect_responsive_voice_contexts(
                export_root,
                {"audioDialogWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "voiceId": signed_hash,
                    "name": event_name,
                    "sources": ["AudioDialog.json"],
                }]},
                native_context=validated_native_context(),
            )[event_name]

            self.assertEqual(
                {row["kind"] for row in contexts},
                {
                    "audioDialogVoiceDefinition", "responsiveDialogVoice",
                    "voiceToneVariant", "responsiveDialogToneVariant",
                },
            )
            response = next(row for row in contexts if row["kind"] == "responsiveDialogVoice")
            definition = next(row for row in contexts if row["kind"] == "audioDialogVoiceDefinition")
            self.assertEqual(definition["voiceExtraDataStatus"], "exactSignedVoiceIdTableRows")
            self.assertEqual(definition["voiceExtraData"][0]["devStageCN"], 2)
            self.assertEqual(definition["voiceExtraData"][0]["durationCN"], 1.25)
            self.assertEqual(definition["voiceExtraData"][0]["sourceLayer"], "StreamingAssets")
            self.assertEqual(response["triggerKey"], "combat_taunt")
            self.assertEqual(response["speakerId"], "eny_fixture")
            self.assertEqual(response["responseWeight"], 100)
            self.assertEqual(response["playbackPlacementStatus"], "authoredPossibleTrigger")
            self.assertEqual(response["aiBarkRuntimeStatus"], "exactAIBarkTableTriggerCandidate")
            self.assertEqual(len(response["aiBarkRequests"]), 1)
            bark = response["aiBarkRequests"][0]
            self.assertEqual(bark["barkId"], "bark_battle_taunt")
            self.assertEqual(bark["triggerKey"], "combat_taunt")
            self.assertEqual(bark["barkType"], 1)
            self.assertEqual(bark["barkVoTypes"], [0])
            self.assertEqual(bark["barkSystemMethodVa"], "0x1841957b0")
            self.assertEqual(bark["voicePostInvocationVa"], "0x184197735")
            tone = next(row for row in contexts if row["kind"] == "voiceToneVariant")
            self.assertEqual(tone["playbackPlacementStatus"], "selectionTransformOnly")
            composed = next(
                row for row in contexts if row["kind"] == "responsiveDialogToneVariant"
            )
            self.assertEqual(composed["triggerKey"], "combat_taunt")
            self.assertEqual(composed["aiBarkRequests"][0]["barkId"], "bark_battle_taunt")
            self.assertEqual(
                composed["playbackPlacementStatus"],
                "authoredPossibleTriggerViaToneTransform",
            )

    def test_ai_bark_catalog_does_not_infer_enemy_common_trigger_names(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "AIBark.json").write_text(json.dumps({
                "bark_battle_start": {"array": [{
                    "barkId": "bark_battle_start",
                    "triggerKey": ["combat_intobattle"],
                    "type": 1,
                    "voType": [0],
                }]},
            }), encoding="utf-8")
            rows = responsive_voice.collect_ai_bark_trigger_rows(
                export_root,
                native_context=validated_native_context(),
            )
            self.assertIn("combat_intobattle", rows)
            self.assertNotIn("common_attack", rows)
            self.assertNotIn("common_escape", rows)

    def test_enemy_trigger_voice_action_maps_only_exact_native_dictionary_keys(self) -> None:
        native = native_evidence.ENEMY_TRIGGER_VOICE_ACTION_NATIVE
        mappings = {row["triggerKey"]: row for row in native["voiceTypes"]}
        self.assertEqual(
            {key: row["voiceType"] for key, row in mappings.items()},
            {
                "combat_alarm": 0,
                "combat_intobattle": 1,
                "combat_fighting": 2,
                "combat_outbattle_flee": 3,
                "combat_kill": 4,
            },
        )
        self.assertNotIn("common_attack", mappings)
        self.assertNotIn("common_escape", mappings)
        self.assertEqual(native["playbackInvocationVa"], "0x186bc695e")

    def test_responsive_voice_context_exposes_enemy_trigger_action_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            event_name = "eny_fixture_combat_fighting_sv"
            event_hash = identifiers.audio_hash_generator_compute(event_name)
            signed_hash = event_hash if event_hash < (1 << 31) else event_hash - (1 << 32)
            (table_root / "ResponsiveDialog.json").write_text(json.dumps({
                "1": {"speakers": {"eny_fixture": {"triggers": {
                    "combat_fighting": {"response": [signed_hash], "weight": [100]}
                }}}}
            }), encoding="utf-8")
            contexts = responsive_voice.collect_responsive_voice_contexts(
                export_root,
                {"audioDialogWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "voiceId": signed_hash,
                    "name": event_name,
                }]},
                native_context=validated_native_context(),
            )[event_name]

        response = next(row for row in contexts if row["kind"] == "responsiveDialogVoice")
        self.assertEqual(response["enemyTriggerVoiceActionStatus"], "exactNativeVoiceTypeTriggerMapping")
        self.assertEqual(response["enemyTriggerVoiceAction"]["voiceType"], 2)
        self.assertEqual(response["enemyTriggerVoiceAction"]["mappingAddInvocationVa"], "0x186bc6aa4")

    def test_ai_bark_catalog_keeps_missing_response_ids_as_authored_not_playable(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "AIBark.json").write_text(json.dumps({
                "bark_idle": {"array": [{
                    "barkId": "bark_idle",
                    "triggerKey": ["explore_idletalk"],
                    "type": 2,
                    "voType": [0],
                }]},
            }), encoding="utf-8")
            (table_root / "ResponsiveDialog.json").write_text(json.dumps({
                "32": {"speakers": {"any": {"triggers": {
                    "explore_idletalk": {
                        "response": [101, 202],
                        "weight": [1, 1],
                    },
                }}}},
            }), encoding="utf-8")

            catalog = responsive_voice.build_ai_bark_catalog(
                export_root,
                {"audioDialogWwiseEventAliases": []},
                [{"audioDialogKey": 101, "storyLineBindingCount": 1}],
                native_context=validated_native_context(),
            )

            self.assertEqual(catalog["counts"]["authoredBarkIds"], 1)
            self.assertEqual(catalog["counts"]["uniqueResponseVoiceIds"], 2)
            self.assertEqual(catalog["counts"]["exactStoryLineBoundVoiceIds"], 1)
            self.assertEqual(catalog["counts"]["playableVoiceIds"], 1)
            self.assertEqual(catalog["counts"]["unresolvedVoiceIds"], 1)
            self.assertEqual(catalog["counts"]["unresolvedSentenceType32AnyVoiceIds"], 1)
            self.assertEqual(catalog["unresolvedResponses"][0]["voiceId"], 202)
            self.assertEqual(
                catalog["unresolvedResponses"][0]["status"],
                "authoredAIBarkResponseWithoutCurrentPlaybackObject",
            )

    def test_responsive_voice_contexts_merge_streaming_and_persistent_tables(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            event_name = "chr_fixture_action_dodge_sv"
            event_hash = identifiers.audio_hash_generator_compute(event_name)
            signed_hash = event_hash if event_hash < (1 << 31) else event_hash - (1 << 32)
            for source, trigger_key in (
                ("StreamingAssets", "action_dash_start"),
                ("Persistent", "action_dodge"),
            ):
                table_root = export_root / "structured" / source / "Table"
                table_root.mkdir(parents=True)
                (table_root / "ResponsiveDialog.json").write_text(json.dumps({
                    "1": {"speakers": {"chr_fixture": {"triggers": {
                        trigger_key: {
                            "response": [signed_hash],
                            "triggerTypeId": 149,
                            "weight": [100],
                        }
                    }}}}
                }), encoding="utf-8")

            contexts = responsive_voice.collect_responsive_voice_contexts(
                export_root,
                {"audioDialogWwiseEventAliases": [{
                    "eventHash": event_hash,
                    "voiceId": signed_hash,
                    "name": event_name,
                    "sources": ["AudioDialog.json"],
                }]},
                native_context=validated_native_context(),
            )[event_name]

        responses = [row for row in contexts if row["kind"] == "responsiveDialogVoice"]
        self.assertEqual(
            {row["triggerKey"] for row in responses},
            {"action_dash_start", "action_dodge"},
        )
        self.assertEqual(
            {row["source"] for row in responses},
            {
                "structured/StreamingAssets/Table/ResponsiveDialog.json",
                "structured/Persistent/Table/ResponsiveDialog.json",
            },
        )

    def test_builds_responsive_voice_trigger_catalog_row(self) -> None:
        rows = audio_semantics._build_responsive_voice_trigger_contexts([{
            "id": "chr_fixture_action_dodge_sv",
            "hash": 123,
            "category": "voice",
            "foundInWwise": True,
            "possibleMediaCount": 1,
            "media": [],
            "contexts": [{
                "kind": "responsiveDialogVoice",
                "sentenceType": "1",
                "speakerId": "chr_fixture",
                "triggerKey": "action_dodge",
                "triggerTypeId": 149,
                "responseIndex": 0,
                "responseWeight": 100,
                "voiceId": 123,
                "source": "structured/Persistent/Table/ResponsiveDialog.json",
                "evidence": "exactResponsiveDialogResponseVoiceId",
                "runtimeRoute": "VoiceResponseProcessor -> VoicePlayer.PlayVoice",
                "runtimeSelectionStatus": "liveChoiceUnobserved",
            }],
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "responsiveDialogVoice")
        self.assertEqual(rows[0]["situation"]["triggerKey"], "action_dodge")
        self.assertEqual(rows[0]["owner"]["speakerId"], "chr_fixture")
        self.assertEqual(
            rows[0]["owner"]["source"],
            "structured/Persistent/Table/ResponsiveDialog.json",
        )
        self.assertEqual(rows[0]["runtimeActivationStatus"], "liveResponseSelectionUnobserved")

    def test_levelscript_dynamic_property_resolution_becomes_authored_event_context(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            path = (
                export_root
                / "structured/StreamingAssets/Data/Json/LevelScriptData"
                / "map01_lv001/2100210004.json"
            )
            path.parent.mkdir(parents=True)
            path.write_bytes(b"fixture")

            def decode_file(_path, _data):
                return {
                    "targetCount": 1,
                    "rows": [{
                        "record": {
                            "start": 0,
                            "uid": "fixture-uid",
                            "localId": 7,
                            "unionTag": 0x034E,
                            "serializedMemberCount": 0x0B,
                        },
                        "actionMapRole": "fixture",
                        "audioAction": {
                            "action": "PlayAudio",
                            "nativeMappingId": "fixture",
                            "payloadShape": "fixture",
                            "fields": {
                                "key": {
                                    "sourceField": "_key",
                                    "bindingKind": "dynamic",
                                    "paramSource": 200,
                                    "idRef": -1,
                                    "path": "Start_music",
                                },
                            },
                            "eventBindings": [],
                            "cueBindings": [],
                        },
                    }],
                }

            brief = {
                "properties": [{
                    "name": "Start_music",
                    "value": {
                        "valueType": 7,
                        "atomCount": 1,
                        "atoms": [{
                            "valueBit64": 0,
                            "text": "au_music_tundra_001_race_mode",
                        }],
                    },
                }],
            }
            with patch.object(
                audio_semantics,
                "_load_levelscript_brief_property_sources",
                return_value=(brief, "structured/StreamingAssets/Data/Json/LevelData/map01_lv001/fixture.json"),
            ):
                semantics = audio_semantics.collect_levelscript_audio_semantics(
                    export_root,
                    decode_file=decode_file,
                    cue_semantics={"cueDefinitions": {}},
                )

            self.assertEqual(1, len(semantics["resolvedDynamicEventBindings"]))
            binding = semantics["resolvedDynamicEventBindings"][0]
            self.assertEqual("resolvedLevelScriptBriefProperty", binding["resolutionStatus"])
            self.assertEqual("au_music_tundra_001_race_mode", binding["resolvedEventName"])
            context = semantics["eventContexts"]["au_music_tundra_001_race_mode"][0]
            self.assertEqual(
                "property_value_resolved",
                context["fields"]["key"]["parameterStatus"],
            )
            self.assertEqual(
                "au_music_tundra_001_race_mode",
                binding["binding"]["resolvedValue"],
            )
            self.assertEqual("levelScriptAudioActionDynamicProperty", context["kind"])
            self.assertEqual("Start_music", context["resolution"]["propertyName"])
            self.assertEqual(1, semantics["stats"]["resolvedDynamicEventBindings"])

    def test_audio_hash_generator_matches_native_utf16_fnv1_without_trimming(self) -> None:
        self.assertEqual(
            identifiers.audio_hash_generator_compute("au_cue_music_combat_boss_state1"),
            0x8DD0B0C9,
        )
        self.assertEqual(
            identifiers.audio_hash_generator_compute("AU_CUE_MUSIC_COMBAT_BOSS_STATE1"),
            0x8DD0B0C9,
        )
        self.assertEqual(
            identifiers.audio_hash_generator_compute(" au_cue_music_combat_boss_state1"),
            0x7C6CA2E7,
        )
        self.assertNotEqual(
            identifiers.audio_hash_generator_compute("\u00c9"),
            identifiers.audio_hash_generator_compute("\u00e9"),
        )

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
        rows, _, _ = event_projection.build_event_rows({
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

    def test_music_node_evidence_survives_debug_event_compaction(self) -> None:
        music_node = {
            "objectId": 10,
            "objectType": 12,
            "nodeKind": "musicSwitchContainer",
            "childIds": [11],
            "treeDepth": 1,
            "treeLeaves": [{"audioNodeId": 11, "pathKeys": [22]}],
            "structureStatus": "typedExactV150",
        }
        dispatch = {
            "playbackActionCount": 2,
            "timingClass": "coDispatchWithAuthoredDelayDifference",
            "explicitDelayActionCount": 1,
        }
        rows, _, _ = event_projection.build_event_rows({
            "eventNames": ["au_music_fixture"],
            "events": [],
            "eventEvidence": [{
                "eventId": "au_music_fixture",
                "eventHash": 5,
                "bankId": 9,
                "traversalStatus": "complete",
                "musicNodeEvidence": [music_node],
                "actionDispatchEvidence": dispatch,
            }],
        }, {})

        self.assertEqual(rows[0]["evidence"][0]["musicNodeEvidence"], [music_node])
        self.assertEqual(rows[0]["evidence"][0]["actionDispatchEvidence"], dispatch)

    def test_switch_mapping_compaction_preserves_selector_structure_without_flat_children(self) -> None:
        rows = [
            {
                "objectType": 6,
                "edgeKind": "switchCandidate",
                "childCount": 3,
                "parserConfidence": "wwise150TypedReciprocalChildren",
                "switchMappingEvidence": {
                    "parserStatus": "typedExactV150FlatPackages",
                    "groupType": "switch",
                    "groupId": 0x12345678,
                    "defaultValueId": 0x11,
                    "continuousValidation": True,
                    "packages": [
                        {"valueId": 0x11, "childIds": [1]},
                        {"valueId": 0x22, "childIds": [2, 3]},
                    ],
                    "associations": [
                        {
                            "childId": 1,
                            "onSwitchMode": "stop",
                            "continuePlayback": True,
                            "isFirstOnly": False,
                            "fadeOutTimeMs": 250,
                            "fadeInTimeMs": 0,
                        }
                    ],
                    "mappedChildIdsOutsideChildren": [],
                    "unmappedChildIds": [],
                    "associationChildIdsOutsideChildren": [],
                },
            },
            {
                "objectType": 6,
                "edgeKind": "switchCandidate",
                "childCount": 2,
                "parserConfidence": "wwise150TypedReciprocalChildren",
                "switchMappingEvidence": {
                    "parserStatus": "unresolvedV150SwitchTail",
                    "failureReason": "distinctLayout",
                },
            },
        ]

        compact = event_projection.compact_container_evidence(rows)

        self.assertEqual(len(compact), 1)
        selector = compact[0]
        self.assertEqual(selector["selectorNodeCount"], 2)
        self.assertEqual(selector["typedSelectorNodeCount"], 1)
        self.assertEqual(selector["unresolvedSelectorNodeCount"], 1)
        self.assertEqual(selector["selectorGroupTypes"], {"switch": 1})
        self.assertEqual(selector["selectorGroupIdsHex"], ["0x12345678"])
        self.assertEqual(selector["selectorPackageCount"], 2)
        self.assertEqual(selector["strictSubsetSelectorPackageCount"], 2)
        self.assertEqual(selector["selectorAssociationCount"], 1)
        self.assertEqual(selector["selectorSwitchModes"], {"stop": 1})
        self.assertEqual(selector["continuePlaybackAssociationCount"], 1)
        self.assertEqual(selector["nonzeroFadeOutAssociationCount"], 1)
        self.assertNotIn("packages", selector)

    def test_selector_branch_projection_keeps_exact_values_media_and_authored_controls(self) -> None:
        selector_rows = [{
            "objectType": 6,
            "objectId": 700,
            "rootActionId": 701,
            "childCount": 3,
            "parserConfidence": "wwise150TypedReciprocalChildren",
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "state",
                "groupTypeRaw": 1,
                "groupId": 0xF6699CF4,
                "defaultValueId": 0x2CA33BDB,
                "packages": [
                    {"packageIndex": 0, "valueId": 0x1A9FC91F, "childIds": [10]},
                    {"packageIndex": 1, "valueId": 0x1B9ABDB1, "childIds": [900]},
                    # The authored default has no mapped child and must not be dropped.
                    {"packageIndex": 2, "valueId": 0x2CA33BDB, "isDefaultValue": True, "childIds": []},
                ],
                    "associations": [{
                        "associationIndex": 0,
                        "childId": 10,
                        "flagsRaw": 0x82,
                        "flagsUnknownMask": 0x80,
                        "onSwitchMode": "stop",
                        "onSwitchModeRaw": 1,
                        "onSwitchModeRawByte": 1,
                        "onSwitchModeUnknownMask": 0xF8,
                    "isFirstOnly": True,
                    "continuePlayback": False,
                    "fadeOutTimeMs": 500,
                    "fadeInTimeMs": 25,
                }],
                "mappedChildIdsOutsideChildren": [],
                "unmappedChildIds": [11, 12],
                "associationChildIdsOutsideChildren": [],
            },
        }]
        media = [{
            "mediaId": 55,
            "src": "xinput.flac",
            "wwiseMediaEvidence": [{"bankId": 1, "soundObjectIds": [10]}],
        }]
        branches = event_projection.selector_branch_projection(
            [{"bankId": 1, "bank": "fixture", "containerEvidence": selector_rows}],
            media,
            audio_semantics.wwise_selector_group_catalog(),
        )
        self.assertEqual(len(branches), 1)
        branch = branches[0]
        self.assertEqual(branch["groupIdHex"], "0xf6699cf4")
        self.assertEqual(branch["typedExactStatus"], "typedExactV150FlatPackages")
        self.assertEqual(branch["runtimeSelection"], "groupValueUnobservedAllChildrenRemainPossible")
        packages = branch["packages"]
        self.assertEqual(packages[0]["semantic"]["semanticName"], "XInput")
        self.assertEqual(packages[1]["semantic"]["semanticName"], "ScePad")
        self.assertEqual(packages[0]["directMediaIds"], [55])
        self.assertEqual(packages[0]["mediaStatus"], "directMediaExactSoundObjectJoin")
        self.assertEqual(packages[1]["mediaStatus"], "descendantMediaUnresolved")
        self.assertEqual(packages[2]["valueIdHex"], "0x2ca33bdb")
        self.assertTrue(packages[2]["isDefault"])
        self.assertEqual(packages[2]["childIds"], [])
        self.assertEqual(packages[2]["semanticJoinStatus"], "unresolvedValueId")
        association = branch["associations"][0]
        self.assertEqual(association["onSwitchMode"], "stop")
        self.assertEqual(association["onSwitchModeRaw"], 1)
        self.assertEqual(association["flagsRaw"], 0x82)
        self.assertEqual(association["flagsUnknownMask"], 0x80)
        self.assertEqual(association["onSwitchModeUnknownMask"], 0xF8)
        self.assertEqual(association["fadeOutTimeMs"], 500)
        self.assertEqual(association["fadeInTimeMs"], 25)
        for forbidden in ("selectedValue", "activeBranch", "playedBranch"):
            self.assertNotIn(forbidden, str(branch))

    def test_selector_branch_projection_keeps_unresolved_nested_type6_without_closure(self) -> None:
        row = {
            "objectType": 6,
            "objectId": 800,
            "childCount": 1,
            "parserConfidence": "wwise150TypedReciprocalChildren",
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "switch",
                "groupId": 0x12345678,
                "defaultValueId": 1,
                "packages": [{"valueId": 1, "childIds": [900]}],
                "associations": [],
                "mappedChildIdsOutsideChildren": [],
                "unmappedChildIds": [],
                "associationChildIdsOutsideChildren": [],
            },
        }
        branch = event_projection.selector_branch_projection(
            [{"containerEvidence": [row]}],
            [{"mediaId": 66, "wwiseMediaEvidence": [{"soundObjectIds": [901]}]}],
        )[0]
        self.assertEqual(branch["packages"][0]["childIds"], [900])
        self.assertEqual(branch["packages"][0]["directMediaIds"], [])
        self.assertEqual(branch["packages"][0]["mediaStatus"], "descendantMediaUnresolved")

    def test_selector_branch_media_join_requires_exact_selector_and_media_bank(self) -> None:
        row = {
            "objectType": 6,
            "objectId": 801,
            "childCount": 1,
            "parserConfidence": "wwise150TypedReciprocalChildren",
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "switch",
                "groupId": 0x12345678,
                "defaultValueId": 1,
                "packages": [{"valueId": 1, "childIds": [10]}],
                "associations": [],
                "mappedChildIdsOutsideChildren": [],
                "unmappedChildIds": [],
                "associationChildIdsOutsideChildren": [],
            },
        }
        media = [
            {"mediaId": 66, "wwiseMediaEvidence": [{"bankId": 2, "soundObjectIds": [10]}]},
            {"mediaId": 67, "wwiseMediaEvidence": [{"bankId": 1, "soundObjectIds": [10]}]},
            {"mediaId": 68, "wwiseMediaEvidence": [{"soundObjectIds": [10]}]},
            {"mediaId": 69, "wwiseMediaEvidence": [{"bankId": 1, "soundObjectIds": [10, -1]}]},
            {"mediaId": 70, "wwiseMediaEvidence": [{"bankId": True, "soundObjectIds": [10]}]},
        ]
        branch = event_projection.selector_branch_projection(
            [{"bankId": 1, "containerEvidence": [row]}], media
        )[0]
        self.assertEqual(branch["packages"][0]["directMediaIds"], [67])
        missing_bank = event_projection.selector_branch_projection(
            [{"containerEvidence": [row]}], media
        )[0]
        self.assertEqual(missing_bank["packages"][0]["directMediaIds"], [])

    def test_selector_branch_projection_fails_closed_for_malformed_type6_shapes(self) -> None:
        malformed_rows = [
            {
                "objectType": "six",
                "childCount": "bad",
                "switchMappingEvidence": {
                    "parserStatus": "typedExactV150FlatPackages",
                    "groupType": "switch",
                    "groupId": 1,
                    "defaultValueId": 1,
                    "packages": [],
                    "associations": [],
                },
            },
            {
                "objectType": 6,
                "childCount": "bad",
                "switchMappingEvidence": {
                    "parserStatus": "typedExactV150FlatPackages",
                    "groupType": "switch",
                    "groupId": 1,
                    "defaultValueId": 1,
                    "packages": [{"valueId": 1, "childIds": "10"}],
                    "associations": [],
                },
            },
            {
                "objectType": 6,
                "switchMappingEvidence": {
                    "parserStatus": "typedExactV150FlatPackages",
                    "groupType": "switch",
                    "groupId": 1,
                    "defaultValueId": 1,
                    "packages": "not-an-array",
                    "associations": [],
                },
            },
        ]
        compact = event_projection.compact_container_evidence(malformed_rows)
        self.assertNotIn("selectorNodeCount", compact[0])
        branches = event_projection.selector_branch_projection(
            [{"bankId": 1, "containerEvidence": malformed_rows}], []
        )
        self.assertEqual(len(branches), 2)
        self.assertTrue(all(not branch["typedExact"] for branch in branches))
        self.assertTrue(all(branch.get("packages", []) == [] for branch in branches))
        self.assertTrue(all("typedExactV150FlatPackages" not in branch["typedExactStatus"] for branch in branches))

    def test_selector_branch_exact_shape_rejects_bad_id_arrays_and_single_ids(self) -> None:
        base_row = {
            "objectType": 6,
            "objectId": 100,
            "rootActionId": 200,
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "switch",
                "groupId": 1,
                "defaultValueId": 2,
                "packages": [{"valueId": 2, "childIds": [10]}],
                "associations": [{"childId": 10}],
                "mappedChildIdsOutsideChildren": [],
                "unmappedChildIds": [],
                "associationChildIdsOutsideChildren": [],
            },
        }

        def assert_unresolved(row: dict, *, bank_id: object = 7) -> None:
            branch = event_projection.selector_branch_projection(
                [{"bankId": bank_id, "containerEvidence": [row]}], []
            )[0]
            self.assertFalse(branch["typedExact"])
            self.assertNotEqual(branch["typedExactStatus"], "typedExactV150FlatPackages")
            self.assertEqual(branch.get("packages", []), [])
            self.assertEqual(branch.get("associations", []), [])

        # A malformed ID array is an invalid exact-shape claim.  In particular,
        # do not silently discard a bad member or iterate a scalar string.
        bad_array_members = [{}, True, "not-numeric", -1, 0x100000000]
        for field in (
            "mappedChildIdsOutsideChildren",
            "unmappedChildIds",
            "associationChildIdsOutsideChildren",
        ):
            for bad_member in bad_array_members:
                row = copy.deepcopy(base_row)
                row["switchMappingEvidence"][field] = [bad_member]
                assert_unresolved(row)
        for bad_member in bad_array_members:
            row = copy.deepcopy(base_row)
            row["switchMappingEvidence"]["packages"][0]["childIds"] = [bad_member]
            assert_unresolved(row)

        # Package and association rows are exact-shape arrays too; malformed
        # elements must not be skipped to preserve a false exact projection.
        for field, bad_value in (
            ("packages", [{}]),
            ("packages", [True]),
            ("packages", ["not-a-package"]),
            ("associations", [{}]),
            ("associations", [True]),
            ("associations", ["not-an-association"]),
        ):
            row = copy.deepcopy(base_row)
            row["switchMappingEvidence"][field] = bad_value
            assert_unresolved(row)
        for bad_member in bad_array_members[1:]:
            row = copy.deepcopy(base_row)
            row["switchMappingEvidence"]["associations"][0]["childId"] = bad_member
            assert_unresolved(row)
            row = copy.deepcopy(base_row)
            row["switchMappingEvidence"]["packages"][0]["valueId"] = bad_member
            assert_unresolved(row)
        for field in ("groupId", "defaultValueId"):
            for bad_value in bad_array_members[1:]:
                row = copy.deepcopy(base_row)
                row["switchMappingEvidence"][field] = bad_value
                assert_unresolved(row)
        for field in ("objectId", "rootActionId"):
            for bad_value in bad_array_members[1:]:
                row = copy.deepcopy(base_row)
                row[field] = bad_value
                assert_unresolved(row)
        for bad_value in bad_array_members[1:]:
            assert_unresolved(copy.deepcopy(base_row), bank_id=bad_value)

    def test_selector_branch_empty_packages_are_unresolved_not_exact(self) -> None:
        row = {
            "objectType": 6,
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "switch",
                "groupId": 1,
                "defaultValueId": 2,
                "packages": [],
                "associations": [],
            },
        }
        branch = event_projection.selector_branch_projection(
            [{"bankId": 7, "containerEvidence": [row]}], []
        )[0]
        self.assertFalse(branch["typedExact"])
        self.assertEqual(branch["typedExactStatus"], "unresolvedV150SelectorNoValuePackages")
        self.assertEqual(branch.get("packages", []), [])

    def test_selector_catalog_join_keeps_inferred_evidence_non_exact(self) -> None:
        catalog = [{
            "groupId": 9,
            "groupType": "switch",
            "semanticLabel": "Possible group",
            "semanticEvidence": "highConfidenceHashCorrelation",
            "values": [{
                "valueId": 4,
                "semanticName": "Possible",
                "semanticEvidence": "inferredValueVocabulary",
            }],
        }]
        row = {
            "objectType": 6,
            "childCount": 1,
            "switchMappingEvidence": {
                "parserStatus": "typedExactV150FlatPackages",
                "groupType": "switch",
                "groupId": 9,
                "defaultValueId": 4,
                "packages": [{"valueId": 4, "childIds": [1]}],
                "associations": [],
            },
        }
        branch = event_projection.selector_branch_projection(
            [{"bankId": 1, "containerEvidence": [row]}], [], catalog
        )[0]
        self.assertEqual(branch["ownershipEvidence"]["groupSemanticJoinStatus"], "inferredCatalogSemanticJoin")
        self.assertEqual(branch["packages"][0]["semanticJoinStatus"], "inferredCatalogSemanticJoin")

    def test_selector_branches_are_lazy_and_not_copied_to_event_summary(self) -> None:
        audio = {
            "eventNames": ["au_selector_fixture"],
            "events": [{
                "eventId": "au_selector_fixture",
                "eventHash": 123,
                "mediaId": 55,
                "src": "xinput.flac",
                "wwiseMediaEvidence": [{"bankId": 1, "soundObjectIds": [10]}],
            }],
            "eventEvidence": [{
                "eventId": "au_selector_fixture",
                "eventHash": 123,
                "bankId": 1,
                "bank": "fixture",
                "containerEvidence": [{
                    "objectType": 6,
                    "objectId": 700,
                    "childCount": 1,
                    "parserConfidence": "wwise150TypedReciprocalChildren",
                    "switchMappingEvidence": {
                        "parserStatus": "typedExactV150FlatPackages",
                        "groupType": "switch",
                        "groupId": 0x12345678,
                        "defaultValueId": 1,
                        "packages": [{"valueId": 1, "childIds": [10]}],
                        "associations": [],
                    },
                }],
            }],
        }
        rows, _, _ = event_projection.build_event_rows(audio, {})
        self.assertEqual(rows[0]["selectorBranchSchemaVersion"], 1)
        self.assertEqual(len(rows[0]["selectorBranches"]), 1)
        summary = event_summary.event_summary_row(rows[0], "event_details/00.json")
        self.assertNotIn("selectorBranches", summary)
        self.assertNotIn("selectorBranchSchemaVersion", summary)

    def test_compact_container_evidence_preserves_random_sequence_policy(self) -> None:
        rows = [
            {
                "objectType": 5,
                "edgeKind": "sequenceItem",
                "modeLabel": "sequence",
                "childCount": 3,
                "parserConfidence": "wwise150TypedReciprocalChildren",
                "selectorParserStatus": "typedExactV150PlaylistWeights",
                "randomModeLabel": "shuffle",
                "transitionModeLabel": "delay",
                "playlistItemCount": 3,
                "playlistMembershipStatus": "playlistWithRepeatedOwnedChildren",
                "duplicatePlaylistItemCount": 1,
                "ownedChildIdsNotInPlaylist": [99],
                "childrenOrderMatchesPlaylist": False,
                "nonDefaultWeightCount": 2,
                "uniformWeights": False,
                "avoidRepeatCount": 4,
                "loopCount": 2,
                "globalScope": True,
                "continuous": True,
                "resetPlaylistAtEachPlay": True,
            },
            {
                "objectType": 5,
                "edgeKind": "sequenceItem",
                "modeLabel": "sequence",
                "childCount": 2,
                "parserConfidence": "wwise150TypedReciprocalChildren",
                "selectorParserStatus": "unresolvedV150RandomSequenceTail",
                "selectorParserFailureReason": "unexpectedPlaylistTailLength",
            },
        ]

        compact = event_projection.compact_container_evidence(rows)

        self.assertEqual(len(compact), 1)
        policy = compact[0]
        self.assertEqual(policy["randomSequenceNodeCount"], 2)
        self.assertEqual(policy["typedRandomSequenceNodeCount"], 1)
        self.assertEqual(policy["unresolvedRandomSequenceNodeCount"], 1)
        self.assertEqual(policy["randomSequenceModes"], {"sequence": 1})
        self.assertEqual(policy["randomModes"], {"shuffle": 1})
        self.assertEqual(policy["randomTransitionModes"], {"delay": 1})
        self.assertEqual(policy["randomSequencePlaylistItemCount"], 3)
        self.assertEqual(
            policy["randomSequenceMembershipStatuses"],
            {"playlistWithRepeatedOwnedChildren": 1},
        )
        self.assertEqual(policy["randomSequenceDuplicatePlaylistItemCount"], 1)
        self.assertEqual(policy["randomSequenceOwnedChildNotInPlaylistCount"], 1)
        self.assertEqual(policy["playlistOrderDiffersFromChildrenCount"], 1)
        self.assertEqual(policy["nonDefaultWeightItemCount"], 2)
        self.assertEqual(policy["nonDefaultWeightNodeCount"], 1)
        self.assertEqual(policy["nonUniformWeightNodeCount"], 1)
        self.assertEqual(policy["nonDefaultAvoidRepeatNodeCount"], 1)
        self.assertEqual(policy["maxAvoidRepeatCount"], 4)
        self.assertEqual(policy["nonDefaultLoopNodeCount"], 1)
        self.assertEqual(policy["globalScopeRandomSequenceNodeCount"], 1)
        self.assertEqual(policy["continuousRandomSequenceNodeCount"], 1)
        self.assertEqual(policy["resetPlaylistNodeCount"], 1)
        self.assertNotIn("playlistItems", policy)

    def test_compact_container_evidence_distinguishes_layer_curves_and_proof(self) -> None:
        rows = [
            {
                "objectType": 9,
                "edgeKind": "layerChild",
                "childCount": 3,
                "parserConfidence": "reciprocalParentExact",
                "layerTailEvidence": {
                    "layerTailParserStatus": "typedExactV150LayerTail",
                    "layerAssignmentStatus": "nonEmptyCurves",
                    "layerCount": 1,
                    "initialRtpcCurveCount": 1,
                    "associationCount": 3,
                    "curvePointCount": 9,
                    "continuousValidation": True,
                    "associationChildIdsOutsideChildren": [],
                    "layers": [{
                        "rtpcId": 0x12345678,
                        "rtpcTypeLabel": "gameParameter",
                    }],
                },
            },
            {
                "objectType": 9,
                "edgeKind": "layerChild",
                "childCount": 2,
                "parserConfidence": "typedExactV150CandidateWithoutParentProof",
                "layerTailEvidence": {
                    "layerTailParserStatus": "typedExactV150LayerTail",
                    "layerAssignmentStatus": "zeroLayerAssignments",
                    "layerCount": 0,
                    "initialRtpcCurveCount": 0,
                    "associationCount": 0,
                    "curvePointCount": 0,
                    "continuousValidation": False,
                    "associationChildIdsOutsideChildren": [],
                    "layers": [],
                },
            },
        ]

        compact = event_projection.compact_container_evidence(rows)

        self.assertEqual(len(compact), 1)
        layer = compact[0]
        self.assertEqual(layer["layerNodeCount"], 2)
        self.assertEqual(layer["typedLayerNodeCount"], 2)
        self.assertEqual(layer["layerDefinitionCount"], 1)
        self.assertEqual(layer["layerInitialRtpcCurveCount"], 1)
        self.assertEqual(layer["layerAssociationCount"], 3)
        self.assertEqual(layer["layerCurvePointCount"], 9)
        self.assertEqual(layer["continuousLayerNodeCount"], 1)
        self.assertEqual(layer["layerRtpcIdsHex"], ["0x12345678"])
        self.assertEqual(layer["layerRtpcTypes"], {"gameParameter": 1})
        self.assertEqual(
            layer["layerAssignmentStatuses"],
            {"nonEmptyCurves": 1, "zeroLayerAssignments": 1},
        )
        self.assertEqual(
            layer["layerProofStatuses"],
            {
                "reciprocalParentExact": 1,
                "typedExactV150CandidateWithoutParentProof": 1,
            },
        )
        self.assertNotIn("layers", layer)

    def test_event_categories_preserve_unknowns(self) -> None:
        self.assertEqual(event_projection.event_category("au_sfx_test"), "sfx")
        self.assertEqual(event_projection.event_category("au_chr_test_attack"), "sfx")
        self.assertEqual(event_projection.event_category("au_eny_test_hit"), "sfx")
        self.assertEqual(event_projection.event_category("au_music_test"), "music")
        self.assertEqual(event_projection.event_category("au_amb_wind"), "ambience")
        self.assertEqual(event_projection.event_category("au_rtpc_speed"), "control")
        self.assertEqual(event_projection.event_category("au_vibration_test"), "control")
        self.assertEqual(event_projection.event_category(":au_music_test"), "music")
        self.assertEqual(event_projection.event_category("au_ul_popup_close"), "ui")
        self.assertEqual(event_projection.event_category("player_fol_cloth_fallover"), "sfx")
        self.assertEqual(event_projection.event_category("eny_0125_skill_01_shoot"), "sfx")
        self.assertEqual(event_projection.event_category("a_actor_camille_ui_overview_start"), "ui")
        self.assertEqual(event_projection.event_category("Play_au_ui_button_confirm"), "ui")
        self.assertEqual(event_projection.event_category("levelseq_map02_audio"), "cue")
        self.assertEqual(event_projection.event_category("int_loading_portal_idle"), "sfx")
        self.assertEqual(event_projection.event_category("unproven_name"), "unknown")

        self.assertEqual(
            event_projection.event_category_with_evidence("Play_au_ui_button_confirm"),
            ("ui", "authoredPlayAliasNamePattern"),
        )

    def test_audio_dialog_custom_event_hash_is_control_context(self) -> None:
        event_hash = 0x35B925DA
        rows, _, _ = event_projection.build_event_rows(
            {
                "eventNames": [],
                "events": [],
                "eventEvidence": [],
            },
            {
                identifiers.event_hash_context_key(event_hash): [
                    {
                        "kind": "tableEventHash",
                        "table": "AudioDialogCustomEventTable",
                        "path": "dlg_fixture.preExitEvents[0]",
                    }
                ]
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "hashed-event:0x35b925da")
        self.assertEqual(rows[0]["category"], "control")
        self.assertEqual(
            rows[0]["categoryEvidence"],
            "exactAudioDialogLifecycleEventField",
        )

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
        interact_audio = specs[
            "Beyond.Gameplay.Core.CharInteractPerform.AudioEventActData"
        ]
        interact_runtime = specs[
            "Beyond.Gameplay.Core.CharInteractPerform.AudioEventAction"
        ]
        self.assertEqual(interact_audio["layer"], "character_interaction_audio")
        self.assertEqual(interact_audio["serializedLayout"]["unionTag"], 2)
        self.assertEqual(interact_audio["serializedLayout"]["memberCount"], 15)
        self.assertIn("audioEvent", interact_audio["fields"])
        self.assertIn("OnPlay", interact_runtime["methods"])
        self.assertEqual(interact_runtime["runtimeExecutionStatus"], "runtimeNotObserved")
        physics = specs["Beyond.Gameplay.Core.PhysicsAudioComponentData"]
        self.assertEqual(physics["layer"], "physics_audio")
        self.assertEqual(len(physics["fields"]), 21)
        self.assertIn("<onStartMoveAudioEvent>k__BackingField", physics["fields"])
        self.assertIn("<angularVelocitySqrRtpc>k__BackingField", physics["fields"])
        self.assertIn("ApplyProperties", physics["methods"])
        model_view_specs = [
            row for row in audio_semantics.RUNTIME_SYSTEM_SPECS
            if row["layer"] == "model_view_state_audio"
        ]
        self.assertEqual(len(model_view_specs), 4)
        self.assertEqual(
            [row["serializedLayout"]["unionTag"] for row in model_view_specs],
            [1, 2, 3, 4],
        )
        self.assertEqual(
            [row["serializedLayout"]["memberCount"] for row in model_view_specs],
            [14, 14, 13, 12],
        )
        self.assertTrue(all(row["runtimeExecutionStatus"] == "notObserved" for row in model_view_specs))
        self.assertTrue(all(
            [anchor["role"] for anchor in row["nativeAnchors"]] == ["Deserialize", "Execute"]
            for row in model_view_specs
        ))
        state_condition = specs[
            "Beyond.Gameplay.Actions.LevelEvent.OnAudioStateChanged"
        ]
        mask_condition = specs[
            "Beyond.Gameplay.Audio.AudioStateSystem+MaskCondition"
        ]
        beat_condition = specs[
            "Beyond.Gameplay.Actions.LevelEvent.OnMusicBeatEvent"
        ]
        callback_type = specs["Beyond.Audio.AudioCallbackType"]
        self.assertEqual(state_condition["serializedLayout"]["unionTag"], 0x0048)
        self.assertEqual(state_condition["serializedLayout"]["eventKey"], 148)
        self.assertEqual(state_condition["serializedLayout"]["authoredOccurrenceCount"], 0)
        self.assertEqual(len(state_condition["fields"]), 4)
        self.assertIn("IsMet", mask_condition["methods"])
        self.assertEqual(beat_condition["serializedLayout"]["unionTag"], 0x007A)
        self.assertEqual(beat_condition["serializedLayout"]["eventKey"], 44)
        self.assertEqual(beat_condition["serializedLayout"]["authoredOccurrenceCount"], 0)
        self.assertTrue(callback_type["enumValues"])
        self.assertEqual(len(audio_semantics.LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS), 2)
        self.assertEqual(
            sum(
                row["authoredOccurrenceCount"]
                for row in audio_semantics.LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
            ),
            0,
        )
        self.assertTrue(all(
            row["playbackRequestStatus"] == "notApplicableTriggerInput"
            for row in audio_semantics.LEVEL_EVENT_AUDIO_CONDITION_DEFINITIONS
        ))

    def test_external_source_event_identity_audit_separates_route_and_media_keys(self) -> None:
        audit = audio_semantics.external_source.collect_event_identity_audit(
            {
                "wwiseEventInventory": [
                    {
                        "eventHash": 0x100,
                        "eventId": "hashed-event:0x00000100",
                        "nonMediaSourceEvidence": [
                            {"sourceKind": "externalSourceCodec", "sourceId": 0x24DB9834},
                        ],
                    },
                    {
                        "eventHash": 0x200,
                        "eventId": "au_voice_route",
                        "nonMediaSourceEvidence": [
                            {"sourceKind": "externalSourceCodec", "sourceId": 0x24DB9834},
                        ],
                    },
                    {
                        "eventHash": 0x300,
                        "eventId": "au_dialog_media_identity",
                        "nonMediaSourceEvidence": [],
                    },
                ],
                "voiceTableWwiseEventAliases": [
                    {"eventHash": 0x100},
                    {"eventHash": 0x200},
                ],
                "audioDialogWwiseEventAliases": [{"eventHash": 0x300}],
            },
            language="CN",
        )
        self.assertEqual(audit["status"], "complete")
        self.assertEqual(audit["externalSourceEventCount"], 2)
        self.assertEqual(audit["externalSourceReferenceCount"], 2)
        self.assertEqual(audit["externalEventsWithVoiceTableAlias"], 2)
        self.assertEqual(audit["externalEventsWithAudioDialogAlias"], 0)
        self.assertEqual(audit["externalEventsWithoutVoiceTableAlias"], 0)
        self.assertEqual(audit["externalEventsWithDecodedMedia"], 0)
        self.assertEqual(audit["externalEventsWithMediaRelations"], 0)
        self.assertEqual(audit["externalEventsWithZeroResolvedMedia"], 2)
        self.assertEqual(audit["externalSourceIds"], [{
            "sourceId": 618371124,
            "sourceIdHex": "0x24db9834",
            "referenceCount": 2,
        }])
        self.assertIn("per-request media identity", audit["evidenceBoundary"])

    def test_external_source_audit_recovers_override_route_path_candidates(self) -> None:
        event_name = "vo_fixture_external_route"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for layer, row_id, authored_path in (
                ("StreamingAssets", "1", "v1d0/Narrating/fixture_a.wem"),
                ("Persistent", "2", "v1d0/Narrating/fixture_b.wem"),
            ):
                table = root / "structured" / layer / "Table"
                table.mkdir(parents=True, exist_ok=True)
                (table / "AudioDialog.json").write_text(
                    json.dumps({
                        row_id: {
                            "overrideWwiseEvent": event_name,
                            "path": authored_path,
                        },
                    }),
                    encoding="utf-8",
                )
            audit = audio_semantics.external_source.collect_event_identity_audit(
                {
                    "wwiseEventInventory": [{
                        "eventHash": event_hash,
                        "eventId": event_name,
                        "nonMediaSourceEvidence": [{
                            "sourceKind": "externalSourceCodec",
                            "sourceId": 0x24DB9834,
                        }],
                    }],
                    "entries": [{
                        "id": "fixture_a",
                        "audioDialogPath": "v1d0/Narrating/fixture_a.wem",
                    }],
                },
                language="CN",
                export_root=root,
            )
        self.assertEqual(audit["schemaVersion"], 5)
        self.assertEqual(audit["externalOverridePathAuditStatus"], "complete")
        self.assertEqual(audit["externalEventsWithOverridePathCandidates"], 1)
        self.assertEqual(audit["externalEventsWithUniqueOverridePath"], 0)
        self.assertEqual(audit["externalOverridePathRowCount"], 2)
        self.assertEqual(audit["externalOverridePathCandidateCount"], 2)
        self.assertEqual(audit["externalOverridePathCandidatesWithDecodedMedia"], 1)
        mapping = audit["externalOverridePathMappings"][0]
        self.assertEqual(mapping["overrideWwiseEvent"], event_name)
        self.assertEqual(mapping["pathCount"], 2)
        self.assertEqual(mapping["decodedPathCount"], 1)
        self.assertEqual(mapping["decodedAudioIdCount"], 1)
        self.assertEqual(mapping["decodedAudioIdSamples"], ["fixture_a"])

    def test_external_source_audit_recovers_channel_route_path_candidates(self) -> None:
        event_name = "vo_fixture_channel_route"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            table = root / "structured" / "StreamingAssets" / "Table"
            table.mkdir(parents=True, exist_ok=True)
            (table / "AudioDialog.json").write_text(
                json.dumps({
                    "1": {
                        "speakerChannel": "fixture_channel",
                        "path": "v1d0/Narrating/channel_a.wem",
                    },
                    "2": {
                        "speakerChannel": "other_channel",
                        "path": "v1d0/Narrating/channel_b.wem",
                    },
                }),
                encoding="utf-8",
            )
            (table / "AudioDialogChannel.json").write_text(
                json.dumps({
                    "fixture_channel": {"narratingWwiseEvent": event_name},
                }),
                encoding="utf-8",
            )
            audit = audio_semantics.external_source.collect_event_identity_audit(
                {
                    "wwiseEventInventory": [{
                        "eventHash": event_hash,
                        "eventId": event_name,
                        "nonMediaSourceEvidence": [{
                            "sourceKind": "externalSourceCodec",
                            "sourceId": 0x24DB9834,
                        }],
                    }],
                    "entries": [{
                        "id": "channel_a",
                        "audioDialogPath": "v1d0/Narrating/channel_a.wem",
                    }],
                },
                language="CN",
                export_root=root,
            )
        self.assertEqual(audit["externalChannelPathAuditStatus"], "complete")
        self.assertEqual(audit["externalEventsWithChannelPathCandidates"], 1)
        self.assertEqual(audit["externalChannelPathRowCount"], 1)
        self.assertEqual(audit["externalChannelPathCandidateCount"], 1)
        self.assertEqual(audit["externalChannelPathUniqueCandidateCount"], 1)
        self.assertEqual(audit["externalChannelPathCandidatesWithDecodedMedia"], 1)
        mapping = audit["externalChannelPathMappings"][0]
        self.assertEqual(mapping["fields"], ["narratingWwiseEvent"])
        self.assertEqual(mapping["channelSamples"], ["fixture_channel"])

    def test_external_source_audit_fails_closed_on_malformed_structured_table(self) -> None:
        event_name = "vo_fixture_malformed_table"
        event_hash = identifiers.audio_hash_generator_compute(event_name)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            table = root / "structured" / "StreamingAssets" / "Table"
            table.mkdir(parents=True, exist_ok=True)
            (table / "AudioDialog.json").write_text("{not-json", encoding="utf-8")
            (table / "AudioDialogChannel.json").write_text(
                json.dumps({"fixture_channel": {"narratingWwiseEvent": event_name}}),
                encoding="utf-8",
            )
            audit = audio_semantics.external_source.collect_event_identity_audit(
                {
                    "wwiseEventInventory": [{
                        "eventHash": event_hash,
                        "eventId": event_name,
                        "nonMediaSourceEvidence": [{
                            "sourceKind": "externalSourceCodec",
                            "sourceId": 0x24DB9834,
                        }],
                    }],
                },
                language="CN",
                export_root=root,
            )
        self.assertEqual(audit["externalOverridePathAuditStatus"], "unavailable")
        self.assertEqual(audit["externalChannelPathAuditStatus"], "unavailable")
        self.assertEqual(audit["externalOverridePathMappings"], [])
        self.assertEqual(audit["externalChannelPathMappings"], [])

    def test_external_source_audit_deduplicates_inventory_occurrences(self) -> None:
        audit = audio_semantics.external_source.collect_event_identity_audit(
            {
                "wwiseEventInventory": [
                    {
                        "eventHash": 0x400,
                        "eventId": "au_duplicate_route",
                        "nonMediaSourceEvidence": [{"sourceKind": "externalSourceCodec"}],
                        "mediaIds": [9001],
                        "mediaRelationTypes": ["ordinaryCodecMedia"],
                    },
                    {
                        "eventHash": 0x400,
                        "eventId": "au_duplicate_route",
                        "nonMediaSourceEvidence": [{"sourceKind": "externalSourceCodec"}],
                        "mediaRelationTypes": ["ordinaryCodecMedia"],
                    },
                    {
                        "eventHash": 0x500,
                        "eventId": "au_conflicting_route_a",
                        "nonMediaSourceEvidence": [{"sourceKind": "externalSourceCodec"}],
                    },
                    {
                        "eventHash": 0x600,
                        "eventId": "au_explicit_external_media",
                        "nonMediaSourceEvidence": [{"sourceKind": "externalSourceCodec"}],
                        "externalMediaIds": [1234],
                        "externalMediaRelationTypes": ["externalSourceMedia"],
                    },
                    {
                        "eventHash": 0x500,
                        "eventId": "au_conflicting_route_b",
                        "nonMediaSourceEvidence": [{"sourceKind": "externalSourceCodec"}],
                    },
                ],
            },
            language="CN",
        )
        self.assertEqual(audit["externalSourceEventCount"], 3)
        self.assertEqual(audit["externalSourceReferenceCount"], 5)
        self.assertEqual(audit["externalEventsWithDecodedMedia"], 1)
        self.assertEqual(audit["externalEventsWithMediaRelations"], 1)
        self.assertEqual(audit["namedExternalEventCount"], 2)
        self.assertEqual(audit["hashedExternalEventCount"], 1)

    def test_runtime_model_preserves_exact_native_playback_call_chains(self) -> None:
        specs = {row["type"]: row for row in audio_semantics.RUNTIME_SYSTEM_SPECS}
        adapter = specs["Beyond.Audio.AudioAdapter"]
        animator = specs["Beyond.Gameplay.View.Animation.AnimatorMono"]
        skill = specs["Beyond.Gameplay.Core.PlaySoundAction"]
        levelscript = specs["Beyond.Gameplay.Actions.GameAction"]
        music = specs["Beyond.Gameplay.Audio.AudioMusicSystem"]
        wwise = specs["AkSoundEngine"]
        asset_cache = specs["Beyond.Audio.AudioAssetCache"]
        asset_helper = specs["Beyond.Audio.AudioAssetHelper"]
        audio_manager = specs["Beyond.Gameplay.Audio.AudioManager"]
        audio_state_system = specs["Beyond.Gameplay.Audio.AudioStateSystem"]
        callback_manager = specs["AkCallbackManager"]
        factory_bridge = specs["Beyond.Gameplay.Audio.AudioRemoteFactoryBridge"]
        gamepad_manager = specs["Beyond.Gameplay.Audio.AudioGamePadManager"]
        vfs_loader = specs["Beyond.Audio.AudioVFSLoader"]
        bank_manager = specs["Beyond.Audio.AudioBankManager"]

        adapter_chains = {row["id"]: row for row in adapter["nativeCallChains"]}
        post = adapter_chains["adapterPostEventToWwise"]
        alternate = post["alternateEntryPoints"]
        self.assertEqual(len(alternate), 1)
        self.assertEqual(alternate[0]["role"], "stringCallbackEntry")
        self.assertEqual(alternate[0]["virtualAddress"], "0x183288d10")
        self.assertNotIn("methodIndex", alternate[0])
        self.assertIn("AudioHashGenerator.Compute", alternate[0]["relation"])
        self.assertIn("tail-jumps AudioAdapter._PostEvent", alternate[0]["relation"])
        self.assertIn("notInCodegenOrGenericMethodPointerTables", alternate[0]["evidence"])
        self.assertEqual(
            [row["methodIndex"] for row in post["stages"]],
            [
                479923, 480010, 480201, 480175, 446458, 480211,
                446489, 480212, 480213, 480007, 446377, 446952,
                446954, 480008, 480176,
            ],
        )
        wwise_post = next(row for row in post["stages"] if row["role"] == "wwise")
        adapter_post = next(row for row in post["stages"] if row["role"] == "post")
        self.assertEqual(wwise_post["type"], "AkSoundEngine")
        self.assertIn("0x18f361158", adapter_post["relation"])
        self.assertEqual(post["stages"][-1]["method"], "DeactivateAsset")
        self.assertEqual(
            [row["id"] for row in post["branches"]],
            ["activatedCache", "eventBankMiss", "callbackPayloadCapabilities"],
        )
        self.assertEqual(asset_cache["nativeCallChains"][0]["id"], post["id"])
        self.assertEqual(asset_helper["nativeCallChains"][0]["id"], post["id"])
        self.assertIn("s_waitingCallbacks", asset_helper["fields"])
        self.assertEqual(callback_manager["nativeCallChains"][0]["id"], post["id"])
        self.assertEqual(callback_manager["runtimeExecutionStatus"], "callbackCapabilityExactPayloadsNotObserved")
        self.assertIn("UpdateNodeMode", factory_bridge["methods"])
        self.assertEqual(factory_bridge["nativeAnchors"][0]["groupId"], 0x7ACDACAF)
        self.assertEqual(gamepad_manager["nativeAnchors"][0]["valueId"], 0x1A9FC91F)
        self.assertEqual(gamepad_manager["nativeAnchors"][1]["valueId"], 0x1B9ABDB1)
        self.assertEqual(gamepad_manager["nativeAnchors"][2]["method"], "AddOutput")
        self.assertEqual(
            gamepad_manager["nativeAnchors"][2]["downstreamVirtualAddress"],
            "0x1853cf1a8",
        )
        self.assertIn("m_wwiseMotionOutputDeviceId", gamepad_manager["fields"])
        callback_roles = {row["role"] for row in callback_manager["nativeAnchors"]}
        self.assertTrue({"eventId", "durationMediaId", "playlistSelection", "sourceChange"} <= callback_roles)
        external = adapter_chains["externalSourcePostToWwise"]
        external_alternates = external["alternateEntryPoints"]
        self.assertEqual(
            [row["virtualAddress"] for row in external_alternates],
            ["0x183abef40", "0x183abe750", "0x1800285d0"],
        )
        self.assertIn("PostEventExternal", external_alternates[0]["relation"])
        self.assertIn("voiceData.data (+0x60)", external_alternates[0]["relation"])
        self.assertIn("wwiseEvent (+0x20)", external_alternates[0]["relation"])
        self.assertIn("codec (+0x68)", external_alternates[0]["relation"])
        self.assertIn("rcx=resolved externalSourceKey", external_alternates[0]["relation"])
        self.assertIn("r9d=handleId", external_alternates[0]["relation"])
        self.assertIn("stack +0x20 carries codec", external_alternates[0]["relation"])
        self.assertIn("VoiceData.codec at serialized +0x14", external_alternates[0]["relation"])
        self.assertIn("copies it raw", external_alternates[0]["relation"])
        self.assertIn("externalCookie 0x24db9834", external_alternates[0]["relation"])
        self.assertIn("callback type 0x100001", external_alternates[0]["relation"])
        self.assertIn("managed PostEventExternal result", external_alternates[0]["relation"])
        self.assertIn("native PostEvent result and external-manager registration serial are retained separately", external_alternates[0]["relation"])
        external_cookie_join = next(
            row
            for row in external["stages"]
            if row["role"] == "externalSourceCookieBankJoinAudit"
        )
        managed_return = next(
            row for row in external["stages"] if row["role"] == "prepareExternal"
        )
        self.assertIn("_GetInternalPlayingId at 0x18328a810", managed_return["relation"])
        self.assertIn("native AkSoundEngine.PostEvent at 0x183abed90", managed_return["relation"])
        self.assertIn("stores that result separately in ebx", managed_return["relation"])
        self.assertIn("function returns edi", managed_return["relation"])
        self.assertIn("not the native c3990 registration serial/manager key", managed_return["relation"])
        self.assertEqual(external_cookie_join["virtualAddress"], "0x24db9834")
        self.assertIn("1,712 exact Wwise External Source source records", external_cookie_join["relation"])
        self.assertIn("plugin 0x00080001", external_cookie_join["relation"])
        self.assertIn("sourceId 618371124 = 0x24db9834", external_cookie_join["relation"])
        self.assertIn("0x183abefd9", external_cookie_join["relation"])
        self.assertIn("callback-family selection boundary", external_cookie_join["relation"])
        self.assertIn("per-request externalSourceKey path", external_cookie_join["relation"])
        hirc_path_separation = next(
            row
            for row in external["stages"]
            if row["role"] == "externalSourceHircPathSeparationAudit"
        )
        self.assertEqual(hirc_path_separation["virtualAddress"], "0x18003a5b0")
        self.assertIn("1,712 exact externalSourceCodec records", hirc_path_separation["relation"])
        self.assertIn("1,711 serialized paths", hirc_path_separation["relation"])
        self.assertIn("one is event -> action -> ordinary HIRC type-5", hirc_path_separation["relation"])
        self.assertIn("None is owned by HIRC type-13", hirc_path_separation["relation"])
        self.assertIn("cannot be used as a static key mapping", hirc_path_separation["relation"])
        native_cookie_absence = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeExternalCookieLiteralAbsenceAudit"
        )
        self.assertEqual(native_cookie_absence["virtualAddress"], "0x180344988")
        self.assertIn("zero occurrences", native_cookie_absence["relation"])
        self.assertIn("little-endian dword 0x24db9834", native_cookie_absence["relation"])
        self.assertIn("entry +0x58", native_cookie_absence["relation"])
        self.assertIn("entry +0x4c", native_cookie_absence["relation"])
        self.assertIn("image-initial dword at serial slot 0x180344988 is 0x002f9238", native_cookie_absence["relation"])
        self.assertIn("unmodified first lock-xadd would generate 0x002f9239", native_cookie_absence["relation"])
        self.assertIn("runtime argument capture", native_cookie_absence["relation"])
        self.assertEqual(
            external_alternates[1]["role"],
            "voiceExternalSourceKeyResolution",
        )
        self.assertIn("externalSourceKey", external_alternates[1]["relation"])
        self.assertIn("voiceData.data (+0x60)", external_alternates[1]["relation"])
        self.assertIn("0x182f25040", external_alternates[1]["relation"])
        self.assertIn("template UTF-16 placeholder expansion", external_alternates[1]["relation"])
        self.assertIn("VoiceI18n metadata type", external_alternates[1]["relation"])
        self.assertIn("format {0}/{1}/{2}", external_alternates[1]["relation"])
        self.assertIn("Voice/<language>/<VoiceData.path>", external_alternates[1]["relation"])
        descriptor_alternate = external_alternates[2]
        self.assertIn("record +0x10", descriptor_alternate["relation"])
        self.assertIn("0x1800c3990", descriptor_alternate["relation"])
        self.assertIn("manager +0x38", descriptor_alternate["relation"])
        self.assertIn("sourceInfo +0x10 instance join remains unproven", descriptor_alternate["relation"])
        self.assertIn("does not itself read a file", external_alternates[1]["relation"])
        self.assertIn("VoiceI18n.GetVoicePath", external_alternates[1]["relation"])
        self.assertEqual(external_alternates[2]["role"], "nativeExternalDescriptor")
        self.assertIn("cExternals", external_alternates[2]["relation"])
        self.assertIn("duplicates szFile", external_alternates[2]["relation"])
        self.assertIn("0x18011bf00", external_alternates[2]["relation"])
        self.assertIn("copied external-descriptor allocation pointer at manager +0x38", external_alternates[2]["relation"])
        self.assertIn("noFileOpenCallsite", external_alternates[2]["evidence"])
        self.assertNotIn("methodIndex", external_alternates[0])
        self.assertEqual(
            [row["methodIndex"] for row in external["stages"] if "methodIndex" in row],
            [479931, 480011, 444124, 444128, 444126, 446969, 446376, 446952, 480009, 39041, 39052],
        )
        self.assertIn(
            "0x18f361150",
            next(row for row in external["stages"] if row["role"] == "wwise")["relation"],
        )
        external_package = next(row for row in external["stages"] if row["role"] == "externalCallbackPackage")
        self.assertEqual(external_package["methodIndex"], 446969)
        self.assertEqual(external_package["virtualAddress"], "0x18328ca20")
        self.assertIn("mapping object", external_package["relation"])
        external_wwise = next(row for row in external["stages"] if row["role"] == "wwise")
        self.assertIn("cExternals=1", external_wwise["relation"])
        self.assertIn("mappingCookie", external_wwise["relation"])
        external_file = next(row for row in external["stages"] if row["role"] == "externalFile")
        self.assertIn("directly from the externalSourceKey argument", external_file["relation"])
        self.assertIn("managed key/path", external_file["relation"])
        self.assertIn("direct VoicePlayer key -> external-descriptor path identity", external_file["relation"])
        self.assertIn("native source-state key equals the registration serial", external_file["relation"])
        source_manager = next(row for row in external["stages"] if row["role"] == "nativeSourceManager")
        self.assertEqual(source_manager["virtualAddress"], "0x1800e1320")
        self.assertIn("+0x4c", source_manager["relation"])
        self.assertIn("+0x50", source_manager["relation"])
        self.assertIn("+0x68", source_manager["relation"])
        self.assertIn("internally generated registration serial written at 0x1800c3990 record +0xc", source_manager["relation"])
        self.assertIn("resolves the exact hash-table entry by +0x4c", source_manager["relation"])
        self.assertIn("shared entry pointers can prove one manager node", source_manager["relation"])
        self.assertIn("nativeSourceManagerJoinAudit below", source_manager["relation"])
        self.assertIn("nativeSourceDescriptorManagerRetentionAudit below", source_manager["relation"])
        descriptor_retention = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceDescriptorManagerRetentionAudit"
        )
        self.assertEqual(descriptor_retention["virtualAddress"], "0x1800c38b0")
        self.assertIn("0x1800c08d0", descriptor_retention["relation"])
        self.assertIn("local carrier at [rsp+0x50]", descriptor_retention["relation"])
        self.assertIn("c3990 stack argument 6", descriptor_retention["relation"])
        self.assertIn("registration record +0x14/+0x24", descriptor_retention["relation"])
        self.assertIn("manager entry +0x38", descriptor_retention["relation"])
        self.assertIn("copied external-descriptor allocation pointer", descriptor_retention["relation"])
        self.assertIn("not proof that manager +0x38 is a UTF-16 string", descriptor_retention["relation"])
        cookie_separation = next(
            row
            for row in external["stages"]
            if row["role"] == "nativePostEventCookieFieldSeparationAudit"
        )
        self.assertEqual(cookie_separation["virtualAddress"], "0x1800285d0")
        self.assertIn("pCookie, cExternals, pExternalSources", cookie_separation["relation"])
        self.assertIn("stack argument 5", cookie_separation["relation"])
        self.assertIn("manager entry +0x58", cookie_separation["relation"])
        self.assertIn("AkExternalSourceInfo iExternalSrcCookie/szFile/codec", cookie_separation["relation"])
        self.assertIn("manager +0x4c", cookie_separation["relation"])
        self.assertIn("must not be equated", cookie_separation["relation"])
        descriptor_lifetime = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceDescriptorManagerLifetimeAudit"
        )
        self.assertEqual(descriptor_lifetime["virtualAddress"], "0x1800e1770")
        self.assertIn("0x1800e2a5e", descriptor_lifetime["relation"])
        self.assertIn("0x1800e2a8e", descriptor_lifetime["relation"])
        self.assertIn("reads manager entry +0x38 only", descriptor_lifetime["relation"])
        self.assertIn("refcount release 0x1800c5f60", descriptor_lifetime["relation"])
        self.assertIn("not a direct sourceInfo/provider input", descriptor_lifetime["relation"])
        serial_audit = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceRegistrationSerialAudit"
        )
        self.assertEqual(serial_audit["virtualAddress"], "0x1800e1320")
        self.assertIn("two wrapper families", serial_audit["relation"])
        self.assertIn("0x1800e130b", serial_audit["relation"])
        self.assertIn("0x1800e14d2", serial_audit["relation"])
        self.assertIn("0x1800c3516", serial_audit["relation"])
        self.assertIn("0x1800c4472", serial_audit["relation"])
        self.assertIn("does not prove that the later source-state key equals that serial", serial_audit["relation"])
        source_lookup = next(row for row in external["stages"] if row["role"] == "nativeSourceLookup")
        self.assertEqual(source_lookup["virtualAddress"], "0x1800e2820")
        self.assertIn("0x1800e19a0", source_lookup["relation"])
        self.assertIn("operation 0x10", source_lookup["relation"])
        self.assertIn("0x1800e28d0", source_lookup["relation"])
        self.assertIn("key % manager bucket count", source_lookup["relation"])
        self.assertIn("no additional hash transform", source_lookup["relation"])
        callback_branches = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceCallbackBranches"
        )
        self.assertEqual(callback_branches["virtualAddress"], "0x1800e2820")
        self.assertIn("object +0x60 bit 0x10", callback_branches["relation"])
        self.assertIn("object +0x60 bit 0x20", callback_branches["relation"])
        self.assertIn("operation 0x10", callback_branches["relation"])
        self.assertIn("operation 0x20", callback_branches["relation"])
        self.assertIn("manager +0x48", callback_branches["relation"])
        self.assertIn("0x1800030cf", callback_branches["relation"])
        self.assertIn("0x180003430", callback_branches["relation"])
        self.assertIn("does not identify the managed path", callback_branches["relation"])
        extended_callback_branches = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceExtendedCallbackBranches"
        )
        self.assertEqual(extended_callback_branches["virtualAddress"], "0x1800e25f0")
        self.assertIn("operation 0x80", extended_callback_branches["relation"])
        self.assertIn("operation 0x2000", extended_callback_branches["relation"])
        self.assertIn("0x1800347af", extended_callback_branches["relation"])
        self.assertIn("0x18003578f", extended_callback_branches["relation"])
        self.assertIn("0x18004388b", extended_callback_branches["relation"])
        self.assertIn("0x180003169", extended_callback_branches["relation"])
        self.assertIn("do not select a UTF-16 path", extended_callback_branches["relation"])
        source_media = next(row for row in external["stages"] if row["role"] == "nativeSourceMediaLookup")
        self.assertEqual(source_media["virtualAddress"], "0x18010df60")
        self.assertIn("source-state +0", source_media["relation"])
        self.assertIn("exact numeric equality", source_media["relation"])
        self.assertIn("0x1800c3990 record +0xc serial", source_media["relation"])
        self.assertIn("stack +0x40", source_media["relation"])
        self.assertIn("object +0x58", source_media["relation"])
        self.assertIn("object +0x28", source_media["relation"])
        self.assertIn("managed UTF-16 path", source_media["relation"])
        self.assertIn("0x1801443e0", source_media["relation"])
        self.assertIn("context +0x268", source_media["relation"])
        self.assertIn("0x180189a59", source_media["relation"])
        self.assertIn("temporary dword at its local +0x10", source_media["relation"])
        self.assertIn("separate mixer callers", source_media["relation"])
        self.assertIn("0x180189826", source_media["relation"])
        self.assertIn("0x180188ed0", source_media["relation"])
        self.assertIn("operation 0x8", source_media["relation"])
        self.assertIn("0x180002f31", source_media["relation"])
        self.assertIn("0x180003430", source_media["relation"])
        self.assertIn("no direct call-rel32 or field-dataflow edge proves", source_media["relation"])
        self.assertIn("0x180034e4f", source_media["relation"])
        self.assertIn("upstream record +0x14", source_media["relation"])
        self.assertIn("0x1800365f0", source_media["relation"])
        self.assertIn("field-dataflow edge", source_media["relation"])
        source_key_callsites = next(
            row for row in external["stages"] if row["role"] == "nativeSourceKeyCallsites"
        )
        self.assertEqual(source_key_callsites["virtualAddress"], "0x18018a5a0")
        self.assertIn("0x1801451ea", source_key_callsites["relation"])
        self.assertIn("[r12+0x268]", source_key_callsites["relation"])
        self.assertIn("0x180144c1f", source_key_callsites["relation"])
        self.assertIn("r12+0x18", source_key_callsites["relation"])
        self.assertIn("no key", source_key_callsites["relation"])
        source_key_writes = next(
            row for row in external["stages"] if row["role"] == "nativeSourceKeyWriteAudit"
        )
        self.assertEqual(source_key_writes["virtualAddress"], "0x1800d2055")
        self.assertIn("direct-offset/overlap audit", source_key_writes["relation"])
        self.assertIn("0x18008668c", source_key_writes["relation"])
        self.assertIn("0x1800ac3bf", source_key_writes["relation"])
        self.assertIn("0x1800ae238", source_key_writes["relation"])
        self.assertIn("0x18012d0fe", source_key_writes["relation"])
        self.assertIn("0x18022ad9c", source_key_writes["relation"])
        self.assertIn("0x18022b3f5", source_key_writes["relation"])
        self.assertIn("0x18022b83a", source_key_writes["relation"])
        self.assertIn("global 0x180344988", source_key_writes["relation"])
        self.assertIn("0x1800c3414", source_key_writes["relation"])
        self.assertIn("0x1800c443d", source_key_writes["relation"])
        self.assertIn("no direct RIP-relative read", source_key_writes["relation"])
        self.assertIn("No source-state setter copies the serial", source_key_writes["relation"])
        source_key_config = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceKeyConfigCallsiteAudit"
        )
        self.assertEqual(source_key_config["virtualAddress"], "0x180034db0")
        self.assertIn("one direct callsite", source_key_config["relation"])
        self.assertIn("0x18003def1", source_key_config["relation"])
        self.assertIn("0x180040350", source_key_config["relation"])
        self.assertIn("parent B +0x18", source_key_config["relation"])
        self.assertIn("parent B +0x2c", source_key_config["relation"])
        self.assertIn("0x1800404f0", source_key_config["relation"])
        self.assertIn("0x18003e35b", source_key_config["relation"])
        self.assertIn("source vtable +0x138", source_key_config["relation"])
        self.assertIn("stack argument 6", source_key_config["relation"])
        self.assertIn("config +0x34", source_key_config["relation"])
        self.assertIn("source-state +0x268", source_key_config["relation"])
        self.assertIn("child-source branch", source_key_config["relation"])
        self.assertIn("0x18003779e", source_key_config["relation"])
        self.assertIn("0x180034733", source_key_config["relation"])
        self.assertIn("same-record value identity", source_key_config["relation"])
        self.assertIn("not statically aliased", source_key_config["relation"])
        source_metadata = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceStateMetadataProvenanceAudit"
        )
        self.assertEqual(source_metadata["virtualAddress"], "0x1800d1f90")
        self.assertIn("r9 directly to source-state +0x288", source_metadata["relation"])
        self.assertIn("0x18003def1", source_metadata["relation"])
        self.assertIn("0x180046580", source_metadata["relation"])
        self.assertIn("Alternate callsite", source_metadata["relation"])
        self.assertIn("0x1800fca27", source_metadata["relation"])
        self.assertIn("incoming r9 to initializer rdx/config", source_metadata["relation"])
        self.assertIn("0x18018dbc5", source_metadata["relation"])
        self.assertIn("three distinct register-source families", source_metadata["relation"])
        self.assertIn("manager entry +0x38", source_metadata["relation"])
        self.assertIn("no direct call or field-dataflow edge", source_metadata["relation"])
        self.assertIn("PCM delivery remain unobserved", source_metadata["relation"])
        source_info_selection = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceInfoInternalSelectionAudit"
        )
        self.assertEqual(source_info_selection["virtualAddress"], "0x1800d2ed0")
        self.assertIn("sourceInfo dword +0", source_info_selection["relation"])
        self.assertIn("0x1800f5030", source_info_selection["relation"])
        self.assertIn("0x180344a20", source_info_selection["relation"])
        self.assertIn("entry +8", source_info_selection["relation"])
        self.assertIn("0x1800f9780", source_info_selection["relation"])
        self.assertIn("0x20-byte local descriptor", source_info_selection["relation"])
        self.assertIn("candidate +8", source_info_selection["relation"])
        self.assertIn("candidate +0x10", source_info_selection["relation"])
        self.assertIn("0x180143de0", source_info_selection["relation"])
        self.assertIn("0x180104720", source_info_selection["relation"])
        self.assertIn("source +0x328", source_info_selection["relation"])
        self.assertIn("0x1803449f8", source_info_selection["relation"])
        self.assertIn("0x1803449d0", source_info_selection["relation"])
        self.assertIn("internal selection key", source_info_selection["relation"])
        self.assertIn("PCM delivery remain unobserved", source_info_selection["relation"])
        source_info_path = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceInfoPathWriterAudit"
        )
        self.assertEqual(source_info_path["virtualAddress"], "0x180104630")
        self.assertIn("one direct caller", source_info_path["relation"])
        self.assertIn("0x1800e037e", source_info_path["relation"])
        self.assertIn("incoming UTF-16 pointer r8", source_info_path["relation"])
        self.assertIn("0x1801044f0", source_info_path["relation"])
        self.assertIn("0x18026b7f8", source_info_path["relation"])
        self.assertIn("0x180263808", source_info_path["relation"])
        self.assertIn("direct-path branch", source_info_path["relation"])
        self.assertIn("alias branch", source_info_path["relation"])
        self.assertIn("exact copied-descriptor identity", source_info_path["relation"])
        source_info_parser = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceInfoSerializedParserAudit"
        )
        self.assertEqual(source_info_parser["virtualAddress"], "0x1800f5fc0")
        self.assertIn("0x180047120", source_info_parser["relation"])
        self.assertIn("0x180039a28", source_info_parser["relation"])
        self.assertIn("0x180039b35", source_info_parser["relation"])
        self.assertIn("virtual type value 6", source_info_parser["relation"])
        self.assertIn("output +8 as the map key", source_info_parser["relation"])
        self.assertIn("16-byte identity block", source_info_parser["relation"])
        self.assertIn("sourceId/cookie 0x24db9834", source_info_parser["relation"])
        self.assertIn("registration serial +0x4c", source_info_parser["relation"])
        self.assertIn("managed externalSourceKey", source_info_parser["relation"])
        source_info_owner = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceInfoHircOwnerAudit"
        )
        self.assertEqual(source_info_owner["virtualAddress"], "0x18003a5b0")
        self.assertIn("HIRC type byte", source_info_owner["relation"])
        self.assertIn("10 -> 0x180039e80", source_info_owner["relation"])
        self.assertIn("12 -> 0x180039b70", source_info_owner["relation"])
        self.assertIn("13 -> 0x1800397b0", source_info_owner["relation"])
        self.assertIn("0x180039a28", source_info_owner["relation"])
        self.assertIn("0x180039b35", source_info_owner["relation"])
        self.assertIn("Music Random Sequence Container", source_info_owner["relation"])
        self.assertIn("direct AkBankSourceData external-source parser", source_info_owner["relation"])
        source_manager_join = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceManagerJoinAudit"
        )
        self.assertEqual(source_manager_join["virtualAddress"], "0x1800e2cd0")
        self.assertIn("0x1800350d7", source_manager_join["relation"])
        self.assertIn("parent B +0x2c", source_manager_join["relation"])
        self.assertIn("0x1803449f8", source_manager_join["relation"])
        self.assertIn("entry +0x4c", source_manager_join["relation"])
        self.assertIn("no hash transform", source_manager_join["relation"])
        self.assertIn("successful runtime match", source_manager_join["relation"])
        source_manager_join_callsites = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceManagerJoinCallsiteAudit"
        )
        self.assertEqual(source_manager_join_callsites["virtualAddress"], "0x1800e2cd0")
        self.assertIn("four valid callsites", source_manager_join_callsites["relation"])
        self.assertIn("0x180034762", source_manager_join_callsites["relation"])
        self.assertIn("0x1800350d7", source_manager_join_callsites["relation"])
        self.assertIn("0x1800d35a8", source_manager_join_callsites["relation"])
        self.assertIn("0x1800e06ea", source_manager_join_callsites["relation"])
        self.assertIn("only the two 0x034xxx callsites", source_manager_join_callsites["relation"])
        self.assertIn("do not by themselves prove external-source media selection", source_manager_join_callsites["relation"])
        source_manager_payload = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceManagerJoinPayloadBoundaryAudit"
        )
        self.assertEqual(source_manager_payload["virtualAddress"], "0x1800e2cd0")
        self.assertIn("attachment operation, not path selection", source_manager_payload["relation"])
        self.assertIn("dynamic array at +0x10", source_manager_payload["relation"])
        self.assertIn("+0x18/+0x1c", source_manager_payload["relation"])
        self.assertIn("auxiliary state pointer r9 at +0x30", source_manager_payload["relation"])
        self.assertIn("does not read manager entry +0x38/+0x40", source_manager_payload["relation"])
        self.assertIn("copied UTF-16 record at +0x10", source_manager_payload["relation"])
        self.assertIn("source-state lifecycle registration only", source_manager_payload["relation"])
        self.assertIn("file handle, or PCM consumer", source_manager_payload["relation"])
        source_registration_key = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceRegistrationKeyIndependenceAudit"
        )
        self.assertEqual(source_registration_key["virtualAddress"], "0x1800c3990")
        self.assertIn("global serial slot 0x180344988", source_registration_key["relation"])
        self.assertIn("0x1800c3af2", source_registration_key["relation"])
        self.assertIn("record +0xc", source_registration_key["relation"])
        self.assertIn("manager entry +0x4c", source_registration_key["relation"])
        self.assertIn("0x180034762", source_registration_key["relation"])
        self.assertIn("0x1800350d7", source_registration_key["relation"])
        self.assertIn("no store sourced from the serial global", source_registration_key["relation"])
        self.assertIn("key equality remains a runtime value question", source_registration_key["relation"])
        source_state_lifecycle = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceStateAttachmentLifecycle"
        )
        self.assertEqual(source_state_lifecycle["virtualAddress"], "0x1800e29d0")
        self.assertIn("dynamic array at +0x10", source_state_lifecycle["relation"])
        self.assertIn("live count at +0x18", source_state_lifecycle["relation"])
        self.assertIn("0x1800e1770", source_state_lifecycle["relation"])
        self.assertIn("0x1800e2e20", source_state_lifecycle["relation"])
        self.assertIn("do not read a path", source_state_lifecycle["relation"])
        source_decoder_registry = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceKeyDecoderRegistry"
        )
        self.assertEqual(source_decoder_registry["virtualAddress"], "0x18013f440")
        self.assertIn("0x1801b0160", source_decoder_registry["relation"])
        self.assertIn("owner +0x268", source_decoder_registry["relation"])
        self.assertIn("0x1803449d0", source_decoder_registry["relation"])
        self.assertIn("0x1803449f8", source_decoder_registry["relation"])
        self.assertIn("0x18-byte records", source_decoder_registry["relation"])
        self.assertIn("0x180189041", source_decoder_registry["relation"])
        self.assertIn("not to the UTF-16 path value", source_decoder_registry["relation"])
        source_provider = next(
            row for row in external["stages"] if row["role"] == "nativeSourceProviderPrep"
        )
        self.assertEqual(source_provider["virtualAddress"], "0x1801af7a0")
        self.assertIn("sourceInfo +0x10", source_provider["relation"])
        self.assertIn("0x1800b9530", source_provider["relation"])
        self.assertIn("provider-owned UTF-16 path", source_provider["relation"])
        self.assertIn("source-state key +0", source_provider["relation"])
        source_provider_input = next(
            row
            for row in external["stages"]
            if row["role"] == "nativeSourceProviderDescriptorInputAudit"
        )
        self.assertEqual(source_provider_input["virtualAddress"], "0x1801af7a0")
        self.assertIn("owner +0x18", source_provider_input["relation"])
        self.assertIn("[sourceInfo +0x10]", source_provider_input["relation"])
        self.assertIn("singleton provider vtable +0x28", source_provider_input["relation"])
        self.assertIn("no explicit manager entry, +0x38, or source-state key value", source_provider_input["relation"])
        self.assertIn("identity with the copied external descriptor unresolved", source_provider_input["relation"])
        resolver_callback = next(row for row in external["stages"] if row["role"] == "nativeResolverCallback")
        self.assertEqual(resolver_callback["virtualAddress"], "0x1800e19a0")
        self.assertIn("fixed native bridge 0x180002da0", resolver_callback["relation"])
        native_callback_bridge = next(
            row for row in external["stages"] if row["role"] == "nativeCallbackBridge"
        )
        self.assertEqual(native_callback_bridge["virtualAddress"], "0x180002da0")
        self.assertIn("0x1800030cf", native_callback_bridge["relation"])
        self.assertIn("0x180003430", native_callback_bridge["relation"])
        self.assertIn("0x180002f31", native_callback_bridge["relation"])
        self.assertIn("0x180188fae", native_callback_bridge["relation"])
        native_callback_pump = next(
            row for row in external["stages"] if row["role"] == "nativeCallbackPump"
        )
        self.assertEqual(native_callback_pump["methodIndex"], 446952)
        self.assertEqual(native_callback_pump["virtualAddress"], "0x18328b440")
        self.assertIn("CSharp_b1b6b5807eef294", native_callback_pump["relation"])
        self.assertIn("0x180002d10", native_callback_pump["relation"])
        self.assertIn("0x18328cd90", native_callback_pump["relation"])
        self.assertIn("managed dispatch", native_callback_pump["relation"])
        self.assertIn("not statically joined", external["boundary"])
        package_chain = vfs_loader["nativeCallChains"][0]
        self.assertEqual(package_chain["id"], "vfsBasePathToWwisePackage")
        self.assertEqual(
            [row["methodIndex"] for row in package_chain["stages"]],
            [295909, 480253, 480258, 480259, 446704],
        )
        self.assertEqual(package_chain["stages"][0]["virtualAddress"], "0x184653ea0")
        self.assertIn("native file read", package_chain["boundary"])
        self.assertEqual(bank_manager["nativeCallChains"][0]["id"], package_chain["id"])
        self.assertTrue(any(row["id"] == "extraPck" for row in package_chain["branches"]))
        stream_chain = next(
            row for row in wwise["nativeCallChains"]
            if row["id"] == "streamManagerIoPump"
        )
        self.assertEqual(
            [row["methodIndex"] for row in stream_chain["stages"] if "methodIndex" in row],
            [446743, 446743],
        )
        self.assertEqual(stream_chain["stages"][0]["virtualAddress"], "0x1853d36c8")
        self.assertEqual(stream_chain["stages"][1]["virtualAddress"], "0x180033d20")
        self.assertEqual(stream_chain["stages"][2]["virtualAddress"], "0x1800b6b80")
        self.assertIn("vtable slot +0x8", stream_chain["stages"][2]["relation"])
        self.assertIn("0x1800bc1e0", stream_chain["stages"][2]["relation"])
        self.assertIn("0x1800b5fc0", stream_chain["stages"][2]["relation"])
        self.assertIn("0x180292fc8", stream_chain["stages"][2]["relation"])
        self.assertIn("0x180344900", stream_chain["stages"][2]["relation"])
        source_manager = next(
            row for row in stream_chain["stages"] if row["role"] == "sourceManager"
        )
        self.assertEqual(source_manager["virtualAddress"], "0x1801af7a0")
        self.assertIn("0x1803448f0", source_manager["relation"])
        self.assertIn("0x1801b03b8", source_manager["relation"])
        self.assertIn("0x180292ec0", source_manager["relation"])
        self.assertIn("0x180293260", source_manager["relation"])
        source_descriptor = next(
            row for row in stream_chain["stages"] if row["role"] == "sourceDescriptor"
        )
        self.assertEqual(source_descriptor["virtualAddress"], "0x1800b5e30")
        self.assertIn("0x1800bb160", source_descriptor["relation"])
        self.assertIn("0x180293260", source_descriptor["relation"])
        self.assertIn("separate 0x1800b9460 -> 0x1800b9530", source_descriptor["relation"])
        self.assertIn("+0x288/+0x10", source_descriptor["relation"])
        self.assertIn("UTF-16 path pointer", source_descriptor["relation"])
        self.assertIn("external key/context", source_descriptor["relation"])
        source_provider = next(
            row for row in stream_chain["stages"] if row["role"] == "sourceProviderQueue"
        )
        self.assertEqual(source_provider["virtualAddress"], "0x1800b85c0")
        self.assertIn("0x1800b89b0", source_provider["relation"])
        self.assertIn("0x1800b8120", source_provider["relation"])
        self.assertIn("0x1800b7a40", source_provider["relation"])
        self.assertIn("release/advance-like", source_provider["relation"])
        self.assertIn("0x1801af960", source_provider["relation"])
        self.assertIn("0x18029cde8", source_provider["relation"])
        self.assertIn("0x1801afc80", source_provider["relation"])
        self.assertIn("decoder +0x60", source_provider["relation"])
        self.assertIn("completion 0x1800bf190", source_provider["relation"])
        self.assertIn("one provider allocation", source_manager["relation"])
        self.assertIn("provider allocation/queue", source_provider["relation"])
        request_assembly = next(
            row for row in stream_chain["stages"] if row["role"] == "requestAssembly"
        )
        self.assertEqual(request_assembly["virtualAddress"], "0x1800bc1e0")
        self.assertIn("0x1800bc660", request_assembly["relation"])
        self.assertIn("0x1800bc4a5", request_assembly["relation"])
        self.assertIn("0x18-byte descriptor", request_assembly["relation"])
        self.assertIn("address of candidate +0x8", request_assembly["relation"])
        self.assertIn("branch-dependent provenance", request_assembly["relation"])
        self.assertIn("does not write the candidate context", request_assembly["relation"])
        request_object = next(
            row for row in stream_chain["stages"] if row["role"] == "requestObject"
        )
        self.assertEqual(request_object["virtualAddress"], "0x1800bb8e0")
        self.assertIn("0x1800bbad3", request_object["relation"])
        self.assertIn("0x1800bca20", request_object["relation"])
        self.assertIn("request +0x18", request_object["relation"])
        self.assertIn("0x1800bf190", request_object["relation"])
        self.assertIn("position/source-base/length", request_object["relation"])
        self.assertIn("[object +0xa0] + current offset", request_object["relation"])
        self.assertIn("carrier +0x18 aliases request +0x20", request_object["relation"])
        self.assertIn("same provider allocation", request_object["relation"])
        self.assertIn("primary provider base", request_object["relation"])
        self.assertIn("secondary interface at base +0x90", request_object["relation"])
        native_file_io = next(row for row in stream_chain["stages"] if row["role"] == "nativeFileIo")
        self.assertEqual(native_file_io["virtualAddress"], "0x180005030")
        self.assertIn("CreateFileW", native_file_io["relation"])
        self.assertIn("ReadFileEx", native_file_io["relation"])
        self.assertIn("0x180024270", native_file_io["relation"])
        self.assertIn("+0x60", native_file_io["relation"])
        self.assertIn("WriteFileEx", native_file_io["relation"])
        self.assertIn("pump-to-ReadFileEx dispatch", native_file_io["relation"])
        self.assertIn("+0x428", native_file_io["relation"])
        self.assertIn("0x1800bc1e0", native_file_io["relation"])
        self.assertIn("descriptor +0x10 as request +0x8", native_file_io["relation"])
        self.assertIn("request +0x8", native_file_io["relation"])
        self.assertIn("fixed callback 0x1800bf190", native_file_io["relation"])
        native_file_open = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeFileOpenPathTransportAudit"
        )
        self.assertEqual(native_file_open["virtualAddress"], "0x180024630")
        self.assertIn("0x180004a20", native_file_open["relation"])
        self.assertIn("0x180004b40", native_file_open["relation"])
        self.assertIn("0x180005030", native_file_open["relation"])
        self.assertIn("CreateFileW/GetFileSize", native_file_open["relation"])
        self.assertIn("0x180005150", native_file_open["relation"])
        self.assertIn("no external key, source-state key, or manager +0x38", native_file_open["relation"])
        native_file_open_abi = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeFileOpenArgumentFlowAudit"
        )
        self.assertEqual(native_file_open_abi["virtualAddress"], "0x180024630")
        self.assertIn("rcx is the registered-device/file-I/O object", native_file_open_abi["relation"])
        self.assertIn("rdx is the original descriptor/path argument", native_file_open_abi["relation"])
        self.assertIn("r8 is the caller output slot", native_file_open_abi["relation"])
        self.assertIn("flag r8b=1", native_file_open_abi["relation"])
        self.assertIn("provider context in r9", native_file_open_abi["relation"])
        self.assertIn("normalized UTF-16 result", native_file_open_abi["relation"])
        self.assertIn("No manager entry +0x38, external key, source-state key, or codec pointer", native_file_open_abi["relation"])
        native_io_vtable = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeIoVtablePointerCensus"
        )
        self.assertEqual(native_io_vtable["virtualAddress"], "0x18028f2f8")
        self.assertIn("0x18028bfa0", native_io_vtable["relation"])
        self.assertIn("slots 0/1/2 -> 0x180005030/0x180005150/0x180005180", native_io_vtable["relation"])
        self.assertIn("0x18028c000", native_io_vtable["relation"])
        self.assertIn("+0x28 -> 0x180005430", native_io_vtable["relation"])
        self.assertIn("0x180292c58", native_io_vtable["relation"])
        self.assertIn("0x180292fd0", native_io_vtable["relation"])
        self.assertIn("does not prove", native_io_vtable["relation"])
        read_completion = next(
            row for row in stream_chain["stages"] if row["role"] == "readCompletion"
        )
        self.assertEqual(read_completion["virtualAddress"], "0x1800245b0")
        self.assertIn("0x1800092d0", read_completion["relation"])
        self.assertIn("carrier +0x18", read_completion["relation"])
        self.assertIn("0x1800bf190", read_completion["relation"])
        self.assertIn("rcx=carrier", read_completion["relation"])
        self.assertIn("request cleanup/release", read_completion["relation"])
        self.assertIn("codec provider allocation/queue", read_completion["relation"])
        self.assertIn("not a PCM decoder", read_completion["relation"])
        codec_boundary = next(
            row for row in stream_chain["stages"] if row["role"] == "codecReadBoundary"
        )
        self.assertEqual(codec_boundary["virtualAddress"], "0x1801c9fa0")
        self.assertIn("0x1801ca710", codec_boundary["relation"])
        self.assertIn("indirect function pointer", codec_boundary["relation"])
        self.assertIn("0x1802b09d8", codec_boundary["relation"])
        self.assertIn("0x1801c44d0", codec_boundary["relation"])
        self.assertIn("memory-source copier", codec_boundary["relation"])
        self.assertIn("0x1801cf560", codec_boundary["relation"])
        self.assertIn("0x1801c8d11", codec_boundary["relation"])
        self.assertIn("0x1801c8bda", codec_boundary["relation"])
        self.assertIn("0x1801cc4ce/0x1801cc532/0x1801cc57e", codec_boundary["relation"])
        self.assertIn("callee-frame +0xf0", codec_boundary["relation"])
        self.assertIn("0x1801c6490", codec_boundary["relation"])
        self.assertIn("0x1801c6bf2", codec_boundary["relation"])
        self.assertIn("0x1801c6f90", codec_boundary["relation"])
        self.assertIn("0x1801cbff0", codec_boundary["relation"])
        self.assertIn("integer-array transform", codec_boundary["relation"])
        self.assertIn("not a PCM sink", codec_boundary["relation"])
        self.assertIn("releasing an exhausted buffer", codec_boundary["relation"])
        self.assertIn("decoder-side provider handoff is exact", codec_boundary["relation"])
        self.assertIn("0x1801afc80", codec_boundary["relation"])
        self.assertIn("0x1801aebf0", codec_boundary["relation"])
        self.assertIn("pump-to-ReadFileEx", codec_boundary["relation"])
        self.assertIn("read-completion-to-request-recycle", codec_boundary["relation"])
        self.assertIn("completion-to-provider-allocation", codec_boundary["relation"])
        self.assertIn("direct VoicePlayer externalSourceKey -> AkExternalSourceInfo.szFile -> copied-descriptor path", codec_boundary["relation"])
        self.assertIn("0x1801c4650", codec_boundary["relation"])
        self.assertIn("0x1801c4770", codec_boundary["relation"])
        self.assertIn("0x1801c481a", codec_boundary["relation"])
        self.assertIn("0x1801c483c", codec_boundary["relation"])
        self.assertIn("PCM16", codec_boundary["relation"])
        self.assertIn("0x1801cfe80", codec_boundary["relation"])
        self.assertIn("0x1802b1020", codec_boundary["relation"])
        self.assertIn("0x1801cfd80", codec_boundary["relation"])
        self.assertIn("0x1801cfe00", codec_boundary["relation"])
        self.assertIn("0x18010ad90", codec_boundary["relation"])
        self.assertIn("0x1801cfd70", codec_boundary["relation"])
        self.assertIn("optional decoder callback context +0x2a08", codec_boundary["relation"])
        optional_callback_audit = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeOptionalDecoderCallbackAudit"
        )
        self.assertEqual(optional_callback_audit["virtualAddress"], "0x1801c8b64")
        self.assertIn("overlap-aware audit", optional_callback_audit["relation"])
        self.assertIn("no direct or overlapping write reaches +0x2a08", optional_callback_audit["relation"])
        self.assertIn("unresolved rather than proven absent", optional_callback_audit["relation"])
        descriptor_callsites = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeCodecDescriptorCallsites"
        )
        self.assertEqual(descriptor_callsites["virtualAddress"], "0x1801ca710")
        self.assertIn("only two callsites", descriptor_callsites["relation"])
        self.assertIn("0x1801c7e3e", descriptor_callsites["relation"])
        self.assertIn("0x1801caa1c", descriptor_callsites["relation"])
        self.assertIn("0x1802b09d8", descriptor_callsites["relation"])
        self.assertIn("0x1801cfe80", descriptor_callsites["relation"])
        self.assertIn("No additional direct setup callsite", descriptor_callsites["relation"])
        indirect_setup = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeCodecIndirectSetupReferenceAudit"
        )
        self.assertEqual(indirect_setup["virtualAddress"], "0x1801ca710")
        self.assertIn("no absolute pointer literal", indirect_setup["relation"])
        self.assertIn("no RIP-relative memory operand", indirect_setup["relation"])
        self.assertIn("runtime-computed function pointer", indirect_setup["relation"])
        self.assertIn("remain an evidence gap", indirect_setup["relation"])
        reader_callsites = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeCodecReaderCallsiteAudit"
        )
        self.assertEqual(reader_callsites["virtualAddress"], "0x1801c9fa0")
        self.assertIn("ten valid callsites", reader_callsites["relation"])
        for callsite in (
            "0x1801c83fd",
            "0x1801c8d11",
            "0x1801c96bf/0x1801c985a/0x1801c9909",
            "0x1801c9adb",
            "0x1801c9cca",
            "0x1801ca1eb",
            "0x1801cb8ee/0x1801cbd1b",
        ):
            self.assertIn(callsite, reader_callsites["relation"])
        self.assertIn("no other direct reader call", reader_callsites["relation"])
        self.assertIn("additional setup descriptors", reader_callsites["relation"])
        decoder_callsites = next(
            row
            for row in stream_chain["stages"]
            if row["role"] == "nativeCodecDecoderCallsiteAudit"
        )
        self.assertEqual(decoder_callsites["virtualAddress"], "0x1801c7ec0")
        self.assertIn("three valid calls", decoder_callsites["relation"])
        for callsite in ("0x1801c477b", "0x1801c49bc", "0x1801c4a3e"):
            self.assertIn(callsite, decoder_callsites["relation"])
        self.assertIn("0x1801af960", decoder_callsites["relation"])
        self.assertIn("signed PCM16", decoder_callsites["relation"])
        self.assertIn("return codes drive decoder state", decoder_callsites["relation"])
        self.assertIn("No other direct decoder call", decoder_callsites["relation"])
        boundary = " ".join(stream_chain["boundary"])
        self.assertIn("registered native I/O-device", boundary)
        self.assertIn("registration site", boundary)
        self.assertIn("source-provider queue binding", boundary)
        self.assertIn("dual-interface provider allocation", boundary)
        self.assertIn("selected decoder's 0x1801c4650 -> 0x1801c7ec0", boundary)
        self.assertIn("signed PCM16 writes", boundary)
        action = adapter_chains["playingIdActionQueueToWwise"]
        self.assertEqual(
            [row["methodIndex"] for row in action["stages"]],
            [480012, 480160, 480165, 446431],
        )
        self.assertEqual(len(animator["nativeCallChains"]), 2)
        self.assertEqual(skill["nativeCallChains"][0]["id"], "skillPlaySoundActionRouting")
        self.assertEqual(levelscript["nativeCallChains"][0]["id"], "levelScriptAudioActionRouting")
        self.assertEqual(len(wwise["nativeCallChains"]), 9)
        self.assertIn("PerformStreamMgrIO", wwise["methods"])
        switch_chain = next(
            row for row in audio_manager["nativeCallChains"]
            if row["id"] == "audioObjectSwitchToWwise"
        )
        self.assertEqual(
            [row["methodIndex"] for row in switch_chain["stages"]],
            [38949, 479949, 446539],
        )
        self.assertIn("0x18f373598", switch_chain["stages"][-1]["relation"])
        rtpc_chain = next(
            row for row in audio_manager["nativeCallChains"]
            if row["id"] == "rtpcParameterToWwise"
        )
        self.assertEqual(
            [row["methodIndex"] for row in rtpc_chain["stages"]],
            [38865, 480228, 479952, 446505],
        )
        self.assertIn("0x00000000ffffffff", rtpc_chain["stages"][-2]["relation"])
        self.assertEqual(
            audio_state_system["nativeCallChains"][0]["id"],
            "audioStateTransitionToMusicSetter",
        )
        music_groups = {row["role"]: row for row in music["nativeStateGroups"]}
        self.assertEqual(len(music_groups), 10)
        self.assertEqual(music_groups["topLevelMusicMode"]["groupId"], 0xE414D158)
        self.assertEqual(music_groups["topLevelMusicMode"]["recoveredName"], "music_state")
        self.assertEqual(music_groups["worldMap"]["recoveredName"], "music_map")
        self.assertEqual(music_groups["mission"]["recoveredName"], "music_mission")
        self.assertEqual(music_groups["cutscene"]["recoveredName"], "music_cutscene")
        self.assertNotIn("recoveredName", music_groups["dialog"])
        self.assertEqual(music_groups["remoteCommunication"]["methodIndex"], 39650)
        top_level_values = {
            row["member"]: row["valueId"]
            for row in music_groups["topLevelMusicMode"]["values"]
        }
        self.assertEqual(top_level_values["COMBAT_GENERAL"], 0x525E00A0)
        self.assertEqual(top_level_values["BASE_MODE_DEFENSE"], 0x00FC4659)
        self.assertEqual(
            {
                row["member"]: row["valueId"]
                for row in music_groups["battleIntensity"]["values"]
            },
            {"UNKNOWN": 0xF9D3523D, "LOW": 0x2081B4E5, "HIGH": 0xD3A50981},
        )
        start_calls = {
            row["valueMember"]: row
            for row in music_groups["battleIntensity"]["staticValueCallsites"]
            if row["callerMethod"] == "_StartBattleMusic"
        }
        self.assertEqual(start_calls["HIGH"]["callVirtualAddress"], "0x1846ab04f")
        self.assertEqual(
            music_groups["topLevelMusicMode"]["runtimeValueCallsites"][0]["inputStatus"],
            "runtimeParameterValueUnobserved",
        )
        self.assertEqual(
            music_groups["worldMap"]["staticValueCallsites"][0]["ownerResolution"],
            "unresolvedSharedGenericBody",
        )
        self.assertTrue(all(
            identifiers.audio_hash_generator_compute(row["recoveredName"])
            == row["groupId"]
            for row in music_groups.values()
            if row.get("recoveredName")
        ))
        self.assertEqual(
            music["nativeCallChains"][0]["stages"][-1]["methodIndex"],
            446543,
        )
        transition_rows = {row["stateMask"]: row for row in music["nativeStateTransitions"]}
        self.assertEqual(len(transition_rows), 9)
        self.assertEqual(transition_rows[0x2]["stateNames"], ("FIGHT",))
        self.assertEqual(
            transition_rows[0xC0000]["stateNames"],
            ("IN_FACTORY_AREA", "IN_BLACKBOX"),
        )
        self.assertTrue(all(row["actionOrders"] == (5, 1) for row in transition_rows.values()))
        self.assertTrue(all(row["isOneShot"] is False for row in transition_rows.values()))
        self.assertTrue(all(
            row["callbackTargetStatus"] == "exactMetadataUsageDelegateTargets"
            for row in transition_rows.values()
        ))
        self.assertEqual(
            [row["callbackMethod"] for row in transition_rows[0x40]["registrations"]],
            ["SwitchToDialogMusic", "_OnEnterFMV"],
        )
        self.assertEqual(
            [row["conditionType"] for row in transition_rows[0x40]["registrations"]],
            ["enter", "leave"],
        )
        fight_start = transition_rows[0x2]["registrations"][1]
        self.assertEqual(fight_start["callbackMethod"], "_StartBattleMusic")
        self.assertEqual(fight_start["callbackMethodIndex"], 39483)
        self.assertEqual(len(fight_start["directStateSetters"]), 3)
        for enum_type in (
            "EWwiseMusicMapState", "EWwiseMissionMusicState", "EWwiseDialogMusicState",
            "EWwiseCutsceneMusicState", "EWwiseLoginMusicState", "EWwiseMetaMusicState",
            "EWwiseRemoteCommMusicState",
        ):
            self.assertIn(
                f"Beyond.Gameplay.Audio.AudioMusicSystem+{enum_type}",
                specs,
            )
        self.assertTrue(all(
            row["gameAssemblySha256"] == audio_semantics.CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256
            for row in audio_semantics.AUDIO_PLAYBACK_NATIVE_CALL_CHAINS.values()
        ))

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
            header[0:8] = pack("<II", identifiers.METADATA_MAGIC, 29)
            header[8:24] = pack("<IiIi", 32, len(records), 32 + len(records), len(literal_data))
            path.write_bytes(bytes(header) + records + literal_data)

            self.assertEqual(
                identifiers.collect_metadata_audio_literals(path),
                ["au_rtpc_fixture", "au_ui_confirm", "BARK_TEST"],
            )
            unavailable_native = native_evidence.NativeAudioEvidence(
                path,
                None,
                "missing",
            )
            contexts, event_names = managed_literals.collect_contexts(
                path,
                native_context=unavailable_native,
            )
            self.assertEqual(event_names, ["au_ui_confirm", "BARK_TEST"])
            self.assertNotIn("au_rtpc_fixture", contexts)
            matched_contexts, all_names = managed_literals.collect_contexts(
                path,
                native_context=unavailable_native,
                current_wwise_event_hashes={
                    identifiers.audio_hash_generator_compute("au_ui_confirm")
                },
            )
            self.assertEqual(all_names, ["au_ui_confirm", "BARK_TEST"])
            self.assertEqual(list(matched_contexts), ["au_ui_confirm"])
            self.assertEqual(
                matched_contexts["au_ui_confirm"][0]["playbackPlacementStatus"],
                "identityOnlyManagedStringLiteral",
            )

    def test_promotes_hash_locked_managed_audio_callsite(self) -> None:
        event_name = "au_int_campfire_recover"
        with patch.object(
            identifiers,
            "collect_metadata_audio_literals",
            return_value=[event_name],
        ):
            contexts, _ = managed_literals.collect_contexts(
                Path("metadata"),
                native_context=validated_native_context(),
            )
        context = contexts[event_name][0]
        self.assertEqual(context["kind"], "binaryManagedLiteralCallsite")
        self.assertEqual(context["consumerMethod"], "_LocalReqRecovery")
        self.assertEqual(
            context["playbackCall"],
            "Beyond.Gameplay.Audio.AudioManager.PostEvent",
        )
        self.assertEqual(context["runtimeExecutionStatus"], "runtimeBranchExecutionUnobserved")

    def test_promotes_snapshot_pause_resume_managed_audio_callsites(self) -> None:
        event_names = ["au_gameplay_pause_spidle", "au_gameplay_resume_spidle"]
        with patch.object(
            identifiers,
            "collect_metadata_audio_literals",
            return_value=event_names,
        ):
            contexts, _ = managed_literals.collect_contexts(
                Path("metadata"),
                native_context=validated_native_context(),
                current_wwise_event_hashes={
                    identifiers.audio_hash_generator_compute(name)
                    for name in event_names
                },
            )
        pause = contexts["au_gameplay_pause_spidle"][0]
        self.assertEqual(pause["consumerMethod"], "PauseAction")
        self.assertEqual(pause["literalArgumentRegister"], "rdx")
        self.assertEqual(pause["playbackCallVa"], "0x1873f78a7")
        self.assertEqual(pause["targetBinding"], "snapshotActionEntity")
        resume = contexts["au_gameplay_resume_spidle"][0]
        self.assertEqual(resume["consumerMethod"], "_RemoveActionTimeScaleModifier")
        self.assertEqual(resume["literalLoadVa"], "0x1873fffd8")
        self.assertEqual(resume["playbackCallVa"], "0x1873fffe2")
        self.assertEqual(
            resume["triggerRole"],
            "snapshotActionResumeAfterTimeScaleModifierRemoval",
        )

    def test_promotes_native_custom_state_callsites(self) -> None:
        event_names = (
            "au_int_rotateplatform_port_extense",
            "au_int_rotateplatform_rotate_normal_start",
            "au_int_rotateplatform_rotate_over_start",
            "au_int_rotateplatform_rotate_normal_loop",
            "au_int_crane_rotating_start",
            "au_int_crane_vertical_start",
            "au_int_crane_horizontal_start",
            "au_int_crane_rotating_end",
            "au_int_crane_vertical_end",
            "au_int_crane_horizontal_end",
            "au_int_electric_fence_hit",
            "au_int_forge_iron_smoke",
            "au_int_forge_iron_smoke_stop",
            "au_int_lifter_button_interact_failure",
            "au_int_movingplat_start",
            "au_int_movingplat_end",
        )
        contexts, _ = managed_literals.collect_contexts(
            Path("metadata"),
            native_context=validated_native_context(),
            current_wwise_event_hashes={
                identifiers.audio_hash_generator_compute(name)
                for name in event_names
            },
        )
        expected = {
            "au_int_rotateplatform_port_extense": (
                "PortExtense", "0x1871fe1cd", "0xA000A919",
            ),
            "au_int_rotateplatform_rotate_normal_start": (
                "RotateNormalStart", "0x1871fe0af", "0xA000B4FF",
            ),
            "au_int_rotateplatform_rotate_over_start": (
                "RotateOverStart", "0x1871fe0af", "0xA000B503",
            ),
            "au_int_rotateplatform_rotate_normal_loop": (
                "RotateNormalLoop", "0x18720008f", "0xA000B4FD",
            ),
            "au_int_crane_rotating_start": (
                "start_r", "0x18714537d", "0xA001CF5B",
            ),
            "au_int_crane_vertical_start": (
                "start_ver", "0x1871453cf", "0xA001CF65",
            ),
            "au_int_crane_horizontal_start": (
                "start_hor", "0x18714541b", "0xA001CF3F",
            ),
            "au_int_crane_rotating_end": (
                "end_r", "0x18714520d", "0xA00127A5",
            ),
            "au_int_crane_vertical_end": (
                "end_ver", "0x18714525f", "0xA00127A9",
            ),
            "au_int_crane_horizontal_end": (
                "end_hor", "0x1871452ab", "0xA0012797",
            ),
            "au_int_electric_fence_hit": (
                "onHit", "0x1871d1d50", "0xA0019993",
            ),
            "au_int_forge_iron_smoke": (
                "begin_produce_smoke", "0x1871e2b9f", "0xA00113F3",
            ),
            "au_int_forge_iron_smoke_stop": (
                "stop_produce_smoke", "0x1871e2e86", "0xA001CFFD",
            ),
            "au_int_lifter_button_interact_failure": (
                "failure", "0x1871efdd9", "0xA0012AA7",
            ),
            "au_int_movingplat_start": (
                "start_move", "0x1871f7baa", "0xA001CF45",
            ),
            "au_int_movingplat_end": (
                "stop", "0x1871f7f69", "0xA001CFF5",
            ),
        }
        for event_name, (state_name, callsite, usage_word) in expected.items():
            context = contexts[event_name][0]
            self.assertEqual(context["kind"], "nativeCustomStateCallsite")
            self.assertEqual(context["customStateName"], state_name)
            self.assertEqual(context["switchMethod"], "Beyond.Gameplay.InteractiveLogicBase.SwitchAudioCustomState")
            self.assertEqual(context["callsiteVa"], callsite)
            self.assertEqual(context["metadataUsageWord"], usage_word)
            self.assertEqual(context["playbackPlacementStatus"], "exactManagedNativePlaybackCallsite")

    def test_native_custom_state_trigger_projection_keeps_runtime_boundary(self) -> None:
        rows = [{
            "id": "au_int_rotateplatform_port_retract",
            "hash": identifiers.audio_hash_generator_compute("au_int_rotateplatform_port_retract"),
            "category": "sfx",
            "foundInWwise": True,
            "playbackRole": "playback",
            "possibleMediaCount": 1,
            "media": [{"src": "Audio/CN/sfx/rotate.flac"}],
            "contexts": [{
                "kind": "nativeCustomStateCallsite",
                "consumerType": "Beyond.Gameplay.InteractiveLogicRotatePlatform",
                "consumerMethod": "_EnterStopCargoState",
                "methodIndex": 10138,
                "methodVa": "0x1871fe340",
                "callsiteVa": "0x1871fe401",
                "switchMethod": "Beyond.Gameplay.InteractiveLogicBase.SwitchAudioCustomState",
                "switchMethodVa": "0x187138eac",
                "customStateName": "PortRetract",
                "metadataUsageWord": "0xA000A921",
                "metadataStringLiteralIndex": "0x5490",
                "triggerRole": "rotatePlatformStopCargoPortRetract",
                "evidence": "exactCurrentBuildSwitchAudioCustomStateCallsiteAndAuthoredInteractiveCustomStateEvent",
                "metadataSha256": "metadata",
                "gameAssemblySha256": "gameassembly",
            }],
        }]
        projected = audio_semantics._build_native_custom_state_trigger_contexts(rows)
        self.assertEqual(len(projected), 1)
        self.assertEqual(projected[0]["semanticKind"], "nativeCustomStateCallsite")
        self.assertEqual(projected[0]["action"]["customStateName"], "PortRetract")
        self.assertEqual(projected[0]["selection"]["runtimeSelectionStatus"], "runtimeBranchExecutionUnobserved")

    def test_builds_managed_audio_callsite_trigger_context(self) -> None:
        rows = audio_semantics._build_managed_literal_callsite_trigger_contexts([{
            "id": "au_int_box_collision",
            "hash": 123,
            "category": "sfx",
            "foundInWwise": True,
            "playbackRole": "playback",
            "possibleMediaCount": 1,
            "media": [],
            "contexts": [{
                "kind": "binaryManagedLiteralCallsite",
                "evidence": "exact",
                "source": "metadata:stringLiteral",
                "consumerType": "Beyond.Gameplay.Core.PushableComponent",
                "consumerMethod": "_InternalUpdateAttached",
                "methodIndex": 69383,
                "methodVa": "0x186f10b18",
                "literalLoadVa": "0x186f10c07",
                "playbackCall": "Beyond.Gameplay.Audio.AudioManager.PostEvent",
                "playbackCallVa": "0x186f10c11",
                "targetBinding": "componentAudioObject",
                "triggerRole": "attachedCollisionUpdate",
                "metadataSha256": "metadata",
                "gameAssemblySha256": "assembly",
            }],
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "binaryManagedLiteralCallsite")
        self.assertEqual(rows[0]["situation"]["consumerMethod"], "_InternalUpdateAttached")
        self.assertEqual(rows[0]["action"]["playbackCallVa"], "0x186f10c11")
        self.assertEqual(
            rows[0]["selection"]["triggerBindingStatus"],
            "exactCurrentBuildManagedNativePlaybackCallsite",
        )

    def test_managed_audio_callsite_catalog_keeps_exact_argument_contracts(self) -> None:
        catalog = managed_literals.MANAGED_AUDIO_CALLSITE_CONTEXTS
        self.assertGreaterEqual(len(catalog), 136)
        self.assertEqual(
            catalog["au_ui_button_hyperlink"]["playbackParameter"],
            "eventName",
        )
        self.assertEqual(
            catalog["au_ui_event_growcabin_finish"]["literalArgumentRegister"],
            "r8",
        )
        self.assertEqual(
            catalog["au_int_rune_column_disappear"]["playbackCallVa"],
            catalog["au_int_rune_column_reappear"]["playbackCallVa"],
        )
        self.assertNotEqual(
            catalog["au_int_rune_column_disappear"]["literalLoadVa"],
            catalog["au_int_rune_column_reappear"]["literalLoadVa"],
        )
        self.assertEqual(
            catalog["au_int_anchor_wave_brokensapling_hit"]["literalArgumentInstruction"],
            "cmovne",
        )
        self.assertEqual(
            catalog["au_int_anchor_wave_idlesapling_hit"]["playbackCallVa"],
            catalog["au_int_anchor_wave_brokensapling_hit"]["playbackCallVa"],
        )
        self.assertEqual(
            catalog["au_int_anchor_wave_brokensapling_hit"]["branchCondition"],
            "get_canBreak=true",
        )
        self.assertEqual(
            catalog["au_int_box_touch"]["branchCondition"],
            "previousState!=2 && newState==2",
        )
        self.assertEqual(
            catalog["au_int_box_fall_low"]["branchCondition"],
            "previousState==4 && newState!=4 && m_fallSpeed>10.0",
        )
        self.assertEqual(
            catalog["au_fac_amb_opening"]["playbackSink"],
            "Beyond.Audio.AudioAdapter._PostEvent",
        )
        self.assertEqual(
            catalog["au_fac_amb_opening"]["playbackCallVa"],
            catalog["au_ui_battle_combo_skill"]["playbackCallVa"],
        )
        self.assertEqual(
            catalog["au_ui_plant_gather"]["playbackCall"],
            "nativeStringEventForwarder",
        )
        self.assertEqual(
            catalog["au_ui_plant_gather"]["playbackSink"],
            "Beyond.Audio.AudioAdapter._PostEvent",
        )
        self.assertEqual(
            catalog["au_int_socialcircle_active"]["playbackSink"],
            "Beyond.Gameplay.Audio.AudioManager.PlaySoundAtPosition",
        )
        self.assertEqual(
            catalog["au_int_socialcircle_active"]["branchCondition"],
            "requestedState==2 && currentState==3",
        )
        self.assertEqual(
            catalog["au_int_water_outlet_cdg004_working"]["branchCondition"],
            "newCoreState!=0",
        )
        self.assertEqual(
            catalog["au_vibration_common_short"]["playbackCallVa"],
            "0x18b0f5f68",
        )
        self.assertEqual(
            catalog["au_vibration_common_short"]["branchCondition"],
            "controllerCachedMotion && motionManagerEnabled",
        )
        self.assertEqual(
            catalog["au_ui_power_pole_stayguy"]["branchCondition"],
            "linkType==1",
        )
        self.assertEqual(
            catalog["au_ui_udpipe_stayguy"]["branchCondition"],
            "linkType==2",
        )
        self.assertEqual(
            catalog["au_ui_hud_powertower_count_units"]["playbackCallVa"],
            catalog["au_ui_hud_powertower_count_tens"]["playbackCallVa"],
        )
        self.assertNotEqual(
            catalog["au_ui_hud_powertower_count_units"]["literalLoadVa"],
            catalog["au_ui_hud_powertower_count_tens"]["literalLoadVa"],
        )
        self.assertNotIn("au_music_placeholder_start", catalog)
        self.assertEqual(
            catalog["au_int_blightmiasma_idle_heavy"]["branchCondition"],
            "miasmaAreaLevel==3",
        )
        self.assertEqual(
            catalog["au_int_blightmiasma_idle_heavy"]["playbackSink"],
            "Beyond.Gameplay.Audio.AudioManager.PostEvent",
        )
        self.assertEqual(
            catalog["au_int_erosion_sludge_recover_done"]["selectorMethod"],
            "_GetAudioType",
        )
        self.assertEqual(
            catalog["au_int_erosion_sludge_recover_done"]["playbackSinkVa"],
            "0x18328a690",
        )
        self.assertEqual(
            catalog["au_voice_narrating_3dradio_020"]["branchCondition"],
            "specialOverrideWwiseEvent==2",
        )
        self.assertEqual(
            catalog["au_voice_narrating_3dradio_200"]["literalLoadVa"],
            "0x1852edbe8",
        )
        self.assertEqual(
            catalog["au_voice_narrating_3dradio_100"]["playbackCall"],
            "Beyond.Gameplay.Audio.VoicePlayer.PlayVoice",
        )
        self.assertEqual(
            catalog["au_int_farming_plow_start"]["selectorField"],
            "m_startSoundMap",
        )
        self.assertEqual(
            catalog["au_int_farming_watering_start"]["branchCondition"],
            "operationType==ENatureOperation.Watering(2)",
        )
        self.assertEqual(
            catalog["au_int_farming_harvest_end"]["selectorFieldOffset"],
            "this+0xd8",
        )
        self.assertEqual(
            catalog["au_int_farming_harvest_end"]["additionalConsumerMethod"],
            "_FinishOperation",
        )
        self.assertEqual(
            catalog["au_int_farming_plow_end"]["playbackCallVa"],
            "0x18726b59e",
        )
        self.assertEqual(
            catalog["au_int_xiranitenexus_appear"]["selectorFieldOffset"],
            "config+0x100",
        )
        self.assertEqual(
            catalog["au_int_xiranitenexus_scan_end"]["consumerMethod"],
            "OnScanDisable",
        )
        self.assertEqual(
            catalog["au_int_xiranitenexus_flash"]["additionalConsumerMethod"],
            "OnStart",
        )
        self.assertEqual(
            catalog["au_int_xiranitenexus_flash"]["playbackSinkInvocationVa"],
            "0x186ff9a50",
        )
        self.assertEqual(
            catalog["au_int_xiranitenexus_appear"]["selectorLoadVa"],
            "0x186ff86dd",
        )
        self.assertNotIn("selectorCallVa", catalog["au_int_xiranitenexus_appear"])
        self.assertEqual(
            catalog["au_int_shuimo_bridge_appear"]["consumerMethod"],
            "_TickUpdateFireSeedInUse",
        )
        self.assertEqual(
            catalog["au_int_shuimo_bridge_appear"]["selectorFieldOffset"],
            "config+0x98",
        )
        self.assertEqual(
            catalog["au_int_shuimo_bridge_appear"]["playbackCallVa"],
            "0x183efb877",
        )
        self.assertEqual(
            catalog["au_int_shuimo_bridge_disappear"]["triggerRole"],
            "invisibleBridgeUseEnd",
        )
        self.assertEqual(
            catalog["au_int_yinglongguan_fire_appear"]["branchCondition"],
            "SetFireSeedLevel with active=true and level>0",
        )
        self.assertEqual(
            catalog["au_int_yinglongguan_fire_disappear"]["selectorLoadVa"],
            "0x1870d302b",
        )
        self.assertEqual(
            catalog["au_int_blightmiasma_screen_enter"]["playbackSinkInvocationVa"],
            "0x18721cf6a",
        )
        self.assertEqual(
            catalog["au_int_blightmiasma_screen_dying"]["triggerRole"],
            "miasmaToleranceEnteredDanger",
        )
        self.assertEqual(
            catalog["au_ui_event_explorelevels_hold"]["selectorField"],
            "_audioHoldStart",
        )
        self.assertEqual(
            catalog["au_ui_event_explorelevels_release"]["playbackCallVa"],
            "0x18b0f3b9c",
        )
        self.assertEqual(
            catalog["au_ui_event_explorelevels_alignment"]["selectorLoadVa"],
            "0x18b0ee569",
        )
        self.assertEqual(
            catalog["au_ui_event_explorelevels_set"]["selectorFieldOffset"],
            "owner+0x40",
        )
        self.assertEqual(
            catalog["au_ui_event_socialbuildinglike"]["playbackCallVa"],
            "0x185255f42",
        )
        self.assertEqual(
            catalog["au_ui_event_socialbuildinglike"]["targetBinding"],
            "socialBuildingControllerTransformPosition",
        )
        self.assertEqual(
            catalog["au_ui_popup_levelup_ingame_side"]["playbackInvocationVa"],
            "0x1852fc2f2",
        )
        self.assertEqual(
            catalog["au_ui_popup_levelup_ingame_side"]["playbackSink"],
            "Beyond.Audio.AudioAdapter._PostEvent",
        )
        self.assertEqual(
            catalog["au_weekraid_danger_warnning_start"]["selectorField"],
            "s_DangerAudio",
        )
        self.assertEqual(
            catalog["au_weekraid_danger_warnning_start"]["playbackCallVa"],
            "0x186f60333",
        )
        self.assertEqual(
            catalog["au_int_collection_intteractive"]["selectorField"],
            "AUDIO_COLLECT",
        )
        self.assertEqual(
            catalog["au_int_collection_intteractive"]["targetBinding"],
            "collectionMoonEntityPosition",
        )
        self.assertEqual(
            catalog["au_int_collection_coin_countingdown"]["selectorField"],
            "DISAPPEAR_AUDIO_NAME",
        )
        self.assertEqual(
            catalog["au_int_collection_coin_countingdown"]["additionalPlaybackCallVa"],
            "0x186ecf1f4",
        )
        self.assertEqual(
            catalog["au_int_gold_coin_eny_die"]["branchCondition"],
            "source==EGoldCoinSource.Monster(3)",
        )
        self.assertEqual(
            catalog["au_int_gold_coin_eny_die"]["callerCallVa"],
            "0x1870de140",
        )
        self.assertEqual(
            catalog["au_int_gold_coin_eny_trigger"]["selectorField"],
            "AUDIO_COIN_DISAPPEAR",
        )
        self.assertEqual(
            catalog["au_int_gold_coin_eny_trigger"]["targetBinding"],
            "playerPositionPlusGoldCoinEffectOffset",
        )
        self.assertEqual(
            catalog["au_sfx_enemy_drop_absorbing_02"]["selectorField"],
            "DROP_EFFECT_FIRST",
        )
        self.assertEqual(
            catalog["au_sfx_enemy_drop_absorbing_02"]["callerCallVa"],
            "0x1870e50cd",
        )
        self.assertEqual(
            catalog["au_sfx_enemy_drop_absorbing_01_start"]["selectorField"],
            "DROP_EFFECT_SECOND",
        )
        self.assertEqual(
            catalog["au_sfx_enemy_drop_absorbing_01_start"]["selectorFieldOffset"],
            "static+0x8",
        )
        self.assertEqual(
            catalog["au_int_medicalstation_end"]["playbackCallVa"],
            "0x1850f5dd1",
        )
        self.assertEqual(
            catalog["au_int_medicalstation_end"]["triggerRole"],
            "mainCharacterExitedMedicalTowerRange",
        )
        self.assertEqual(
            catalog["au_int_medicalstation_start"]["playbackCallVa"],
            "0x1850f5e68",
        )
        self.assertEqual(
            catalog["au_int_medicalstation_start"]["triggerRole"],
            "mainCharacterEnteredMedicalTowerRange",
        )
        self.assertEqual(
            catalog["au_gameplay_pause_spidle"]["consumerMethod"],
            "PauseAction",
        )
        self.assertEqual(
            catalog["au_gameplay_pause_spidle"]["playbackCallVa"],
            "0x1873f78a7",
        )
        self.assertEqual(
            catalog["au_gameplay_pause_spidle"]["targetBinding"],
            "snapshotActionEntity",
        )
        self.assertEqual(
            catalog["au_gameplay_resume_spidle"]["consumerMethod"],
            "_RemoveActionTimeScaleModifier",
        )
        self.assertEqual(
            catalog["au_gameplay_resume_spidle"]["playbackCallVa"],
            "0x1873fffe2",
        )
        self.assertEqual(
            catalog["au_gameplay_resume_spidle"]["triggerRole"],
            "snapshotActionResumeAfterTimeScaleModifierRemoval",
        )
        self.assertEqual(
            catalog["au_ui_hud_tacticalmedicationrecovery"]["consumerMethod"],
            "_UpdateTacticalItemStatus",
        )
        self.assertEqual(
            catalog["au_ui_hud_tacticalmedicationrecovery"]["playbackInvocationVa"],
            "0x18504f154",
        )
        self.assertEqual(
            catalog["au_eny_find_target"]["selectorField"],
            "soundName",
        )
        self.assertEqual(
            catalog["au_eny_find_target"]["playbackCallVa"],
            "0x1841357f9",
        )
        self.assertEqual(
            catalog["au_int_farming_addsoil"]["consumerMethod"],
            "OnNodeAdded",
        )
        self.assertEqual(
            catalog["au_int_farming_addsoil"]["targetBinding"],
            "mainCharacterEntity",
        )
        self.assertEqual(
            catalog["au_int_anchor_wave_explosion"]["selectorLoadVa"],
            "0x1870b93c4",
        )
        self.assertEqual(
            catalog["au_int_anchor_wave_diffusion"]["playbackCallVa"],
            "0x1870b9422",
        )
        self.assertEqual(
            catalog["au_int_anchor_idle"]["playbackCall"],
            "Beyond.Gameplay.Core.DynamicScene.DynamicSceneConditionHelper.PlayLoopAudioIfNecessary",
        )
        self.assertEqual(
            catalog["au_int_anchor_idle"]["targetBinding"],
            "anchorSceneDynamicMono",
        )
        self.assertEqual(
            catalog["au_env_npc_butterflyclust_small_interactall"]["selectorField"],
            "ALL_SMALL_BUTTER_FLY_COLLECTED_AUDIO",
        )
        self.assertEqual(
            catalog["au_env_npc_butterflyclust_small_interactall"]["additionalPlaybackCallVa"],
            "0x186f9edc1",
        )

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
            _names, hashes = table_contexts.collect_table_audio_events(root)
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

            contexts = table_contexts.collect_table_contexts(root)

            self.assertEqual(set(contexts), {"au_sfx_radio_transition"})
            self.assertEqual(len(contexts["au_sfx_radio_transition"]), 1)
            self.assertIn("Persistent", contexts["au_sfx_radio_transition"][0]["source"])

    def test_remote_common_audio_id_is_event_context_not_timeline_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            table_path = root / "structured/Persistent/Table/RemoteCommonTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "remotecomm_fixture": {
                    "autoPlay": True,
                    "remoteCommSingleDataList": [{
                        "singleId": "remotecomm_fixture_001",
                        "middleId": "npc_fixture",
                        "actorList": ["npc_fixture"],
                        "audioId": "au_sfx_remotecomm_fixture",
                        "voiceId": "au_remotecomm_fixture_001",
                        "autoPlayTime": -1.0,
                    }],
                },
            }), encoding="utf-8")

            contexts = table_contexts.collect_table_contexts(root)
            self.assertEqual(set(contexts), {"au_sfx_remotecomm_fixture"})
            authored = contexts["au_sfx_remotecomm_fixture"][0]
            self.assertEqual(authored["kind"], "remoteCommonAudio")
            self.assertEqual(authored["triggerBindingStatus"], "exactRemoteCommonAudioId")
            self.assertEqual(authored["voiceLinkStatus"], "separateRemoteCommonVoiceId")
            self.assertEqual(authored["voiceId"], "au_remotecomm_fixture_001")

            rows, _, _ = event_projection.build_event_rows({
                "eventNames": ["au_sfx_remotecomm_fixture"],
                "events": [],
                "eventEvidence": [],
            }, contexts)
            summary = event_summary.event_summary_row(rows[0], "event_details/00.json")
            self.assertEqual(summary["contextKinds"], ["remoteCommonAudio"])
            self.assertEqual(summary["contextGroups"], ["authoredConfig"])
            self.assertEqual(summary["triggerBindingStatuses"], ["exactRemoteCommonAudioId"])
            self.assertNotIn("timelineOwnershipGapCount", summary)

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
                            "children": [],
                        },
                        "conditionExpr": {
                            "exprType": 2,
                            "stringValue": "",
                            "boolValue": False,
                            "intValue": 149,
                            "floatValue": 0.0,
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
                                "boolValue": False,
                                "intValue": 0,
                                "floatValue": 0.0,
                                "children": [],
                            },
                            "conditionExpr": {"exprType": 0, "stringValue": "", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                        }]},
                    },
                },
            }), encoding="utf-8")

            semantics = table_contexts.collect_audio_cue_semantics(root)

            self.assertEqual(set(semantics["eventContexts"]), {"au_music_direct", "au_music_level"})
            level = semantics["eventContexts"]["au_music_level"][0]
            self.assertEqual(level["handlerScope"], "level")
            self.assertEqual(level["levelId"], "map_test")
            self.assertEqual(level["cueId"], 0xFFFFFFFE)
            self.assertEqual(
                {row["stringValue"] for row in semantics["expressionOperands"]},
                {"au_trigger_condition_operand"},
            )
            expression_nodes = semantics["cueDefinitions"][0xFFFFFFFE]["expressionAst"]
            event_nodes = [node for node in expression_nodes if node["exprType"] == 3]
            self.assertEqual(len(event_nodes), 2)
            self.assertTrue(all(node["nodeClass"] == "authoredEventRequest" for node in event_nodes))
            self.assertTrue(all(node["validationStatus"] == "validated" for node in event_nodes))
            variable_nodes = [node for node in expression_nodes if node["exprType"] == 8]
            self.assertEqual(len(variable_nodes), 1)
            self.assertTrue(all(node["nodeClass"] == "stringLiteral" for node in variable_nodes))
            self.assertTrue(all(node["semanticRole"] == "runtimeCueVariable" for node in variable_nodes))
            self.assertTrue(all(node["canonicalNodeClass"] == "runtimeCueVariable" for node in variable_nodes))
            class_counts = semantics["cueDefinitions"][0xFFFFFFFE]["expressionNodeClassCounts"]
            self.assertEqual(class_counts["stringLiteral"], 1)
            self.assertNotIn("runtimeCueVariable", class_counts)
            self.assertNotIn("authoredVariableNameCandidate", class_counts)
            self.assertEqual(
                table_contexts.collect_table_audio_events(root)[0],
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
                        "behaviourExpr": {"exprType": 3, "stringValue": "au_music_fixture", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                        "conditionExpr": {"exprType": 0, "stringValue": "", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
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

            cue_semantics = table_contexts.collect_audio_cue_semantics(root)
            controls = table_contexts.collect_audio_global_control_semantics(root, cue_semantics)

            refs = {row["field"]: row for row in controls["audioGlobalMusicCueRefs"]}
            self.assertEqual(refs["musicCueCombatIn"]["definitionStatus"], "resolved")
            self.assertEqual(refs["musicCueFactoryAreaIn"]["definitionStatus"], "missing")
            self.assertEqual(
                {row["parameterName"] for row in controls["rtpcParameters"]},
                {"au_rtpc_global_fixture", "au_rtpc_speed_fixture"},
            )
            derived = controls["eventContexts"]["au_music_fixture"][0]
            self.assertEqual(derived["globalMusicCueField"], "musicCueCombatIn")
            contexts = table_contexts.collect_table_contexts(root)
            self.assertIn("au_music_fixture", contexts)
            self.assertNotIn("#0xfffffffe", contexts)

    def test_audio_cue_expression_ast_is_typed_recursive_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            table_path = root / "structured/StreamingAssets/Table/AudioCueTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "-7": {
                    "directHandlers": [{
                        "behaviourExpr": {
                            "exprType": 2,
                            "stringValue": " au_authored ",
                            "boolValue": False,
                            "intValue": 0,
                            "floatValue": 0.0,
                            "children": [
                                {"exprType": 8, "stringValue": "runtime_key", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                                {"exprType": 2, "stringValue": "", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": [{"exprType": 0, "stringValue": "", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []}]},
                                {"exprType": 99, "stringValue": "unknown", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                            ],
                        },
                        "conditionExpr": {"exprType": 8, "stringValue": "condition_key", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                    }],
                    "levelHandlerMap": {"map_fixture": {"handlers": [{
                        "behaviourExpr": {"exprType": 3, "stringValue": " au_level ", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                        "conditionExpr": {"exprType": 3, "stringValue": "bad_shape", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": "not-a-list"},
                    }]}},
                },
            }), encoding="utf-8")

            semantics = table_contexts.collect_audio_cue_semantics(root)

        definition = semantics["cueDefinitions"][0xFFFFFFF9]
        nodes = definition["expressionAst"]
        by_path = {node["path"]: node for node in nodes}
        authored = by_path["-7.directHandlers[0].behaviourExpr"]
        self.assertEqual(authored["nodeClass"], "compositeOpaque")
        self.assertEqual(authored["cueSignedId"], -7)
        self.assertEqual(authored["cueU32"], 0xFFFFFFF9)
        self.assertEqual(authored["depth"], 0)
        self.assertEqual(authored["childPaths"][0], "-7.directHandlers[0].behaviourExpr.children[0]")
        self.assertEqual(by_path[authored["childPaths"][0]]["nodeClass"], "stringLiteral")
        self.assertEqual(by_path[authored["childPaths"][0]]["semanticRole"], "runtimeCueVariable")
        self.assertEqual(by_path[authored["childPaths"][0]]["canonicalNodeClass"], "runtimeCueVariable")
        self.assertEqual(by_path[authored["childPaths"][0]]["parentPath"], authored["path"])
        self.assertEqual(by_path["-7.directHandlers[0].behaviourExpr.children[1]"]["nodeClass"], "compositeOpaque")
        self.assertEqual(by_path["-7.directHandlers[0].behaviourExpr.children[2]"]["validationStatus"], "unknownExprType")
        self.assertEqual(
            by_path["-7.levelHandlerMap[map_fixture].handlers[0].conditionExpr"]["validationStatus"],
            "invalidShape",
        )
        self.assertEqual(
            {row["semanticRole"] for row in semantics["expressionOperands"]},
            {"runtimeCueVariable"},
        )
        self.assertEqual(
            {row["stringValue"] for row in semantics["expressionOperands"]},
            {"runtime_key", "condition_key"},
        )
        self.assertEqual(
            by_path["-7.levelHandlerMap[map_fixture].handlers[0].conditionExpr"]["nodeClass"],
            "opaque",
        )
        self.assertTrue(any(row["code"] == "unknownExprType" for row in semantics["diagnostics"]))
        self.assertTrue(any(row["code"] == "childrenNotListOfDict" for row in semantics["diagnostics"]))
        self.assertIsNone(authored["exprTypeName"])
        self.assertIsNone(authored["exprOperatorType"])

        detail = table_contexts.audio_cue_expression_detail_for_contexts(
            semantics["eventContexts"]["au_level"], semantics
        )
        self.assertEqual(detail["audioCueExpressionSchemaVersion"], 1)
        summary = event_summary.event_summary_row({
            "id": "au_level",
            "contexts": semantics["eventContexts"]["au_level"],
            "audioCueExpressionDetail": detail,
        }, "event_details/00.json")
        self.assertNotIn("audioCueExpressionDetail", summary)

        missing = audio_semantics.build_timeline_audio_cue_contexts(
            {"occurrencesByCue": {"missing": [{"cueName": "au_missing", "cueRole": "start"}]}},
            semantics,
        )
        self.assertEqual(len(missing["invocations"]), 1)
        self.assertEqual(missing["invocations"][0]["definitionStatus"], "missing")
        self.assertEqual(missing["eventContexts"], {})

    def test_audio_cue_native_gate_and_iterative_bound_are_fail_closed(self) -> None:
        missing = audio_cue_native.exact_native_audio_cue_contract(None)
        self.assertEqual(missing["status"], "missing")
        self.assertEqual(missing["expressionTypes"], {})
        mismatched = audio_cue_native.exact_native_audio_cue_contract(
            native_evidence.NativeAudioEvidence(
                Path("metadata"), Path("GameAssembly.dll"), "mismatched",
                audio_cue_native.native_evidence.EXPECTED_METADATA_SHA256,
                audio_cue_native.native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
                gate_verified=True,
            )
        )
        self.assertEqual(mismatched["operatorTypes"], {})
        exact_context = native_evidence.NativeAudioEvidence(
            Path("metadata"), Path("GameAssembly.dll"), "validated",
            audio_cue_native.native_evidence.EXPECTED_METADATA_SHA256,
            audio_cue_native.native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
            gate_verified=True,
        )
        exact = audio_cue_native.exact_native_audio_cue_contract(exact_context)
        self.assertEqual(exact["expressionTypes"][8], "STRING_LITERAL")
        self.assertEqual(exact["operatorTypes"][149], "GetBoolVar")

        def node(expr_type: int, *, children: list[dict[str, object]] | None = None, int_value: int = 0) -> dict[str, object]:
            return {
                "boolValue": False, "children": children or [], "exprType": expr_type,
                "floatValue": 0.0, "intValue": int_value, "stringValue": "",
            }

        deep = node(1)
        cursor = deep
        for _ in range(1100):
            child = node(1)
            cursor["children"] = [child]
            cursor = child
        nodes, diagnostics = table_contexts.walk_audio_cue_expression(
            deep, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
            level_id="", handler_index=0, expression_side="behavior", root_field="behaviourExpr",
            root_path="1.directHandlers[0].behaviourExpr", source="fixture",
            native_contract=exact,
        )
        self.assertLessEqual(len(nodes), 1025)
        self.assertTrue(any(row["code"] == "depthLimit" for row in diagnostics))
        self.assertNotIn("authoredEventRequest", {row["nodeClass"] for row in nodes})
        bad_shape = node(3)
        bad_shape.pop("floatValue")
        bad_nodes, bad_diagnostics = table_contexts.walk_audio_cue_expression(
            bad_shape, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
            level_id="", handler_index=0, expression_side="behavior", root_field="behaviourExpr",
            root_path="1.directHandlers[0].behaviourExpr", source="fixture", native_contract=exact,
        )
        self.assertEqual(bad_nodes[0]["validationStatus"], "invalidShape")
        self.assertEqual(bad_nodes[0]["nodeClass"], "opaque")
        self.assertIsNone(bad_nodes[0]["exprTypeName"])
        self.assertIsNone(bad_nodes[0]["exprOperatorType"])
        self.assertTrue(any(row["code"] == "invalidShape" for row in bad_diagnostics))
        oversized_child = node(3)
        oversized_child["stringValue"] = "au_must_not_project"
        oversized = node(
            1,
            children=[
                oversized_child
                for _ in range(table_contexts._AUDIO_CUE_MAX_CHILDREN + 1)
            ],
        )
        oversized_nodes, oversized_diagnostics = table_contexts.walk_audio_cue_expression(
            oversized, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
            level_id="", handler_index=0, expression_side="behavior", root_field="behaviourExpr",
            root_path="1.directHandlers[0].behaviourExpr", source="fixture",
        )
        self.assertEqual(len(oversized_nodes), 1)
        self.assertEqual(oversized_nodes[0]["validationStatus"], "childrenLimit")
        self.assertEqual(oversized_nodes[0]["nodeClass"], "opaque")
        self.assertEqual(oversized_nodes[0]["canonicalNodeClass"], "opaque")
        self.assertEqual(oversized_nodes[0]["childPaths"], [])
        self.assertTrue(any(row["code"] == "childrenLimit" for row in oversized_diagnostics))
        self.assertNotIn("authoredEventRequest", {row["canonicalNodeClass"] for row in oversized_nodes})
        self.assertNotIn("runtimeCueVariable", {row.get("semanticRole") for row in oversized_nodes})
        self.assertNotIn("au_must_not_project", {row.get("stringValue") for row in oversized_nodes})
        binary = node(2, children=[{**node(8), "stringValue": "flag_name"}], int_value=149)
        binary_nodes, _ = table_contexts.walk_audio_cue_expression(
            binary, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
            level_id="", handler_index=0, expression_side="condition", root_field="conditionExpr",
            root_path="1.directHandlers[0].conditionExpr", source="fixture", native_contract=exact,
        )
        candidate = binary_nodes[1]
        self.assertEqual(candidate["exprTypeName"], "STRING_LITERAL")
        self.assertEqual(candidate["exprOperatorType"], "GetBoolVar")
        self.assertEqual(candidate["nodeClass"], "authoredVariableNameCandidate")
        self.assertEqual(candidate["semanticRole"], "runtimeCueVariable")
        self.assertEqual(candidate["canonicalNodeClass"], "runtimeCueVariable")
        self.assertEqual(candidate["nativeEnumStatus"], "validated")
        self.assertNotIn("directCall", candidate)

        for gated_contract in (None, mismatched):
            gated_nodes, _ = table_contexts.walk_audio_cue_expression(
                binary, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
                level_id="", handler_index=0, expression_side="condition", root_field="conditionExpr",
                root_path="1.directHandlers[0].conditionExpr", source="fixture",
                native_contract=gated_contract,
            )
            gated_candidate = gated_nodes[1]
            self.assertIsNone(gated_candidate["exprTypeName"])
            self.assertIsNone(gated_candidate["exprOperatorType"])
            self.assertEqual(gated_candidate["nodeClass"], "stringLiteral")
            self.assertEqual(gated_candidate["semanticRole"], "runtimeCueVariable")
            self.assertEqual(gated_candidate["canonicalNodeClass"], "runtimeCueVariable")
            self.assertEqual(
                gated_candidate["nativeEnumStatus"],
                "missing" if gated_contract is None else "mismatched",
            )

        unproven = node(2, children=[{**node(8), "stringValue": "flag_name"}], int_value=0)
        unproven_nodes, _ = table_contexts.walk_audio_cue_expression(
            unproven, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
            level_id="", handler_index=0, expression_side="condition", root_field="conditionExpr",
            root_path="1.directHandlers[0].conditionExpr", source="fixture", native_contract=exact,
        )
        self.assertEqual(unproven_nodes[1]["exprTypeName"], "STRING_LITERAL")
        self.assertIsNone(unproven_nodes[1]["exprOperatorType"])
        self.assertEqual(unproven_nodes[1]["nodeClass"], "stringLiteral")

        nested = node(
            2,
            children=[node(1, children=[{**node(8), "stringValue": "nested_flag"}])],
            int_value=149,
        )
        nested_nodes, _ = table_contexts.walk_audio_cue_expression(
            nested, cue_signed_id=1, cue_id=1, cue_hex="0x00000001", handler_scope="direct",
            level_id="", handler_index=0, expression_side="condition", root_field="conditionExpr",
            root_path="1.directHandlers[0].conditionExpr", source="fixture", native_contract=exact,
        )
        self.assertEqual(nested_nodes[2]["exprOperatorType"], "GetBoolVar")
        self.assertEqual(nested_nodes[2]["nodeClass"], "authoredVariableNameCandidate")

    def test_audio_cue_bounds_reject_huge_scalars_ids_levels_and_paths(self) -> None:
        huge_float = 10 ** 10000
        huge_string = "x" * (table_contexts._AUDIO_CUE_MAX_STRING + 5000)
        huge_node = {
            "boolValue": False, "children": [], "exprType": 3,
            "floatValue": huge_float, "intValue": 0, "stringValue": huge_string,
        }
        nodes, diagnostics = table_contexts.walk_audio_cue_expression(
            huge_node, cue_signed_id=1, cue_id=1, cue_hex="0x00000001",
            handler_scope="direct", level_id="", handler_index=0,
            expression_side="behavior", root_field="behaviourExpr",
            root_path="1.directHandlers[0].behaviourExpr", source="fixture",
        )
        self.assertEqual(nodes[0]["validationStatus"], "badScalar")
        self.assertEqual(nodes[0]["nodeClass"], "opaque")
        self.assertIsNone(nodes[0]["floatValue"])
        self.assertEqual(len(nodes[0]["stringValue"]), table_contexts._AUDIO_CUE_MAX_STRING)
        self.assertIsNone(nodes[0]["rawScalars"]["floatValue"])
        self.assertEqual(len(nodes[0]["rawScalars"]["stringValue"]), table_contexts._AUDIO_CUE_MAX_STRING)
        self.assertTrue(any(row["code"] == "badScalar" for row in diagnostics))

        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            table_path = root / "structured/StreamingAssets/Table/AudioCueTable.json"
            table_path.parent.mkdir(parents=True)
            valid = {
                "boolValue": False, "children": [], "exprType": 3,
                "floatValue": 0.0, "intValue": 0, "stringValue": "event",
            }
            table_path.write_text(json.dumps({
                str(2 ** 31): {"directHandlers": [{"behaviourExpr": valid}]},
                "1": {"levelHandlerMap": {"L" * (table_contexts._AUDIO_CUE_MAX_LEVEL + 1): {
                    "handlers": [{"behaviourExpr": valid}],
                }}},
            }), encoding="utf-8")
            semantics = table_contexts.collect_audio_cue_semantics(root)
        self.assertNotIn(2 ** 31, semantics["cueDefinitions"])
        definition = semantics["cueDefinitions"][1]
        self.assertEqual(definition["expressionNodeCount"], 0)
        codes = {row["code"] for row in semantics["diagnostics"]}
        self.assertIn("cueSignedIdOutOfRange", codes)
        self.assertIn("levelIdTooLong", codes)

        compact_a = table_contexts._audio_cue_compact_path("root", (4097, 564))
        compact_b = table_contexts._audio_cue_compact_path("root", (256, 4660))
        self.assertIsNotNone(compact_a)
        self.assertIsNotNone(compact_b)
        self.assertNotEqual(compact_a, compact_b)
        self.assertEqual(compact_a, table_contexts._audio_cue_compact_path("root", (4097, 564)))
        self.assertIn("#children/4097/564", compact_a)
        self.assertLessEqual(len(compact_a), table_contexts._AUDIO_CUE_MAX_PATH)

        deep = {
            "boolValue": False, "children": [], "exprType": 0,
            "floatValue": 0.0, "intValue": 0, "stringValue": "",
        }
        cursor = deep
        for _ in range(table_contexts._AUDIO_CUE_MAX_DEPTH + 1):
            child = {
                "boolValue": False, "children": [], "exprType": 0,
                "floatValue": 0.0, "intValue": 0, "stringValue": "",
            }
            cursor["children"] = [child]
            cursor = child
        deep_nodes, deep_diagnostics = table_contexts.walk_audio_cue_expression(
            deep, cue_signed_id=1, cue_id=1, cue_hex="0x00000001",
            handler_scope="direct", level_id="", handler_index=0,
            expression_side="behavior", root_field="behaviourExpr",
            root_path="1.directHandlers[0].behaviourExpr", source="fixture",
        )
        self.assertTrue(all(len(node["path"]) <= table_contexts._AUDIO_CUE_MAX_PATH for node in deep_nodes))
        self.assertEqual(len({node["path"] for node in deep_nodes}), len(deep_nodes))
        self.assertTrue(any(row["code"] == "depthLimit" for row in deep_diagnostics))

    def test_audio_frontend_audio_cue_redaction_covers_all_context_owners(self) -> None:
        source = (Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js").read_text(encoding="utf-8")
        for kind in (
            "audioCueBehaviorEvent", "audioCueExpressionOperand",
            "timelineAudioCueBehaviorEvent", "levelScriptAudioCueBehaviorEvent",
            "audioGlobalMusicCueBehaviorEvent",
        ):
            self.assertIn(f'"{kind}"', source)
        self.assertIn("function isAudioCueContext", source)
        self.assertIn("function isAudioCueBehaviorContext", source)
        raw_body = source.split("const rawForDisplay", 1)[1].split("const json", 1)[0]
        for key in ("cueHex", "handlerLevel", "exprType", "expressionPath", "rawScalars", "validationIssues"):
            self.assertIn(f'"{key}"', raw_body)
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split("function radioTableLineLabel", 1)[0]
        self.assertIn("const audioCueContext = isAudioCueContext(context)", evidence_body)
        self.assertIn("isAudioCueBehaviorContext(context)", evidence_body)

    def test_mono_behaviour_audio_id_fields_are_exact_authored_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            index = (
                root / "recovered/AnimeStudio-cli/StreamingAssets/object_index/parts"
                / "StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl"
            )
            index.parent.mkdir(parents=True)
            rows = [{
                "recordType": "object",
                "object": {
                    "serializedFile": "CAB-test", "source": "VFS/test.chk",
                    "sourceOffset": 42, "pathId": 99,
                },
                "name": "FixtureComponent",
                "schemaId": "schema-test",
                "typeTreeSource": "serializedType",
                "scalars": [
                    ["$._spawnAudioEvent._id", "i", -2],
                    ["$._onHitAudioRtpc._id", "i", 123],
                    ["$.genericValue", "i", 456],
                ],
                "script": {"pathId": 7, "fullName": "Fixture.AudioComponent"},
                "sceneContext": {
                    "gameObjectName": "Audio Fixture",
                    "hierarchyPath": ["Root", "Audio Fixture"],
                    "worldPosition": {"x": 1, "y": 2, "z": 3},
                    "worldPositionStatus": "exact_transform_hierarchy",
                },
            }, {
                "recordType": "object",
                "object": {"serializedFile": "CAB-managed", "pathId": 100},
                "name": "ManagedFixture",
                "scalars": [
                    ["$.references.RefIds[0].type.class", "s", "PlaySingleSound"],
                    ["$.references.RefIds[0].type.ns", "s", "Beyond.Gameplay"],
                    ["$.references.RefIds[0].data.layout", "s", "Beyond.Gameplay.PlaySingleSound"],
                    ["$.references.RefIds[0].data.soundBase.soundSpawn.hex", "s", "0x12345678"],
                ],
            }, {
                "recordType": "object",
                "object": {"serializedFile": "CAB-absent", "pathId": 101},
                "scalars": [["$._finishAudioEvent._id", "i", 111]],
            }, {
                "recordType": "object",
                "object": {"serializedFile": "CAB-state", "pathId": 102},
                "name": "StateAudioFixture",
                "scalars": [
                    ["$.stateList[0].stateName", "s", "active"],
                    ["$.stateList[0].audioPlayConfigs[0].isDirectlyPlay", "i", 1],
                    ["$.stateList[0].audioPlayConfigs[0].normalAudiId._id", "i", 0x87654321],
                    ["$.stateList[0].disableAudio", "i", 1],
                ],
            }]
            index.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )

            result = audio_semantics.collect_mono_behaviour_audio_id_contexts(
                root,
                {0xFFFFFFFE, 0x12345678, 0x87654321},
            )

            self.assertEqual(result["stats"]["distinctEventHashes"], 3)
            self.assertEqual(result["stats"]["eventContextOccurrences"], 3)
            spawn = result["eventContexts"]["#0xfffffffe"][0]
            self.assertEqual(spawn["authoredFieldRole"], "componentSoundSpawn")
            self.assertEqual(spawn["authoredFieldNameRaw"], "_spawnAudioEvent")
            self.assertEqual(spawn["serializedFieldPathStatus"], "exact")
            self.assertEqual(spawn["gameObjectName"], "Audio Fixture")
            self.assertEqual(spawn["runtimeActivationStatus"], "monoBehaviourComponentExecutionNotObserved")
            managed = result["eventContexts"]["#0x12345678"][0]
            self.assertEqual(managed["managedReferenceClass"], "PlaySingleSound")
            self.assertEqual(managed["managedReferenceLayout"], "Beyond.Gameplay.PlaySingleSound")
            state = result["eventContexts"]["#0x87654321"][0]
            self.assertEqual(state["serializedPlaybackControls"], {
                "stateName": "active",
                "isDirectlyPlay": 1,
                "disableAudioOnState": 1,
            })
            self.assertNotIn("#0x0000007b", result["eventContexts"])
            self.assertNotIn("#0x0000006f", result["eventContexts"])

    def test_mono_behaviour_audio_id_context_is_exposed_as_static_trigger(self) -> None:
        rows = audio_semantics._build_mono_behaviour_audio_id_trigger_contexts([{
            "id": "hashed-event:0x12345678",
            "hash": 0x12345678,
            "category": "unknown",
            "foundInWwise": True,
            "possibleMediaCount": 2,
            "media": [],
            "contexts": [{
                "kind": "monoBehaviourAudioIdField",
                "authoredFieldRole": "componentHitCallback",
                "componentLayout": "serializedMonoBehaviourAudioIdField",
                "componentType": "Fixture.AudioComponent",
                "authoredFieldNameRaw": "_onHitAudioEvent",
                "serializedFieldPath": "$._onHitAudioEvent._id",
                "serializedFile": "CAB-test",
                "pathId": 5,
                "gameObjectName": "Hit FX",
                "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                "evidence": "exactSerializedMonoBehaviourAudioIdFieldAndCurrentWwiseEvent",
            }],
        }])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "monoBehaviourAudioIdField")
        self.assertEqual(rows[0]["triggerRole"], "componentHitCallback")
        self.assertEqual(rows[0]["situation"]["componentType"], "Fixture.AudioComponent")
        self.assertEqual(rows[0]["situation"]["serializedFieldPathStatus"], None)
        self.assertEqual(
            rows[0]["runtimeActivationStatus"],
            "monoBehaviourComponentExecutionNotObserved",
        )

    def test_mono_behaviour_audio_field_roles_are_narrow_and_fail_closed(self) -> None:
        spawn = managed_literals.project_mono_behaviour_audio_field(
            "$._spawnAudioEvent._id",
            component_layout="Fixture.AudioComponent",
            component_type="Fixture.AudioComponent",
        )
        self.assertEqual(spawn["authoredFieldRole"], "componentSoundSpawn")
        self.assertEqual(spawn["serializedFieldName"], "_spawnAudioEvent")
        self.assertEqual(spawn["serializedFieldPathStatus"], "exact")
        self.assertEqual(spawn["componentLayoutStatus"], "exact")

        unknown = managed_literals.project_mono_behaviour_audio_field(
            "$._onHitAudioRtpc._id",
        )
        self.assertEqual(unknown["authoredFieldRole"], "componentSerializedAudioField")
        self.assertEqual(unknown["serializedFieldName"], "_onHitAudioRtpc")
        self.assertEqual(unknown["authoredFieldRoleEvidence"], "genericSerializedAudioField")

        state = managed_literals.project_mono_behaviour_audio_field(
            "$.stateList[0].audioPlayConfigs[0].normalAudiId._id",
        )
        self.assertEqual(state["authoredFieldRole"], "componentAnimationStateAudioConfig")
        self.assertEqual(state["componentLayout"], "serializedAnimationStateAudioConfig")
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field("$.normalAudiId._id")["authoredFieldRole"],
            "componentSerializedAudioField",
        )

        audio_key = managed_literals.project_mono_behaviour_audio_field("$._audioKey._id")
        self.assertEqual(audio_key["authoredFieldRole"], "componentSerializedAudioField")
        self.assertEqual(audio_key["authoredFieldRoleEvidence"], "genericSerializedAudioField")
        self.assertEqual(audio_key["serializedFieldRoleHint"], "componentAudioKey")
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field("$._entries[0].soundEvent._id")["authoredFieldRole"],
            "componentParticleSoundEvent",
        )
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field("$.waterDroneUIAudioData.aimableSoundEvent._id")["authoredFieldRole"],
            "componentWaterDroneAimableSound",
        )
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field("$._onEnableLoopAudioEvent._id")["authoredFieldRole"],
            "componentEnableLoopCallback",
        )

        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field(
                "$.references.RefIds[1].data.soundBase.soundFinish.hex",
            )["authoredFieldRole"],
            "componentFinish",
        )
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field(
                "$.references.RefIds[1].data.soundSpawn.hex",
            )["authoredFieldRole"],
            "componentSoundSpawn",
        )
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field(
                "$.waterDroneSourceDataDict._valueData[0].enterSoundName._id",
            )["authoredFieldRole"],
            "componentWaterDroneEnterSound",
        )
        self.assertEqual(
            managed_literals.project_mono_behaviour_audio_field(
                "$.waterTypeDataDict._valueData[0].startHitEvent._id",
            )["authoredFieldRole"],
            "componentWaterStartHitSound",
        )

        for unsupported_path, raw_field in (
            ("$.wrapper._spawnAudioEvent._id", "_spawnAudioEvent"),
            ("$.audioPlayConfigs[0].stateList[0].normalAudiId._id", "normalAudiId"),
            (
                "$.stateList[0].audioPlayConfigs[0].waterDroneUIAudioData.normalAudiId._id",
                "normalAudiId",
            ),
            ("$._spawnAudioEvent.hex", "_spawnAudioEvent"),
            ("$.waterDroneUIAudioData.aimableSoundEvent.value", "aimableSoundEvent"),
            ("$.waterTypeDataDict._valueData[0].startHitEvent._id.extra", "startHitEvent"),
        ):
            with self.subTest(unsupported_path=unsupported_path):
                projection = managed_literals.project_mono_behaviour_audio_field(
                    unsupported_path,
                    field_name=raw_field,
                )
                self.assertEqual(
                    projection["authoredFieldRole"],
                    "componentSerializedAudioField",
                )
                self.assertEqual(
                    projection["authoredFieldRoleEvidence"],
                    "genericSerializedAudioField",
                )
                self.assertEqual(
                    projection["serializedFieldDiagnostic"],
                    "serializedAudioFieldPathUnsupportedShape",
                )

        malformed = managed_literals.project_mono_behaviour_audio_field("")
        self.assertEqual(malformed["authoredFieldRole"], "componentSerializedAudioField")
        self.assertEqual(malformed["serializedFieldPathStatus"], "malformed")
        self.assertEqual(malformed["serializedFieldDiagnostic"], "serializedAudioFieldPathMalformed")

    def test_mono_behaviour_audio_multi_field_summary_preserves_event_and_runtime_boundary(self) -> None:
        contexts = [
            {
                "kind": "monoBehaviourAudioIdField",
                "authoredFieldRole": "componentSoundSpawn",
                "componentLayout": "serializedMonoBehaviourAudioIdField",
                "serializedFieldPath": "$._spawnAudioEvent._id",
                "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
            },
            {
                "kind": "monoBehaviourAudioIdField",
                "authoredFieldRole": "componentHitCallback",
                "componentLayout": "serializedMonoBehaviourAudioIdField",
                "serializedFieldPath": "$._onHitAudioEvent._id",
                "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
            },
        ]
        row = {
            "id": "au_fixture_multi_field",
            "name": "au_fixture_multi_field",
            "hash": 0x12345678,
            "category": "sfx",
            "categoryEvidence": "namePrefix",
            "foundInWwise": True,
            "contexts": contexts,
            "media": [],
            "evidence": [],
        }
        summary = event_summary.event_summary_row(row, "event_details/12.json")
        self.assertEqual(summary["category"], "sfx")
        self.assertEqual(summary["monoBehaviourAudioIdFieldCount"], 2)
        self.assertEqual(summary["monoBehaviourAudioIdFieldRoleCounts"], {
            "componentHitCallback": 1,
            "componentSoundSpawn": 1,
        })
        self.assertIn("componentSoundSpawn", summary["contextSearch"])
        triggers = audio_semantics._build_mono_behaviour_audio_id_trigger_contexts([row])
        self.assertEqual({trigger["triggerRole"] for trigger in triggers}, {
            "componentHitCallback", "componentSoundSpawn",
        })
        self.assertTrue(all(
            trigger["runtimeActivationStatus"] == "monoBehaviourComponentExecutionNotObserved"
            for trigger in triggers
        ))
        self.assertTrue(all(trigger["situation"]["worldPosition"] is None for trigger in triggers))

    def test_audio_frontend_component_field_role_search_and_detail_labels(self) -> None:
        source = (Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js").read_text(encoding="utf-8")
        self.assertIn("context.componentLayout", source)
        self.assertIn("context.componentType", source)
        self.assertIn("context.authoredFieldNameRaw", source)
        self.assertIn("serialized field ${context.authoredFieldNameRaw}", source)
        self.assertIn('context?.worldPositionStatus === "exact_transform_hierarchy"', source)

    def test_collects_typed_play_line_sound_managed_reference_payload(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            index = (
                root / "recovered/AnimeStudio-cli/StreamingAssets/object_index/parts"
                / "StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl"
            )
            index.parent.mkdir(parents=True)
            prefix = "$.references.RefIds[1]"
            index.write_text(json.dumps({
                "recordType": "object",
                "object": {"serializedFile": "CAB-line", "pathId": 101},
                "name": "Line Audio FX",
                "scalars": [
                    [prefix + ".type.class", "s", "PlayLineSound"],
                    [prefix + ".type.ns", "s", "Beyond.Gameplay"],
                    [prefix + ".type.asm", "s", "Gameplay.Beyond"],
                    [prefix + ".data.layout", "s", "Beyond.Gameplay.PlayLineSound"],
                    *[
                        [prefix + f".data.rawWords[{word_index}].hex", "s", value]
                        for word_index, value in enumerate((
                            "0x12345678", "0x87654321", "0x00000000",
                            "0x00000000", "0x00000001", "0x00000034",
                        ))
                    ],
                ],
                "sceneContext": {
                    "gameObjectName": "Line FX",
                    "hierarchyPath": ["Root", "Line FX"],
                },
            }) + "\n", encoding="utf-8")

            result = audio_semantics.collect_mono_behaviour_audio_id_contexts(
                root,
                {0x12345678, 0x87654321},
            )

            self.assertEqual(result["stats"]["eventContextOccurrences"], 2)
            self.assertEqual(result["stats"]["distinctEventHashes"], 2)
            spawn = result["eventContexts"]["#0x12345678"][0]
            self.assertEqual(spawn["authoredFieldRole"], "componentSoundSpawn")
            self.assertEqual(spawn["managedReferenceClass"], "PlayLineSound")
            self.assertEqual(spawn["managedReferencePayloadLength"], 24)
            self.assertEqual(spawn["gameObjectName"], "Line FX")
            finish = result["eventContexts"]["#0x87654321"][0]
            self.assertEqual(finish["authoredFieldRole"], "componentFinish")
            self.assertEqual(
                finish["evidence"],
                "exactSerializedPlayLineSoundPayloadAndCurrentWwiseEvent",
            )
            structured = list(audio_semantics._mono_play_line_sound_event_scalars({
                prefix + ".type.class": "PlayLineSound",
                prefix + ".type.ns": "Beyond.Gameplay",
                prefix + ".type.asm": "Gameplay.Beyond",
                prefix + ".data.layout": "Beyond.Gameplay.PlayLineSound",
                prefix + ".data.soundSpawn.hex": "0x12345678",
                prefix + ".data.soundFinish.hex": "0x87654321",
            }))
            self.assertEqual([row[2] for row in structured], ["soundSpawn", "soundFinish"])
            self.assertTrue(all(
                row[3]["managedReferenceDecodeStatus"] == "strictStructuredDecoder"
                for row in structured
            ))

    def test_audio_global_config_context_is_exposed_as_static_trigger(self) -> None:
        rows = audio_semantics._build_audio_global_config_trigger_contexts([{
            "id": "hashed-event:0x12345678",
            "hash": 0x12345678,
            "category": "unknown",
            "foundInWwise": True,
            "playbackRole": "mixedPlaybackAndControl",
            "possibleMediaCount": 0,
            "media": [],
            "contexts": [{
                "kind": "audioGlobalConfigEventHash",
                "semanticRole": "audioStateTransitionEvent",
                "path": "audioStatesIn._valueData[0]._ids[0]",
                "stateDirection": "enter",
                "audioStateMask": 512,
                "sourceRoot": "Persistent",
                "serializedFile": "CAB-global",
                "pathId": 77,
                "source": "recovered/object-index.jsonl",
                "evidence": "exactSerializedAudioGlobalConfigObjectIndexScalar",
                "triggerRequestEvidence": ["serializedGlobalAudioPolicy"],
            }],
        }])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["semanticKind"], "audioGlobalConfigEventHash")
        self.assertEqual(rows[0]["situation"]["stateDirection"], "enter")
        self.assertEqual(rows[0]["situation"]["audioStateMask"], 512)
        self.assertEqual(
            rows[0]["selection"]["triggerBindingStatus"],
            "exactSerializedGlobalAudioPolicyAudioId",
        )
        self.assertEqual(
            rows[0]["runtimeActivationStatus"],
            "runtimeLifecycleConditionRequired",
        )

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

            contexts = table_contexts.collect_table_contexts(root, runtime_model)

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
                table_contexts.collect_table_audio_events(root)[0],
                {"au_int_door_open", "au_item_ore_collect", "au_music_main", "au_sfx_init"},
            )
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)
            (component_root / "data_int_fixture.json").write_bytes(b"fixture")
            table_path = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveTable.json"
            table_path.parent.mkdir(parents=True, exist_ok=True)
            table_path.write_bytes(b"table-fixture")

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

            def decode_table_fixture(data: bytes) -> dict:
                self.assertEqual(data, b"table-fixture")
                return {
                    "coreTemplatePaths": {
                        "int_fixture": "Data/Json/Interactive/InteractiveData/data_int_fixture.json",
                    },
                    "objectToTemplate": {
                        "int_fixture": "int_fixture",
                        "int_fixture_alias": "int_fixture",
                    },
                }

            component_contexts = interactive_components.collect_interactive_component_contexts(
                root,
                decoder=decode_fixture,
                table_decoder=decode_table_fixture,
            )
            lifecycle = component_contexts["au_int_fixture_break"][0]
            self.assertEqual(lifecycle["triggerStateName"], "Destroy")
            self.assertEqual(lifecycle["ownerId"], "data_int_fixture")
            self.assertEqual(lifecycle["interactiveTemplateIds"], ["int_fixture"])
            self.assertEqual(
                lifecycle["interactiveTemplatePath"],
                "Data/Json/Interactive/InteractiveData/data_int_fixture.json",
            )
            self.assertEqual(
                lifecycle["interactiveConsumerIds"],
                ["int_fixture", "int_fixture_alias"],
            )
            self.assertEqual(
                lifecycle["templateAssociationStatus"],
                "exactInteractiveTableTemplatePath",
            )
            custom_component = component_contexts["au_int_fixture_open"][0]
            self.assertEqual(custom_component["triggerCustomState"], "panel_open")
            self.assertEqual(custom_component["componentIndex"], 2)

    def test_interactive_audio_key_property_is_exact_but_runtime_consumer_stays_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)

            def string(value: str) -> bytes:
                raw = value.encode("utf-8")
                return pack("<I", len(raw)) + raw

            event_id = "au_int_fixture_moving_start"
            property_map = b"".join((
                pack("<I", 1), bytes((2,)), string("audio_key_start"),
                bytes((2,)), pack("<iI", 7, 1), bytes((2,)), pack("<q", 0), string(event_id),
            ))
            component = b"".join((
                bytes((0xF5, 3)),
                pack("<I", 0xFFFFFFFF), pack("<I", 1), bytes((20,)), bytes(60),
                property_map,
                bytes((0, 0)),
            ))
            (component_root / "data_int_fixture_mover.json").write_bytes(component)

            contexts = interactive_components.collect_interactive_component_contexts(root)

            row = contexts[event_id][0]
            self.assertEqual(row["kind"], "interactiveComponentPropertyAudio")
            self.assertEqual(row["ownerId"], "data_int_fixture_mover")
            self.assertEqual(row["componentType"], "Core_TriggerZoneComponentForIntData")
            self.assertEqual(row["componentTag"], "0x00f5")
            self.assertEqual(row["audioPropertyKey"], "audio_key_start")
            self.assertEqual(row["evidence"], "exactDecodedMemoryPackInteractiveAudioProperty")
            self.assertEqual(row["triggerRuntimeActivationStatuses"], [
                "runtimePropertyConsumerUnresolved",
                "runtimeEventPostingNotObserved",
            ])
            trigger_rows = audio_semantics._build_interactive_property_audio_trigger_contexts([{
                "id": event_id,
                "hash": 123,
                "category": "sfx",
                "foundInWwise": True,
                "playbackRole": "playback",
                "possibleMediaCount": 0,
                "media": [],
                "contexts": [row],
            }])
            self.assertEqual(len(trigger_rows), 1)
            self.assertEqual(trigger_rows[0]["semanticKind"], "interactiveComponentPropertyAudio")
            self.assertEqual(trigger_rows[0]["situation"]["audioPropertyKey"], "audio_key_start")
            self.assertEqual(
                trigger_rows[0]["selection"]["runtimeSelectionStatus"],
                "runtimeEventPostingNotObserved",
            )

    def test_standalone_interactive_property_map_recovers_hit_role_without_component_guess(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)

            def string(value: str) -> bytes:
                raw = value.encode("utf-8")
                return pack("<I", len(raw)) + raw

            event_id = "au_int_fixture_shield_hit"
            property_map = b"".join((
                pack("<I", 1), bytes((2,)), string("hit_sound_event"),
                bytes((2,)), pack("<iI", 7, 1), bytes((2,)), pack("<q", 0), string(event_id),
            ))
            (component_root / "data_int_fixture_shield.json").write_bytes(
                bytes(24) + property_map + bytes(8)
            )

            contexts = interactive_components.collect_interactive_component_contexts(root)

            row = contexts[event_id][0]
            self.assertEqual(row["kind"], "interactivePropertyMapAudio")
            self.assertEqual(row["audioPropertyKey"], "hit_sound_event")
            self.assertEqual(row["componentResolutionStatus"], "containingComponentUnresolved")
            self.assertEqual(row["triggerRuntimeActivationStatuses"], [
                "runtimePropertyConsumerUnresolved",
                "runtimeEventPostingNotObserved",
            ])

    def test_interactive_template_config_audio_recovers_exact_authored_role(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)
            (component_root / "data_int_fixture_rabbit.json").write_bytes(b"fixture")
            event_id = "au_int_fixture_escape"

            def decode_fixture(_path: Path, _data: bytes, _size: int) -> dict:
                return {"decoded": {
                    "componentAudioComponents": [],
                    "componentAudioPropertyComponents": [],
                    "standaloneAudioPropertyMaps": [],
                    "templateConfigProperties": {
                        "configPropertiesOffset": "0x100",
                        "configPropertiesEndOffset": "0x180",
                        "audioPropertyRows": [{
                            "key": "audio_escape",
                            "events": [event_id],
                            "valueType": 7,
                            "identityKind": "wwiseEvent",
                        }],
                    },
                }}

            contexts = interactive_components.collect_interactive_component_contexts(
                root, decoder=decode_fixture
            )

            row = contexts[event_id][0]
            self.assertEqual(row["kind"], "interactiveTemplateConfigAudio")
            self.assertEqual(row["ownerId"], "data_int_fixture_rabbit")
            self.assertEqual(row["audioPropertyKey"], "audio_escape")
            self.assertEqual(row["propertyMapOffset"], "0x100")
            self.assertEqual(
                row["evidence"],
                "exactDecodedMemoryPackInteractiveTemplateConfigProperty",
            )
            trigger_rows = audio_semantics._build_interactive_property_audio_trigger_contexts([{
                "id": event_id,
                "hash": 123,
                "category": "sfx",
                "foundInWwise": True,
                "playbackRole": "playback",
                "possibleMediaCount": 0,
                "media": [],
                "contexts": [row],
            }])
            self.assertEqual(trigger_rows[0]["semanticKind"], "interactiveTemplateConfigAudio")
            self.assertEqual(trigger_rows[0]["situation"]["audioPropertyKey"], "audio_escape")

    def test_interactive_template_action_audio_preserves_action_and_runtime_gates(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)
            (component_root / "data_int_fixture_platform.json").write_bytes(b"fixture")
            event_id = "au_int_fixture_platform_loop"

            def decode_fixture(_path: Path, _data: bytes, _size: int) -> dict:
                return {"decoded": {
                    "componentAudioComponents": [],
                    "componentAudioPropertyComponents": [],
                    "standaloneAudioPropertyMaps": [],
                    "templateConfigProperties": {},
                    "templateActionMapAudio": {
                        "audioActions": [{
                            "actionMapRole": "actionList#7 root",
                            "recordOffset": "0x65d",
                            "payloadOffset": "0x67d",
                            "unionTag": "0x0352",
                            "serializedMemberCount": 12,
                            "localId": 22,
                            "uid": "6f60a989",
                            "nextId": -1,
                            "action": "PlayAudioOnTarget",
                            "fields": {
                                "stopOnRelease": {"value": True},
                                "target": {"bindingKind": "dynamic", "paramSource": 1001},
                            },
                            "eventBindings": [{
                                "eventName": event_id,
                                "role": "play",
                                "sourceField": "_audioKey",
                            }],
                        }],
                    },
                }}

            contexts = interactive_components.collect_interactive_component_contexts(
                root, decoder=decode_fixture
            )

            row = contexts[event_id][0]
            self.assertEqual(row["kind"], "interactiveTemplateActionAudio")
            self.assertEqual(row["audioAction"], "PlayAudioOnTarget")
            self.assertEqual(row["actionMapRole"], "actionList#7 root")
            self.assertEqual(row["actionLocalId"], 22)
            self.assertTrue(row["stopOnRelease"])
            self.assertEqual(row["targetBindingKind"], "dynamic")
            trigger_rows = audio_semantics._build_interactive_property_audio_trigger_contexts([{
                "id": event_id,
                "hash": 123,
                "category": "sfx",
                "foundInWwise": True,
                "playbackRole": "playback",
                "possibleMediaCount": 0,
                "media": [],
                "contexts": [row],
            }])
            trigger = trigger_rows[0]
            self.assertEqual(trigger["semanticKind"], "interactiveTemplateActionAudio")
            self.assertEqual(trigger["triggerRole"], "authoredInteractiveActionAudioRequest")
            self.assertEqual(trigger["action"]["action"], "PlayAudioOnTarget")
            self.assertEqual(trigger["action"]["runtimeActivationStatus"], "runtimeActionActivationUnobserved")

    def test_interactive_embedded_action_audio_keeps_outer_field_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            component_root = root / "structured/StreamingAssets/Data/Json/Interactive/InteractiveData"
            component_root.mkdir(parents=True)
            (component_root / "data_int_fixture_wall.json").write_bytes(b"fixture")
            event_id = "au_int_fixture_wall_hit"

            def decode_fixture(_path: Path, _data: bytes, _size: int) -> dict:
                return {"decoded": {
                    "componentAudioComponents": [],
                    "componentAudioPropertyComponents": [],
                    "standaloneAudioPropertyMaps": [],
                    "templateConfigProperties": {},
                    "templateActionMapAudio": {},
                    "embeddedActionMapAudioActions": [{
                        "actionMapOffset": "0x793",
                        "actionMapListCounts": {"actionList": 9, "getterList": 20, "headerList": 1},
                        "actionMapRole": "actionList#9 linked",
                        "recordOffset": "0xca3",
                        "payloadOffset": "0xcc3",
                        "unionTag": "0x034c",
                        "serializedMemberCount": 12,
                        "localId": 9,
                        "uid": "91763d7d",
                        "nextId": -1,
                        "action": "PlayAudiAtPosition",
                        "fields": {
                            "stopOnRelease": {"value": True},
                            "position": {"bindingKind": "dynamic", "paramSource": -1},
                        },
                        "eventBindings": [{
                            "eventName": event_id,
                            "role": "play",
                            "sourceField": "_key",
                        }],
                    }],
                }}

            contexts = interactive_components.collect_interactive_component_contexts(
                root, decoder=decode_fixture
            )

            row = contexts[event_id][0]
            self.assertEqual(row["kind"], "interactiveEmbeddedActionAudio")
            self.assertEqual(row["componentResolutionStatus"], "containingSerializedFieldUnresolved")
            self.assertEqual(row["audioAction"], "PlayAudiAtPosition")
            self.assertEqual(row["actionMapOffset"], "0x793")
            self.assertEqual(row["targetParameterKind"], "position")
            self.assertEqual(row["targetBindingKind"], "dynamic")

    def test_global_audio_policy_falls_back_to_object_index_scalars(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            index_path = (
                root / "recovered/AnimeStudio-cli/Persistent/object_index/parts"
                / "Persistent_animestudio_json_by_type_MonoBehaviour.jsonl"
            )
            index_path.parent.mkdir(parents=True)
            index_path.write_text(json.dumps({
                "recordType": "object",
                "object": {
                    "serializedFile": "CAB-global",
                    "pathId": 77,
                },
                "name": "AudioGlobalConfig",
                "script": {
                    "fullName": "Beyond.Gameplay.Audio.AudioGlobalConfig",
                },
                "scalars": [
                    ["$.gameplayMusicStartEvent", "s", "au_music_main"],
                    ["$.globalEventLeaveMainGame._id", "i", -2],
                    ["$.audioStatesIn._keyData[0]", "i", 512],
                    ["$.audioStatesIn._valueData[0]._ids[0]._id", "i", 123],
                    ["$.charInitEvent._keyData[0]", "s", "chr_test"],
                    ["$.charInitEvent._valueData[0]._id", "i", 456],
                ],
                "scalarsTruncated": True,
            }) + "\n", encoding="utf-8")

            contexts = table_contexts.collect_table_contexts(root)

            music = contexts["au_music_main"][0]
            self.assertEqual(music["semanticRole"], "gameplayMusicStartEvent")
            leave = contexts["#0xfffffffe"][0]
            self.assertEqual(leave["semanticRole"], "leaveMainGameEvent")
            self.assertEqual(leave["serializedFile"], "CAB-global")
            self.assertTrue(leave["scalarsTruncated"])
            state = contexts["#0x0000007b"][0]
            self.assertEqual(state["stateDirection"], "enter")
            self.assertEqual(state["audioStateMask"], 512)
            owner = contexts["#0x000001c8"][0]
            self.assertEqual(owner["ownerKind"], "character")
            self.assertEqual(owner["ownerId"], "chr_test")

    def test_interactive_table_mirror_conflict_keeps_component_owner_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            component_rel = "Data/Json/Interactive/InteractiveData/data_int_fixture.json"
            for source_root in ("Persistent", "StreamingAssets"):
                component_path = root / "structured" / source_root / component_rel
                component_path.parent.mkdir(parents=True, exist_ok=True)
                component_path.write_bytes(b"fixture")
                table_path = root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
                table_path.parent.mkdir(parents=True, exist_ok=True)
                table_path.write_bytes(source_root.encode("ascii"))

            def decode_fixture(_path: Path, _data: bytes, _size: int) -> dict:
                return {"decoded": {"componentAudioComponents": [{
                    "index": 0,
                    "audioRows": [{"state": 13, "stateName": "Destroy", "events": ["au_int_fixture_break"]}],
                    "customRows": [],
                }]}}

            def unexpected_table_decode(_data: bytes) -> dict:
                raise AssertionError("conflicting mirrors must fail closed before table decode")

            contexts = interactive_components.collect_interactive_component_contexts(
                root,
                decoder=decode_fixture,
                table_decoder=unexpected_table_decode,
            )
            row = contexts["au_int_fixture_break"][0]
            self.assertEqual(row["templateAssociationStatus"], "interactiveTableTemplatePathUnresolved")
            self.assertEqual(row["interactiveTemplateIds"], [])
            self.assertEqual(row["interactiveConsumerIds"], [])

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
            rows, _, _ = event_projection.build_event_rows({"eventNames": [], "events": [], "eventEvidence": []}, contexts)
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
            selector_catalog = payload["controlCatalog"]
            self.assertEqual(selector_catalog["counts"]["wwiseSelectorGroupsCensused"], 56)
            self.assertEqual(selector_catalog["counts"]["wwiseSelectorGroupsWithRuntimeSetter"], 2)
            self.assertEqual(selector_catalog["counts"]["wwiseSelectorGroupsPublished"], 15)
            self.assertEqual(selector_catalog["counts"]["wwiseMusicStateGroupsPublished"], 10)
            selector_groups = {
                row["groupId"]: row for row in selector_catalog["wwiseSelectorGroups"]
            }
            factory_mode = selector_groups[0x7ACDACAF]
            self.assertEqual(factory_mode["runtimeScope"], "audioObject")
            self.assertEqual(factory_mode["runtimeSetter"]["callerMethodIndex"], 39714)
            self.assertEqual(
                [row["valueId"] for row in factory_mode["values"]],
                [1, 2, 4, 8, 16, 32, 64],
            )
            self.assertEqual(
                [row["resolvedValueId"] for row in factory_mode["values"]],
                [0x4527C498, 0xF3A9ACD5, 0x228CF0D8, 0xFB9CA5C8,
                 0x59A68236, 0x2F715D31, 0x8353CA3C],
            )
            self.assertEqual(
                [row["resolvedValueName"] for row in factory_mode["values"]],
                ["normal", "liquid", "gas", "gasliquid", "gastrans",
                 "liquidtrans", "solidtrans"],
            )
            self.assertEqual(
                factory_mode["valueResolverStatus"],
                "exactAllSevenInputsMapToWwiseValueHashes",
            )
            gamepad = selector_groups[0xF6699CF4]
            self.assertEqual(gamepad["groupType"], "state")
            self.assertEqual(gamepad["values"][0]["semanticName"], "XInput")
            self.assertEqual(gamepad["values"][1]["semanticName"], "ScePad")
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

    def test_patrol_sub_action_audio_context_preserves_exact_owner_and_unresolved_event(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root = root / "export_full"
            webui_root = root / "webui"
            path = (
                export_root
                / "structured/Persistent/Data/Json/LevelData/map02_lv002/fixture.json"
            )
            path.parent.mkdir(parents=True)
            path.write_bytes(patrol_leveldata_fixture())

            semantics = audio_semantics.collect_patrol_sub_action_audio_semantics(export_root)
            stats = semantics["stats"]
            self.assertEqual("complete", stats["status"])
            self.assertEqual(1, stats["sourceFiles"])
            self.assertEqual(1, stats["decodedFiles"])
            self.assertEqual(1, stats["patrolRows"])
            self.assertEqual(1, stats["patrolPoints"])
            self.assertEqual(1, stats["patrolActions"])
            self.assertEqual(1, stats["playAudioContexts"])
            context = semantics["eventContexts"]["#0x0b1279e0"][0]
            self.assertEqual("patrolSubActionPlayAudio", context["kind"])
            self.assertEqual(280007, context["patrolId"])
            self.assertEqual(0, context["pointIndex"])
            self.assertEqual(0, context["actionIndex"])
            self.assertEqual("patrolPointActionExecutionNotObserved", context["runtimeActivationStatus"])

            payload = audio_semantics.build_audio_semantic_data(
                {"eventNames": [], "events": [], "eventEvidence": [], "entries": []},
                language="CN",
                export_root=export_root,
                webui_root=webui_root,
                metadata_path=None,
            )
            self.assertEqual(audio_semantics.AUDIO_SEMANTIC_SCHEMA_VERSION, payload["schemaVersion"])
            self.assertEqual(1, payload["counts"]["patrolSubActionPlayAudioEvents"])
            self.assertEqual(1, payload["counts"]["patrolSubActionPlayAudioContexts"])
            self.assertEqual(0, payload["counts"]["patrolSubActionPlayAudioEventsFoundInWwise"])
            self.assertEqual(1, payload["counts"]["patrolSubActionPlayAudioEventsUnresolved"])
            self.assertEqual(
                1,
                payload["triggerCatalog"]["patrolSubActionPlayAudio"]["decodedFiles"],
            )
            event_summaries = json.loads(
                (webui_root / "data/lang/CN/audio/events.json").read_text(encoding="utf-8")
            )["events"]
            summary = next(
                row for row in event_summaries
                if row["id"] == "hashed-event:0x0b1279e0"
            )
            self.assertEqual("sfx", summary["category"])
            self.assertEqual("exactPatrolSubPlayAudioData", summary["categoryEvidence"])
            self.assertIn("patrolSubActionPlayAudio", summary["contextKinds"])
            self.assertIn("280007", summary["contextSearch"])

    def test_char_interact_audio_context_preserves_phase_owner_and_numeric_join(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root = root / "export_full"
            webui_root = root / "webui"
            event_hash = 0x12345678
            for source_root in ("StreamingAssets", "Persistent"):
                path = (
                    export_root / "structured" / source_root
                    / "Data/Json/CharInteractPerformCfgs/CharIntPerform_fixture.json"
                )
                path.parent.mkdir(parents=True)
                path.write_bytes(char_interact_fixture(event_hash))

            semantics = audio_semantics.collect_char_interact_audio_semantics(export_root)
            stats = semantics["stats"]
            self.assertEqual(stats["status"], "complete")
            self.assertEqual(stats["physicalFiles"], 2)
            self.assertEqual(stats["ownerFiles"], 1)
            self.assertEqual(stats["candidateOwners"], 1)
            self.assertEqual(stats["audioEventActions"], 1)
            self.assertEqual(stats["actionPhaseCounts"], {"startActions": 1})
            context = semantics["eventContexts"]["#0x12345678"][0]
            self.assertEqual(context["kind"], "charInteractAudioEvent")
            self.assertEqual(context["charInteractPerformId"], "CharIntPerform_fixture")
            self.assertEqual(context["actionPhase"], "startActions")
            self.assertEqual(context["actionIndex"], 0)
            self.assertEqual(context["logicId"], 9)
            self.assertEqual(context["sourceOffset"], 80)
            self.assertEqual(context["runtimeOwnerStatus"], "authoredPerformConfigOwnerOnly")
            self.assertEqual(
                context["runtimeActivationStatus"],
                "charInteractPerformRuntimeExecutionNotObserved",
            )

            payload = audio_semantics.build_audio_semantic_data(
                {
                    "eventNames": ["au_int_fixture"],
                    "events": [],
                    "eventEvidence": [{
                        "eventId": "au_int_fixture",
                        "eventHash": event_hash,
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
            self.assertEqual(payload["counts"]["charInteractAudioEvents"], 1)
            self.assertEqual(payload["counts"]["charInteractAudioContexts"], 1)
            self.assertEqual(payload["counts"]["charInteractAudioEventsFoundInWwise"], 1)
            self.assertEqual(payload["counts"]["charInteractAudioEventsUnresolved"], 0)
            self.assertEqual(payload["triggerCatalog"]["charInteractAudio"]["audioEventActions"], 1)
            summaries = json.loads(
                (webui_root / "data/lang/CN/audio/events.json").read_text(encoding="utf-8")
            )["events"]
            summary = next(row for row in summaries if row["id"] == "au_int_fixture")
            self.assertIn("charInteractAudioEvent", summary["contextKinds"])
            self.assertIn("CharIntPerform_fixture", summary["contextSearch"])

    def test_physics_audio_contexts_preserve_aliases_offsets_and_rtpc_control(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            webui_root = Path(raw_root) / "webui"
            template_rel = "Data/Json/Interactive/InteractiveData/data_int_kickable_ball.json"
            for source_root in ("StreamingAssets", "Persistent"):
                table_path = export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
                table_path.parent.mkdir(parents=True, exist_ok=True)
                table_path.write_bytes(b"same-table")
                template_path = export_root / "structured" / source_root / template_rel
                template_path.parent.mkdir(parents=True, exist_ok=True)
                template_path.write_bytes(b"same-template")

            def table_decoder(data: bytes) -> dict:
                self.assertEqual(data, b"same-table")
                return {
                    "coreTemplateCount": 1,
                    "interactiveDataCount": 2,
                    "coreTemplatePaths": {"int_kickable_ball": template_rel},
                    "objectToTemplate": {
                        "int_kickable_ball": "int_kickable_ball",
                        "int_tumble_weed": "int_kickable_ball",
                    },
                }

            property_rows = []
            for index, (authored_key, runtime_field, value, event_role, rtpc_role) in enumerate((
                ("on_start_move_audio_event", "onStartMoveAudioEvent", "au_int_ball_start", "movementStart", ""),
                ("on_stop_move_audio_event", "onStopMoveAudioEvent", "au_int_ball_stop", "movementStop", ""),
                ("on_hit_audio_event", "onHitAudioEvent", "au_int_ball_hit", "movementHit", ""),
                ("on_rotation_loop_audio_event", "onRotationLoopAudioEvent", "", "rotationLoop", ""),
                ("on_rotation_one_shot_audio_event", "onRotationOneShotAudioEvent", "au_int_ball_scatter", "rotationOneShot", ""),
                ("on_rotation_ground_loop_audio_event", "onRotationGroundLoopAudioEvent", "au_int_ball_loop", "groundRotationLoop", ""),
                ("on_rotation_ground_one_shot_audio_event", "onRotationGroundOneShotAudioEvent", "au_int_ball_ground", "groundRotationOneShot", ""),
                ("velocity_sqr_rtpc", "velocitySqrRtpc", "rtpc_int_ball_speed", "", "movementVelocitySquared"),
                ("acceleration_sqr_rtpc", "accelerationSqrRtpc", "", "", "movementAccelerationSquared"),
                ("angular_velocity_sqr_rtpc", "angularVelocitySqrRtpc", "", "", "rotationAngularVelocitySquared"),
            )):
                property_rows.append({
                    "index": index,
                    "propertySourceOffset": 0x900 + index * 16,
                    "valueSourceOffset": 0x908 + index * 16,
                    "authoredKey": authored_key,
                    "runtimeField": runtime_field,
                    "eventRole": event_role,
                    "rtpcRole": rtpc_role,
                    "valueType": 7,
                    "valueTypeName": "string",
                    "value": value,
                })

            def component_decoder(data: bytes) -> list[dict]:
                self.assertEqual(data, b"same-template")
                return [{
                    "sourceOffset": 0x8C7,
                    "propertyMapOffset": 0x8C9,
                    "endOffset": 0xE5B,
                    "unionTag": 0xBE,
                    "unionTagHex": "0x00be",
                    "memberCount": 1,
                    "propertyCount": 21,
                    "schemaMappingId": "fixture-memorypack",
                    "runtimeMappingId": "fixture-runtime",
                    "schemaStatus": "exact-current-complete-property-map",
                    "properties": property_rows,
                }]

            semantics = authored_components.collect_physics_audio_semantics(
                export_root,
                component_decoder=component_decoder,
                table_decoder=table_decoder,
            )

            self.assertEqual(semantics["stats"]["status"], "complete")
            self.assertEqual(semantics["stats"]["physicsAudioEventContexts"], 6)
            self.assertEqual(semantics["stats"]["physicsAudioRtpcControls"], 1)
            self.assertEqual(semantics["stats"]["physicsAudioConsumerIdentities"], 2)
            self.assertEqual(semantics["stats"]["physicsAudioAliasIdentities"], 1)
            start = semantics["eventContexts"]["au_int_ball_start"][0]
            self.assertEqual(start["definitionOwnerId"], "int_kickable_ball")
            self.assertEqual(start["consumerIds"], ["int_kickable_ball", "int_tumble_weed"])
            self.assertEqual(start["componentTag"], 0xBE)
            self.assertEqual(start["serializedMemberCount"], 1)
            self.assertEqual(start["sourceOffset"], 0x8C7)
            self.assertEqual(start["propertySourceOffset"], 0x900)
            self.assertEqual(start["authoredProperty"], "on_start_move_audio_event")
            self.assertEqual(start["runtimeField"], "onStartMoveAudioEvent")
            self.assertEqual(start["runtimeActivationStatus"], "physicsAudioRuntimeExecutionNotObserved")
            rtpc = semantics["rtpcParameters"][0]
            self.assertEqual(rtpc["parameterName"], "rtpc_int_ball_speed")
            self.assertEqual(rtpc["controlRole"], "movementVelocitySquared")

            with patch.object(
                authored_components,
                "collect_physics_audio_semantics",
                return_value=semantics,
            ):
                payload = audio_semantics.build_audio_semantic_data(
                    {
                        "eventNames": ["au_int_ball_start"],
                        "events": [],
                        "eventEvidence": [{
                            "eventId": "au_int_ball_start",
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
            self.assertEqual(payload["counts"]["physicsAudioEvents"], 6)
            self.assertEqual(payload["counts"]["physicsAudioEventsFoundInWwise"], 1)
            self.assertEqual(payload["counts"]["physicsAudioEventsUnresolved"], 5)
            self.assertEqual(payload["controlCatalog"]["counts"]["physicsAudioRtpcParameters"], 1)
            self.assertEqual(
                payload["controlCatalog"]["physicsAudioRtpcParameters"][0]["parameterName"],
                "rtpc_int_ball_speed",
            )
            summaries = json.loads(
                (webui_root / "data/lang/CN/audio/events.json").read_text(encoding="utf-8")
            )["events"]
            start_summary = next(row for row in summaries if row["id"] == "au_int_ball_start")
            self.assertIn("physicsAudioComponentEvent", start_summary["contextKinds"])
            self.assertIn("int_tumble_weed", start_summary["contextSearch"])
            self.assertIn("on_start_move_audio_event", start_summary["contextSearch"])

    def test_model_view_state_audio_preserves_owner_chain_and_control_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            webui_root = Path(raw_root) / "webui"
            controller_id = "fixture_postmodel"
            controller_rel = "Data/Json/Interactive/ModelViewStateControllerData/fixture.json"
            template_rel = "Data/Json/Interactive/InteractiveData/data_fixture.json"
            for source_root in ("StreamingAssets", "Persistent"):
                controller_path = export_root / "structured" / source_root / controller_rel
                controller_path.parent.mkdir(parents=True, exist_ok=True)
                controller_path.write_bytes(b"same-controller")
                table_path = export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
                table_path.parent.mkdir(parents=True, exist_ok=True)
                table_path.write_bytes(b"same-table")
                template_path = export_root / "structured" / source_root / template_rel
                template_path.parent.mkdir(parents=True, exist_ok=True)
                template_path.write_bytes(b"prefix" + mp_string(controller_id) + b"suffix")

            event_hash = identifiers.audio_hash_generator_compute("au_mv_event")
            signed_event_hash = event_hash if event_hash < 0x80000000 else event_hash - 0x100000000
            common = {
                "modelAnimatorIndex": 0,
                "modelAnimatorName": "P_fixture",
                "layerIndex": 1,
                "layerFsmIndex": 3,
                "layerName": "audioLayer",
                "stateIndex": 2,
                "stateName": "Rotating",
                "stateType": 4,
                "behaviorIndex": 0,
                "memberCount": 14,
                "canLoopActive": False,
                "needForceExecute": True,
                "normalizedTimeFlowBasedActive": False,
                "time": 0.25,
                "timeFlowSwitch": 2,
                "sourceOffset": 0x401,
                "endOffset": 0x450,
            }
            behaviors = [
                {
                    **common, "unionTag": 1, "unionTagHex": "0x0001",
                    "behaviorType": 1, "behaviorKind": "event",
                    "audioNodeName": "AudioPoint", "customAudioId": "",
                    "eAudioTriggerState": 1, "isCustom": False, "isDirectlyPlay": True,
                    "normalAudioId": signed_event_hash, "stopOnEnd": True,
                    "transitionTime": 200,
                },
                {
                    **common, "unionTag": 2, "unionTagHex": "0x0002",
                    "behaviorType": 8, "behaviorKind": "positionEvent",
                    "audioNodeName": "Position", "customAudioId": "",
                    "eAudioTriggerState": 2, "isCustom": False, "isDirectlyPlay": True,
                    "normalAudioId": 1348303159, "stopOnEnd": False,
                    "transitionTime": 300,
                },
                {
                    **common, "unionTag": 2, "unionTagHex": "0x0002",
                    "behaviorType": 8, "behaviorKind": "positionEvent",
                    "audioNodeName": "Position", "customAudioId": "custom_position",
                    "eAudioTriggerState": 3, "isCustom": True, "isDirectlyPlay": False,
                    "normalAudioId": 123, "stopOnEnd": False,
                    "transitionTime": 300,
                },
                {
                    **common, "unionTag": 2, "unionTagHex": "0x0002",
                    "behaviorType": 8, "behaviorKind": "positionEvent",
                    "audioNodeName": "Position", "customAudioId": "",
                    "eAudioTriggerState": 4, "isCustom": False, "isDirectlyPlay": False,
                    "normalAudioId": 456, "stopOnEnd": False,
                    "transitionTime": 300,
                },
                {
                    **common, "unionTag": 1, "unionTagHex": "0x0001",
                    "behaviorType": 1, "behaviorKind": "event",
                    "audioNodeName": "AudioPoint", "customAudioId": "custom_portal",
                    "eAudioTriggerState": 1, "isCustom": True, "isDirectlyPlay": False,
                    "normalAudioId": 0, "stopOnEnd": False, "transitionTime": 200,
                },
                {
                    **common, "unionTag": 3, "unionTagHex": "0x0003",
                    "memberCount": 13, "behaviorType": 9, "behaviorKind": "rtpc",
                    "audioNodeName": "AudioPoint", "audioRTPCSetValue": 0.5,
                    "audioRTPCValue": "au_rtpc_int_delta_progress",
                    "rtpcBehaviourType": 2, "continuousTick": True,
                    "dependBlackBoard": True, "dependFloatKey": "Progress",
                },
                {
                    **common, "unionTag": 4, "unionTagHex": "0x0004",
                    "memberCount": 12, "behaviorType": 13, "behaviorKind": "spatialAudio",
                    "continuous": False, "dependBlackBoard": False,
                    "dependFloatKey": "", "directSet": True,
                    "targetClosePercentage": 0.75, "totalTime": 1.5,
                },
            ]

            def controller_decoder(data: bytes) -> dict:
                self.assertEqual(data, b"same-controller")
                return {
                    "modelId": controller_id,
                    "audioBehaviors": behaviors,
                    "schemaMappingId": "fixture-model-view-memorypack",
                    "runtimeMappingId": "fixture-model-view-runtime",
                    "schemaStatus": "exact-current-complete",
                }

            def table_decoder(data: bytes) -> dict:
                self.assertEqual(data, b"same-table")
                return {
                    "coreTemplatePaths": {"int_fixture": template_rel},
                    "objectToTemplate": {
                        "int_fixture": "int_fixture",
                        "int_fixture_alias": "int_fixture",
                    },
                }

            semantics = authored_components.collect_model_view_state_audio_semantics(
                export_root,
                controller_decoder=controller_decoder,
                table_decoder=table_decoder,
            )

            self.assertEqual(semantics["stats"]["status"], "complete")
            self.assertEqual(semantics["stats"]["audioBehaviorCount"], 7)
            self.assertEqual(semantics["stats"]["normalEventContextCount"], 1)
            self.assertEqual(semantics["stats"]["positionDirectEventBehaviorCount"], 1)
            self.assertEqual(semantics["stats"]["positionCustomStateSwitchCount"], 1)
            self.assertEqual(semantics["stats"]["positionEntityStateSwitchCount"], 1)
            self.assertEqual(len(semantics["positionedControls"]), 2)
            self.assertEqual(semantics["stats"]["customAudioControlCount"], 1)
            self.assertEqual(len(semantics["rtpcParameters"]), 1)
            self.assertEqual(len(semantics["spatialControls"]), 1)
            event = semantics["eventContexts"][identifiers.event_hash_context_key(event_hash)][0]
            self.assertEqual(event["modelAnimatorName"], "P_fixture")
            self.assertEqual(event["layerName"], "audioLayer")
            self.assertEqual(event["stateName"], "Rotating")
            self.assertEqual(event["behaviorTagHex"], "0x0001")
            self.assertEqual(event["interactiveTemplateIds"], ["int_fixture"])
            self.assertEqual(event["interactiveConsumerIds"], ["int_fixture", "int_fixture_alias"])
            self.assertEqual(
                event["templateAssociationStatus"],
                "exactSerializedControllerIdReferencePropertyUnresolved",
            )
            self.assertEqual(
                semantics["customAudioControls"][0]["wwiseEventStatus"],
                "notPromotedToEvent",
            )
            self.assertNotIn("custom_portal", semantics["eventContexts"])

            with patch.object(
                authored_components,
                "collect_model_view_state_audio_semantics",
                return_value=semantics,
            ):
                payload = audio_semantics.build_audio_semantic_data(
                    {
                        "eventNames": ["au_mv_event"],
                        "events": [],
                        "eventEvidence": [{
                            "eventId": "au_mv_event", "eventHash": event_hash,
                            "bankId": 7, "bank": "main_banks.pck",
                            "traversalStatus": "complete",
                        }],
                        "entries": [],
                    },
                    language="CN",
                    export_root=export_root,
                    webui_root=webui_root,
                    metadata_path=None,
                )
            self.assertEqual(payload["counts"]["modelViewStateAudioEvents"], 2)
            self.assertEqual(payload["counts"]["modelViewStateAudioEventsFoundInWwise"], 1)
            self.assertEqual(payload["counts"]["modelViewStateAudioEventsUnresolved"], 1)
            self.assertEqual(payload["controlCatalog"]["counts"]["modelViewStateRtpcParameters"], 1)
            self.assertEqual(payload["controlCatalog"]["counts"]["modelViewStateSpatialControls"], 1)
            self.assertEqual(payload["controlCatalog"]["counts"]["modelViewStateCustomAudioControls"], 1)
            self.assertEqual(payload["controlCatalog"]["counts"]["modelViewStatePositionedControls"], 2)
            summaries = json.loads(
                (webui_root / "data/lang/CN/audio/events.json").read_text(encoding="utf-8")
            )["events"]
            summary = next(row for row in summaries if row["id"] == "au_mv_event")
            self.assertIn("modelViewStateAudioEvent", summary["contextKinds"])
            self.assertIn("audioLayer", summary["contextSearch"])
            self.assertIn("int_fixture_alias", summary["contextSearch"])
            unresolved = next(
                row for row in summaries
                if "modelViewStatePositionAudioEvent" in row.get("contextKinds", [])
            )
            self.assertEqual(unresolved["category"], "sfx")
            self.assertEqual(unresolved["categoryEvidence"], "exactModelViewStateAudioBehavior")

            event_rows = [{
                "id": "au_mv_event",
                "hash": event_hash,
                "category": "sfx",
                "foundInWwise": True,
                "playbackRole": "playback",
                "possibleMediaCount": 2,
                "media": [
                    {"id": "leaf-a", "src": "/audio/leaf-a.flac"},
                    {"id": "leaf-b", "src": "/audio/leaf-b.flac"},
                ],
            }]
            native_rows = model_view_projection.project_model_view_state_audio_trigger_contexts(
                semantics,
                event_rows,
                native_context=validated_native_context(),
            )
            self.assertEqual(3, len(native_rows))
            trigger = next(row for row in native_rows if row["semanticKind"] == "modelViewStateAudioEvent")
            self.assertEqual("modelViewStateAudioEvent", trigger["semanticKind"])
            self.assertEqual(2, len(trigger["wwiseMediaCandidates"]))
            self.assertEqual("unresolved", trigger["runtimeBranch"]["status"])
            self.assertEqual("unobserved", trigger["activation"]["status"])
            self.assertEqual(
                "interactiveTableAssociationNotOwner",
                trigger["owner"]["ownerPromotionStatus"],
            )
            self.assertEqual(81734, trigger["nativeRoute"]["consumer"]["methodIndex"])
            self.assertEqual(
                "0x0600982d",
                trigger["nativeRoute"]["directCalls"][0]["targetToken"],
            )

            excluded_semantics = {
                "eventContexts": {
                    identifiers.event_hash_context_key(event_hash): [
                        semantics["eventContexts"][identifiers.event_hash_context_key(event_hash)][0],
                        {
                            **semantics["eventContexts"][identifiers.event_hash_context_key(event_hash)][0],
                            "kind": "modelViewStatePositionAudioEvent",
                            "behaviorTag": 0x0002,
                        },
                        {
                            **semantics["eventContexts"][identifiers.event_hash_context_key(event_hash)][0],
                            "isCustom": True,
                        },
                    ]
                }
            }
            self.assertEqual(
                2,
                len(model_view_projection.project_model_view_state_audio_trigger_contexts(
                    excluded_semantics,
                    event_rows,
                    native_context=validated_native_context(),
                )),
            )

            missing_rows = model_view_projection.project_model_view_state_audio_trigger_contexts(
                semantics,
                event_rows,
                native_context=native_evidence.NativeAudioEvidence(
                    None, None, "missing"
                ),
            )
            self.assertNotIn("nativeRoute", missing_rows[0])
            self.assertEqual(
                "nativeRouteUnavailable",
                missing_rows[0]["runtimeBranch"]["nativeRouteStatus"],
            )
            self.assertIn("reason", missing_rows[0]["nativeRouteDiagnostic"])
            mismatch_rows = model_view_projection.project_model_view_state_audio_trigger_contexts(
                semantics,
                event_rows,
                native_context=native_evidence.NativeAudioEvidence(
                    Path("global-metadata.dat"), Path("GameAssembly.dll"), "mismatched",
                    "wrong-metadata", "wrong-gameassembly", "fingerprint mismatch",
                ),
            )
            self.assertNotIn("nativeRoute", mismatch_rows[0])
            wrong_fingerprint = native_evidence.NativeAudioEvidence(
                Path("global-metadata.dat"), Path("GameAssembly.dll"), "validated",
                "wrong-metadata", "wrong-gameassembly",
            )
            self.assertNotIn(
                "nativeRoute",
                model_view_projection.project_model_view_state_audio_trigger_contexts(
                    semantics, event_rows, native_context=wrong_fingerprint
                )[0],
            )

            route = native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE
            drifted = {
                **route,
                "consumer": {**route["consumer"], "bodySha256": "body-drift"},
            }
            self.assertIsNone(
                native_evidence.model_view_state_audio_native_route(
                    validated_native_context(), observed_route=drifted
                )
            )

            catalog = audio_semantics.build_trigger_context_catalog(
                event_rows,
                [],
                webui_root,
                "CN",
                model_view_semantics=semantics,
                native_context=validated_native_context(),
            )
            self.assertIn("modelViewStateAudioEvent", catalog["counts"]["bySemanticKind"])
            self.assertEqual(
                "modelViewStateAudioEvent",
                next(
                    row for row in catalog["contexts"]
                    if row["semanticKind"] == "modelViewStateAudioEvent"
                )["semanticKind"],
            )

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

    def test_decodes_and_aggregates_custom_footstep_parameters_exactly(self) -> None:
        regular = event_projection.decode_custom_footstep_parameters(0x0D, 0.5)
        self.assertEqual(regular["footSide"], "Right")
        self.assertEqual(regular["vfxType"], "Land")
        self.assertEqual(regular["playbackFilter"], "IsMaxWeight")
        self.assertIsNone(regular["customWeightThreshold"])
        self.assertTrue(regular["inactiveFloat"])
        self.assertEqual(regular["runtimeVfxWeightThreshold"], 0.5)
        self.assertEqual(regular["decodeStatus"], "exactCurrentBuild")

        custom = event_projection.decode_custom_footstep_parameters(0x44, 0.375)
        self.assertEqual(custom["footSide"], "Left")
        self.assertEqual(custom["vfxType"], "Step")
        self.assertEqual(custom["playbackFilter"], "CustomWeight")
        self.assertEqual(custom["customWeightThreshold"], 0.375)
        self.assertFalse(custom["inactiveFloat"])
        self.assertEqual(custom["floatParameterStatus"], "customWeightThreshold")

        variants = event_projection.aggregate_custom_footstep_parameter_variants([
            {"function": "OnCustomFootStep", "intParameter": 0x0D, "floatParameter": 0.5},
            {"function": "OnCustomFootStep", "intParameter": 0x0D, "floatParameter": 0.5},
            {"function": "OnCustomFootStep", "intParameter": 0x44, "floatParameter": 0.375},
            {"function": "PostAudioEvent", "intParameter": 0x0D, "floatParameter": 0.5},
        ])
        self.assertEqual([row["occurrenceCount"] for row in variants], [2, 1])
        self.assertIsNone(event_projection.decode_custom_footstep_parameters(True, 0.5))
        self.assertEqual(
            event_projection.decode_custom_footstep_parameters(0x02, 0.5)["decodeStatus"],
            "unsupportedMaskedValue",
        )

    def test_collects_levelscript_events_controls_and_exact_cue_behavior_join(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            for source, marker in (("StreamingAssets", b"base"), ("Persistent", b"override")):
                path = export_root / f"structured/{source}/Data/Json/LevelScriptData/map/test.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(marker)

            def decode_file(_path: Path, data: bytes) -> dict:
                self.assertEqual(data, b"override")
                common_record = {
                    "start": 24,
                    "uid": "00112233445566778899aabbccddeeff",
                    "localId": 7,
                    "unionTag": 0x034E,
                    "serializedMemberCount": 0x0B,
                }
                return {"targetCount": 5, "rows": [{
                    "record": common_record,
                    "actionMapRole": "actionList#1 root",
                    "audioAction": {
                        "action": "PlayAudio",
                        "nativeMappingId": "binary-test",
                        "payloadShape": "exact",
                        "fields": {
                            "key": {"sourceField": "_key", "bindingKind": "constant", "value": "au_ls_play", "idRef": -1, "paramSource": 0},
                            "stopOnRelease": {"sourceField": "_stopOnRelease", "bindingKind": "constant", "value": True},
                        },
                        "eventBindings": [{"eventName": "au_ls_play", "role": "play", "sourceField": "_key"}],
                    },
                }, {
                    "record": {**common_record, "start": 48},
                    "actionMapRole": "actionList#2 linked",
                    "audioAction": {
                        "action": "PlayAudio",
                        "fields": {"key": {"sourceField": "_key", "bindingKind": "dynamic", "idRef": -1, "paramSource": 200, "path": "Start_music"}},
                    },
                }, {
                    "record": {**common_record, "start": 72, "unionTag": 0x036B, "serializedMemberCount": 0x13},
                    "actionMapRole": "actionList#3 linked",
                    "audioAction": {
                        "action": "PostAudioCue",
                        "fields": {"name": {"sourceField": "_name", "bindingKind": "constant", "value": "au_cue_music_combat_boss_state1"}},
                        "cueBindings": [{"cueName": "au_cue_music_combat_boss_state1", "role": "invoke", "sourceField": "_name"}],
                    },
                }, {
                    "record": {**common_record, "start": 96, "unionTag": 0x0307, "serializedMemberCount": 0x0B},
                    "actionMapRole": "actionList#4 linked",
                    "audioAction": {
                        "action": "ManualSetMusicState",
                        "fields": {
                            "baseState": {"sourceField": "_baseState", "bindingKind": "constant", "value": 2},
                            "battleIntensityState": {"sourceField": "_battleIntensityState", "bindingKind": "constant", "value": 1},
                            "battleState": {"sourceField": "_battleState", "bindingKind": "constant", "value": 3},
                        },
                    },
                }, {
                    "record": {**common_record, "start": 120, "unionTag": 0x04AC, "serializedMemberCount": 0x0A},
                    "actionMapRole": "actionList#5 linked",
                    "audioAction": {
                        "action": "StopAudio",
                        "fields": {
                            "audioId": {"sourceField": "_audioId", "bindingKind": "dynamic", "paramSource": 100, "path": "$28@_audioPlayingId"},
                            "fadeTimeMs": {"sourceField": "_fadeTimeMs", "bindingKind": "constant", "value": 100},
                        },
                    },
                }]}

            semantics = audio_semantics.collect_levelscript_audio_semantics(
                export_root,
                decode_file=decode_file,
                cue_semantics={"cueDefinitions": {
                    identifiers.audio_hash_generator_compute("au_cue_music_combat_boss_state1"): {
                        "source": "structured/Persistent/Table/AudioCueTable.json",
                        "handlerCount": 1,
                        "directHandlerCount": 1,
                        "levelHandlerCount": 0,
                        "expressionOperands": [],
                        "behaviorEvents": [{
                            "eventId": "au_music_cue_fixture",
                            "handlerScope": "direct",
                            "handlerIndex": 0,
                            "expressionSide": "behavior",
                            "expressionPath": "fixture.behaviourExpr",
                            "exprType": 3,
                        }],
                    },
                }},
            )

            context = semantics["eventContexts"]["au_ls_play"][0]
            self.assertEqual(context["kind"], "levelScriptAudioAction")
            self.assertEqual(context["sourceRoot"], "Persistent")
            self.assertEqual(context["triggerRole"], "play")
            self.assertEqual(context["fields"]["stopOnRelease"]["value"], True)
            self.assertEqual(context["serializedActionOrdinal"], 0)
            self.assertNotIn("recordIndex", context)
            self.assertEqual(
                semantics["cueInvocations"][0]["serializedActionOrdinal"],
                2,
            )
            self.assertFalse(context["storyOrderEvidence"])
            self.assertEqual(event_summary.semantic_context_group(context["kind"]), "scripted")
            self.assertEqual(semantics["cueInvocations"][0]["cueName"], "au_cue_music_combat_boss_state1")
            self.assertEqual(semantics["cueInvocations"][0]["definitionStatus"], "resolved")
            self.assertEqual(
                semantics["cueInvocations"][0]["cueId"],
                identifiers.audio_hash_generator_compute("au_cue_music_combat_boss_state1"),
            )
            self.assertEqual(semantics["cueInvocations"][0]["cueSignedId"], -1915703095)
            cue_context = semantics["eventContexts"]["au_music_cue_fixture"][0]
            self.assertEqual(cue_context["kind"], "levelScriptAudioCueBehaviorEvent")
            self.assertEqual(cue_context["handlerScope"], "direct")
            self.assertIn("nativeAudioHashGeneratorCompute", cue_context["triggerRequestEvidence"])
            missing = audio_semantics.collect_levelscript_audio_semantics(
                export_root,
                decode_file=decode_file,
                cue_semantics={"cueDefinitions": {}},
            )
            self.assertEqual(missing["cueInvocations"][0]["definitionStatus"], "missing")
            self.assertNotIn("au_music_cue_fixture", missing["eventContexts"])
            self.assertEqual(semantics["dynamicEventBindings"][0]["binding"]["path"], "Start_music")
            self.assertEqual(semantics["controlActions"][0]["controlRole"], "musicStateOverride")
            self.assertEqual(semantics["controlActions"][0]["fields"]["baseState"]["value"], 2)
            self.assertEqual(semantics["dynamicControlBindings"][0]["controlRole"], "playingAudioStop")
            self.assertEqual(semantics["dynamicControlBindings"][0]["binding"]["path"], "$28@_audioPlayingId")
            self.assertEqual(semantics["stats"]["decodedAudioActionRecords"], 5)
            self.assertEqual(semantics["stats"]["constantEventRequestContexts"], 1)
            self.assertEqual(semantics["stats"]["cueBehaviorEventContexts"], 1)
            self.assertEqual(semantics["stats"]["cueDefinitionStatusCounts"], {"resolved": 1})
            self.assertEqual(semantics["stats"]["controlActions"], 2)
            self.assertEqual(semantics["stats"]["dynamicControlBindings"], 1)

    def test_joins_levelscript_radio_triggers_to_ordered_audio_dialog_media(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            script_path = (
                export_root
                / "structured/Persistent/Data/Json/LevelScriptData/map/test.json"
            )
            script_path.parent.mkdir(parents=True)
            script_path.write_bytes(b"radio-fixture")
            table_path = export_root / "structured/Persistent/Table/RadioTable.json"
            table_path.parent.mkdir(parents=True)
            table_path.write_text(json.dumps({
                "radio_fixture": {
                    "radioType": 1,
                    "priority": 3,
                    "continueAfterDialog": False,
                    "continueAfterRadio": True,
                    "radioSingleDataList": [{
                        "index": 1,
                        "id": "radio_fixture_001",
                        "audioOverride": "au_radio_fixture_001",
                        "audioEvent": "",
                        "actorNameId": "actor_fixture",
                        "is3D": False,
                    }, {
                        "index": 2,
                        "id": "radio_fixture_002",
                        "audioOverride": "au_radio_fixture_002",
                        "audioEvent": "",
                        "actorNameId": "actor_fixture",
                        "is3D": False,
                    }],
                },
                "radio_unplayed": {
                    "radioSingleDataList": [{
                        "index": 1,
                        "id": "radio_unplayed_001",
                        "audioOverride": "au_radio_unplayed_001",
                    }],
                },
            }), encoding="utf-8")

            common_record = {
                "uid": "00112233445566778899aabbccddeeff",
                "localId": 7,
                "serializedMemberCount": 0x0D,
            }

            def constant_row(start: int, action: str, role: str, radio_id: str) -> dict:
                return {
                    "record": {**common_record, "start": start, "unionTag": 0x0363},
                    "actionMapRole": "actionList#1 root",
                    "audioAction": {
                        "action": action,
                        "nativeMappingId": "binary-radio-test",
                        "payloadShape": "exact",
                        "fields": {
                            "radioId": {
                                "sourceField": "_radioId",
                                "bindingKind": "constant",
                                "value": radio_id,
                                "idRef": -1,
                                "paramSource": 0,
                            },
                        },
                        "radioBindings": [{
                            "radioId": radio_id,
                            "role": role,
                            "sourceField": "_radioId",
                        }],
                    },
                }

            def decode_file(_path: Path, _data: bytes) -> dict:
                return {"targetCount": 5, "rows": [
                    constant_row(24, "PlayRadio", "play", "radio_fixture"),
                    constant_row(48, "StopRadio", "stop", "radio_fixture"),
                    constant_row(72, "PlayRadio", "play", "radio_missing"),
                    {
                        "record": {**common_record, "start": 96, "unionTag": 0x0363},
                        "actionMapRole": "actionList#4 linked",
                        "audioAction": {
                            "action": "PlayRadio",
                            "fields": {"radioId": {
                                "sourceField": "_radioId",
                                "bindingKind": "dynamic",
                                "idRef": 1,
                                "paramSource": -1,
                            }},
                        },
                    },
                    {
                        "record": {
                            **common_record,
                            "start": 120,
                            "unionTag": 0x04CA,
                            "serializedMemberCount": 0x09,
                        },
                        "actionMapRole": "actionList#5 linked",
                        "audioAction": {
                            "action": "ToggleClearScreenButRadio",
                            "fields": {"isShow": {
                                "sourceField": "_isShow",
                                "bindingKind": "constant",
                                "value": False,
                            }},
                        },
                    },
                ]}

            semantics = audio_semantics.collect_levelscript_audio_semantics(
                export_root,
                decode_file=decode_file,
                cue_semantics={"cueDefinitions": {}},
            )
            self.assertEqual(semantics["stats"]["radioActionRecords"], 5)
            self.assertEqual(semantics["stats"]["constantRadioBindings"], 3)
            self.assertEqual(semantics["stats"]["dynamicRadioBindings"], 1)
            self.assertEqual(
                semantics["stats"]["radioRoleCounts"],
                {"play": 2, "stop": 1},
            )

            self.assertNotIn("radio_fixture", semantics["eventContexts"])

            media = [{
                "id": "au_radio_fixture_001",
                "audioDialogPath": "fixture/au_radio_fixture_001.wem",
            }, {
                "id": "au_radio_unplayed_001",
                "audioDialogPath": "fixture/au_radio_unplayed_001.wem",
            }]
            catalog = audio_semantics.attach_levelscript_radio_contexts(
                media,
                export_root,
                semantics,
            )
            self.assertEqual(catalog["counts"]["radioTableDefinitions"], 2)
            self.assertEqual(catalog["counts"]["radioTableLines"], 3)
            self.assertEqual(catalog["counts"]["decodedDirectMedia"], 2)
            self.assertEqual(catalog["counts"]["unresolvedRadioTableLines"], 1)
            self.assertEqual(catalog["counts"]["constantRadioBindings"], 3)
            self.assertEqual(catalog["counts"]["resolvedConstantRadioBindings"], 2)
            self.assertEqual(catalog["counts"]["unresolvedConstantRadioBindings"], 1)
            self.assertEqual(catalog["counts"]["referencedRadioLines"], 2)
            self.assertEqual(catalog["counts"]["decodedReferencedRadioLines"], 1)
            self.assertEqual(catalog["counts"]["unresolvedReferencedRadioLines"], 1)
            self.assertEqual(catalog["counts"]["radioTriggerContextAssociations"], 2)

            triggered = media[0]
            self.assertEqual(triggered["radioTableLineIdentities"][0]["lineOrdinal"], 0)
            self.assertEqual(triggered["radioTableLineIdentities"][0]["audioOverride"], "au_radio_fixture_001")
            self.assertEqual(triggered["radioTriggerContextCount"], 2)
            self.assertEqual(triggered["radioTriggerContextStoredCount"], 2)
            self.assertFalse(triggered["radioTriggerContextsTruncated"])
            self.assertEqual(triggered["radioTriggerRoles"], ["play", "stop"])
            self.assertIn("radio_fixture", triggered["radioTriggerSearch"])
            self.assertEqual(
                triggered["radioTriggerContexts"][0]["audioDialogMatchEvidence"],
                "exactAudioDialogPathStem",
            )
            self.assertEqual(triggered["radioTriggerContexts"][0]["wwiseEventStatus"], "notApplicable")

            unplayed = media[1]
            self.assertEqual(unplayed["radioTableLineCount"], 1)
            self.assertEqual(unplayed["radioTriggerContextCount"], 0)
            self.assertNotIn("radioTriggerContexts", unplayed)

            self.assertEqual(catalog["unresolvedRadioIds"]["totalCount"], 1)
            self.assertEqual(catalog["unresolvedRadioIds"]["items"][0]["radioId"], "radio_missing")
            self.assertEqual(catalog["unresolvedRadioLines"]["totalCount"], 1)
            self.assertEqual(catalog["unresolvedRadioLines"]["items"][0]["audioOverride"], "au_radio_fixture_002")
            self.assertEqual(catalog["dynamicRadioBindings"]["totalCount"], 1)
            self.assertEqual(
                catalog["dynamicRadioBindings"]["items"][0]["binding"]["idRef"],
                1,
            )

    def test_levelscript_voice_id_joins_audio_dialog_media_not_wwise_event(self) -> None:
        media = [{
            "id": "au_voice_fixture",
            "src": "/voice/au_voice_fixture.flac",
            "audioDialogPath": "v1d0/Narrating/au_voice_fixture.wem",
            "audioCategory": "story_voice",
            "storyLineBindingCount": 1,
            "purposeKnowledgeStatus": "exactStoryLineBinding",
        }]
        invocations = [{
            "action": "PlayVoiceNarrative",
            "voiceId": "au_voice_fixture",
            "triggerRole": "voiceNarrative",
            "levelScriptId": "map/fixture",
            "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/fixture.json",
            "recordStart": 24,
            "sourceField": "_voId",
            "runtimeActivationStatus": "levelScriptActionExecutionNotObserved",
        }]

        rows = audio_semantics._build_levelscript_voice_trigger_contexts(
            media,
            invocations,
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("levelScriptVoice", rows[0]["semanticKind"])
        self.assertEqual("exactAudioDialogPathStem", rows[0]["selection"]["voiceSelectionStatus"])
        self.assertEqual("notApplicable", rows[0]["selection"]["wwiseEventStatus"])
        self.assertEqual("/voice/au_voice_fixture.flac", rows[0]["mediaRefs"][0]["src"])
        self.assertEqual(1, rows[0]["meaning"]["storyLineBindingCount"])

    def test_resolves_dynamic_radio_string_list_candidates_without_selecting_one(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            script_path = (
                export_root
                / "structured/Persistent/Data/Json/LevelScriptData/map/1001.json"
            )
            script_path.parent.mkdir(parents=True)
            script_path.write_bytes(b"dynamic-radio-fixture")

            def decode_file(_path: Path, _data: bytes) -> dict:
                return {
                    "targetCount": 1,
                    "rows": [{
                        "record": {
                            "start": 84,
                            "uid": "radio-action",
                            "localId": 2,
                            "unionTag": 0x0363,
                            "serializedMemberCount": 0x0D,
                        },
                        "actionMapRole": "actionList#2 root",
                        "audioAction": {
                            "action": "PlayRadio",
                            "fields": {"radioId": {
                                "sourceField": "_radioId",
                                "bindingKind": "dynamic",
                                "idRef": 1,
                                "paramSource": -1,
                            }},
                        },
                    }],
                    "stringListGetters": {1: {
                        "record": {"localId": 1, "uid": "radio-getter"},
                        "actionMapRole": "getterList#1",
                        "getter": {
                            "index": {
                                "bindingKind": "localGetterRef",
                                "getterLocalId": 0,
                            },
                            "list": {
                                "bindingKind": "dynamic",
                                "idRef": -1,
                                "paramSource": 200,
                                "path": "RandomLines",
                            },
                        },
                    }},
                }

            brief = {
                "properties": [{
                    "name": "RandomLines",
                    "value": {
                        "valueType": 8,
                        "atomCount": 2,
                        "atoms": [
                            {"valueBit64": 0, "text": "radio_a"},
                            {"valueBit64": 0, "text": "radio_b"},
                        ],
                    },
                }],
            }
            with patch.object(
                audio_semantics,
                "_load_levelscript_brief_property_sources",
                return_value=(brief, "structured/Persistent/Data/Json/LevelData/map.json"),
            ):
                semantics = audio_semantics.collect_levelscript_audio_semantics(
                    export_root,
                    decode_file=decode_file,
                    cue_semantics={"cueDefinitions": {}},
                )

            self.assertEqual(1, semantics["stats"]["dynamicRadioBindings"])
            self.assertEqual(1, semantics["stats"]["resolvedDynamicRadioBindings"])
            row = semantics["dynamicRadioBindings"][0]
            self.assertEqual(
                "resolvedRadioCandidateSetRuntimeIndexUnobserved",
                row["resolutionStatus"],
            )
            self.assertEqual(["radio_a", "radio_b"], row["candidateRadioIds"])
            self.assertEqual("runtimeListIndexUnobserved", row["selectionStatus"])
            self.assertNotIn("radioId", row)

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
                            "evidence": [{
                                "time": 0.25,
                                "function": "OnCustomFootStep",
                                "floatParameter": 0.5,
                                "intParameter": 0,
                            }],
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
                            "evidence": [{
                                "time": 0.5,
                                "function": "OnCustomFootStep",
                                "floatParameter": 0.0,
                                "intParameter": 225,
                            }],
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
                        "behaviourExpr": {"exprType": 3, "stringValue": "au_sfx_test", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
                        "conditionExpr": {"exprType": 0, "stringValue": "", "boolValue": False, "intValue": 0, "floatValue": 0.0, "children": []},
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

            self.assertEqual(payload["shards"], {
                "events": "events.json",
                "media": "media.json",
                "sceneBackgrounds": "scene_backgrounds.json",
            })
            scene_background_payload = json.loads(
                (out_root / "scene_backgrounds.json").read_text(encoding="utf-8")
            )
            self.assertEqual(scene_background_payload["status"], "unavailable")
            self.assertNotIn("eventContexts", scene_background_payload)
            self.assertFalse(payload["debugOnly"])
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
            self.assertEqual(payload["counts"]["customFootstepCallbackOccurrences"], 2)
            self.assertEqual(payload["counts"]["customFootstepParameterVariants"], 2)
            self.assertEqual(event["customFootstepOccurrenceCount"], 2)
            self.assertEqual(event_summary["customFootstepOccurrenceCount"], 2)
            self.assertEqual(
                [(row["rawInt"], row["rawFloat"], row["occurrenceCount"])
                 for row in event["customFootstepParameterVariants"]],
                [(0, 0.5, 1), (225, 0.0, 1)],
            )
            self.assertIn("customFootstepCallbacks", payload["evidenceBoundary"])
            self.assertIn("_SetAudioMatSwitch", payload["customFootstepModel"]["runtimeSelectorBoundary"])
            self.assertIn("does not map", payload["customFootstepModel"]["runtimeSelectorBoundary"])

    def test_audio_frontend_materializes_each_distinct_media_player_on_expand(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        playable_body = source.split("function playableRecords", 1)[1].split(
            "function audioSource", 1
        )[0]
        render_body = source.split("function renderPlayers", 1)[1].split(
            "function statNode", 1
        )[0]

        self.assertIn("`${candidate.id}\\u0000${candidate.src}`", playable_body)
        self.assertIn('document.createElement("details")', render_body)
        self.assertIn('document.createElement("summary")', render_body)
        self.assertIn('card.addEventListener("toggle"', render_body)
        self.assertIn("if (!card.open || materialized) return", render_body)
        self.assertGreater(
            render_body.index('document.createElement("audio")'),
            render_body.index('card.addEventListener("toggle"'),
        )
        self.assertNotIn("players.length <= 200", render_body)
        self.assertIn('contextNpcPatrolTrigger: "NPC patrol-point audio"', source)
        self.assertIn('contextKind === "patrolSubActionPlayAudio"', source)
        self.assertIn('`NPC patrol ${context.patrolId}`', source)
        self.assertIn("function customFootstepParameterSummary", source)
        self.assertIn('"float inactive for playback filter"', source)
        self.assertIn("runtimeSelectorBoundary", source)
        self.assertIn('levelEventConditions: "LevelEvent audio conditions"', source)
        self.assertIn("catalog.levelEventAudioConditions", source)
        self.assertIn("authoredOccurrenceCount", source)
        self.assertNotIn("selected Wwise switch child", source)
        self.assertIn("const PLAYER_COLLAPSE_THRESHOLD = 20", source)
        self.assertIn("candidates.length > PLAYER_COLLAPSE_THRESHOLD", render_body)

    def test_audio_frontend_selector_branches_use_candidate_and_evidence_boundaries(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        branch_body = source.split("function selectorBranchesSection", 1)[1].split(
            "function sourceEvidenceSummary", 1
        )[0]
        self.assertIn('t("selectorBranches")', branch_body)
        self.assertIn("inferred / possible", branch_body)
        self.assertIn("mapped selector candidate", branch_body)
        self.assertIn("outside ownership evidence", branch_body)
        self.assertIn("Selector candidates, not guaranteed playable children.", branch_body)
        self.assertIn("selectorRuntimeUnobserved", source)
        self.assertNotIn("authored child${childCount", branch_body)

    def test_audio_frontend_prioritizes_unknown_purpose_and_exposes_enemy_action_mapping(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        purpose_body = source.split("function purposeRecoveryTag", 1)[1].split(
            "function recordType", 1
        )[0]
        normalize_body = source.split("function normalizeRecord", 1)[1].split(
            "function rebuildEventTaxonomy", 1
        )[0]
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split(
            "function radioTableLineLabel", 1
        )[0]

        self.assertIn('priority === "resolvedTerminal"', purpose_body)
        self.assertIn("storyLineBindingCount", purpose_body)
        self.assertIn('priority === "highest"', purpose_body)
        self.assertIn('"purposeStoryTerminal"', source)
        self.assertIn("purposeTag", normalize_body)
        self.assertIn('purposeUnknown: "Purpose unknown — investigate"', source)
        self.assertIn("enemyTriggerVoiceActionCatalogSection", source)
        self.assertIn("state.index?.triggerCatalog?.enemyTriggerVoiceAction", source)
        self.assertIn("context?.enemyTriggerVoiceAction", evidence_body)
        self.assertIn("enemyAction.voiceType", evidence_body)
        self.assertIn("enemyAction.mappingAddInvocationVa", evidence_body)
        self.assertIn('"purposeUnknownEvents"', (
            Path(__file__).resolve().parents[1] / "build_audio_semantics.py"
        ).read_text(encoding="utf-8"))
        self.assertIn('"purposeStoryTerminalMedia"', (
            Path(__file__).resolve().parents[1] / "build_audio_semantics.py"
        ).read_text(encoding="utf-8"))

    def test_audio_frontend_keeps_event_type_and_media_purpose_separate(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")

        self.assertIn('eventType: "Event type"', source)
        self.assertIn('mediaPurpose: "Media purpose"', source)
        self.assertIn('relatedEventTypes: "Related Event types"', source)
        self.assertIn('state.mode === "events" ? "eventType" : "mediaPurpose"', source)
        self.assertIn('record?.relatedEventCategories', source)
        self.assertIn('["#audio-category-filter", "category", state.filters.categories, categoryLabel]', source)

    def test_audio_frontend_exposes_exact_levelscript_radio_media_contexts(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        context_tags_body = source.split("function recordContextTags", 1)[1].split(
            "function recordRelationTags", 1
        )[0]
        relation_body = source.split("function recordRelationTags", 1)[1].split(
            "function recordMeta", 1
        )[0]
        search_body = source.split("function searchText", 1)[1].split(
            "function humanize", 1
        )[0]
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split(
            "function radioTableLineLabel", 1
        )[0]
        record_panel_body = source.split("function recordPanel", 1)[1].split(
            "function collectIds", 1
        )[0]

        self.assertIn('contextKind === "levelScriptRadioTrigger"', context_tags_body)
        self.assertIn("record?.radioTriggerContextCount", context_tags_body)
        self.assertIn("record?.radioTriggerContexts", context_tags_body)
        self.assertIn("record?.radioTriggerSearch", search_body)
        self.assertIn("record?.radioTableLineIdentities", search_body)
        self.assertIn("record?.radioTriggerContexts", search_body)
        self.assertIn('kind === "levelScriptRadioTrigger"', evidence_body)
        self.assertIn("radioDefinition.continueAfterDialog", evidence_body)
        self.assertIn("radioDefinition.continueAfterRadio", evidence_body)
        self.assertIn("radioLine.is3D", evidence_body)
        self.assertIn("radioLine.actorNameId", evidence_body)
        self.assertIn("radioLine.lineOrdinal", evidence_body)
        self.assertIn("context?.audioDialogMatchEvidence", evidence_body)
        self.assertIn("raw.radioTableLineIdentities", record_panel_body)
        self.assertIn("raw.radioTriggerContexts", record_panel_body)
        self.assertIn("raw.radioTriggerContextStoredCount", record_panel_body)
        self.assertIn("raw.radioTriggerContextsTruncated", record_panel_body)
        self.assertIn("triggerCatalog?.levelScriptRadio?.evidenceBoundary", record_panel_body)
        self.assertIn("state.index?.triggerCatalog?.levelScriptRadio", source)
        self.assertIn("function levelScriptRadioCatalogSection", source)
        self.assertIn("catalog.dynamicRadioBindings", source)
        self.assertIn("catalog.unresolvedRadioIds", source)
        self.assertIn("catalog.unresolvedRadioLines", source)
        self.assertLess(
            record_panel_body.index('playerHeading.textContent = t("playableMedia")'),
            record_panel_body.index('const facts = record.kind === "events"'),
        )
        self.assertLess(
            record_panel_body.index('playerHeading.textContent = t("playableMedia")'),
            record_panel_body.index('heading.textContent = t("details")'),
        )
        self.assertLess(
            record_panel_body.index('playerHeading.textContent = t("playableMedia")'),
            record_panel_body.index("panel.appendChild(manualNoteSection(record))"),
        )

        direct_media_check = 'if (record?.audioDialogKey || record?.audioDialogPath) return ["directDialogMedia"]'
        self.assertIn(direct_media_check, relation_body)
        self.assertLess(
            relation_body.index(direct_media_check),
            relation_body.index("record?.eventIds"),
        )

    def test_audio_frontend_hides_levelscript_serialized_output_paths_in_normal_mode(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        lifecycle_body = source.split("function levelScriptAudioLifecycleSection", 1)[1].split(
            "function selectorEvidenceSummary", 1
        )[0]
        self.assertIn("if (debug && detail.serializedOutputPath)", lifecycle_body)
        self.assertIn("field ${detail.fieldName}", lifecycle_body)
        self.assertIn("Static serialized LevelScript evidence only", lifecycle_body)

    def test_audio_frontend_exposes_levelsequence_timeline_director_evidence(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        context_tags_body = source.split("function recordContextTags", 1)[1].split(
            "function recordRelationTags", 1
        )[0]
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split(
            "function radioTableLineLabel", 1
        )[0]
        self.assertIn('timeline: "contextTimeline"', source)
        self.assertIn('contextKind === "levelSequenceAudio"', context_tags_body)
        self.assertIn('context?.timelineAssetName', evidence_body)
        self.assertIn('context?.playableDirectorCount', evidence_body)
        self.assertIn('context?.levelScriptActionCount', evidence_body)
        self.assertIn('context?.audioPlayableKeyStatus', evidence_body)
        self.assertIn("function levelSequenceAudioCatalogSection", source)
        self.assertIn("state.index?.triggerCatalog?.levelSequenceAudio", source)
        self.assertIn("catalog.eventsWithExactLevelSequenceAction", source)
        self.assertIn("catalog.eventsWithoutTimelineCarrier", source)

    def test_audio_frontend_exposes_authored_animator_state_membership_boundary(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split(
            "function radioTableLineLabel", 1
        )[0]
        self.assertIn("context?.animatorControllerContexts", evidence_body)
        self.assertIn("authoredStateReferences", evidence_body)
        self.assertIn("runtime execution unobserved", evidence_body)

    def test_audio_frontend_exposes_animation_callback_aggregate_ownership_contract(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        search_body = source.split("function searchText", 1)[1].split(
            "function humanize", 1
        )[0]
        panel_body = source.split("function recordPanel", 1)[1].split(
            "function collectIds", 1
        )[0]

        for field in (
            "animationCallbackOwnershipStatus",
            "animationCallbackTokenResolutionStatus",
            "animationCallbackTokenResolutionStatuses",
            "animationCallbackResolutionStatuses",
            "animationCallbackResolvedEntityIds",
            "animationCallbackCandidateEntityIds",
            "animationCallbackNpcOwnerIds",
            "animationCallbackNpcOwnerTemplates",
            "animationCallbackNpcActorTokens",
            "animationCallbackOwnerKinds",
            "animationCallbackNpcOccurrenceOwnerIds",
            "animationCallbackNpcOccurrenceOwnerTemplates",
            "animationCallbackNpcOccurrenceActorTokens",
        ):
            self.assertIn(f"record?.{field}", search_body)
            self.assertIn(f"raw.{field}", panel_body)
        self.assertIn("Animation callback ownership", panel_body)
        self.assertIn("Animation callback token resolution", panel_body)
        self.assertIn("Animation callback resolved entities", panel_body)
        self.assertIn("Animation callback candidate entities", panel_body)
        self.assertIn("raw.animationCallbackNpcOwnerIds", panel_body)
        self.assertIn("raw.animationCallbackNpcOwnerTemplates", panel_body)
        self.assertIn("raw.animationCallbackNpcActorTokens", panel_body)
        self.assertIn("raw.animationCallbackOwnerKinds", panel_body)
        self.assertIn("raw.animationCallbackNpcOccurrenceOwnerIds", panel_body)
        self.assertIn("raw.animationCallbackNpcOccurrenceOwnerTemplates", panel_body)
        self.assertIn("raw.animationCallbackNpcOccurrenceActorTokens", panel_body)
        self.assertNotIn("raw.animationCallbackClipResolutions", panel_body)
        self.assertNotIn("raw.animationCallbackOccurrences", panel_body)
        self.assertIn('npcAnimation: "contextNpcAnimation"', source)
        self.assertIn('animationCallbackNpcOwner: "contextAnimationCallbackNpcOwner"', source)
        self.assertIn("function hasExactNpcAnimationOwner", source)
        self.assertIn("const resolutionStatuses = asArray(record?.animationCallbackResolutionStatuses)", source)
        self.assertIn('resolutionStatuses.every((status) => status.startsWith("exactNpc"))', source)
        self.assertIn('"exactNpcOwnerAgreement"', source)
        self.assertIn('tags.add("ownerUnresolvedAnimation")', source)
        self.assertIn('tags.add("animationCallbackNpcOwner")', source)
        self.assertIn('context.kind === "animationCallbackOwnerUnresolved" && hasExactNpcAnimationOwner(record)', search_body)
        self.assertIn("runtime execution unobserved", source)

    def test_audio_frontend_exposes_scene_emitter_containment_boundary(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        search_body = source.split("function searchText", 1)[1].split(
            "function humanize", 1
        )[0]
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split(
            "function radioTableLineLabel", 1
        )[0]
        self.assertIn('kind === "sceneEmitterAudioEvent"', evidence_body)
        self.assertIn("sceneContainmentStatus", evidence_body)
        self.assertIn("sourceAssetPath", evidence_body)
        self.assertIn("containmentType", evidence_body)
        self.assertIn("authored prefab component / runtime scene instantiation unobserved", evidence_body)
        for field in (
            "context.sceneContainmentStatus",
            "context.sourceAssetPath",
            "context.containmentType",
            "context.sceneContainmentDiagnostics",
        ):
            self.assertIn(field, search_body)

    def test_audio_frontend_exposes_scene_global_compact_attribution(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        search_body = source.split("function searchText", 1)[1].split(
            "function humanize", 1
        )[0]
        panel_body = source.split("function recordPanel", 1)[1].split(
            "function collectIds", 1
        )[0]
        evidence_body = source.split("function contextEvidenceLabel", 1)[1].split(
            "function radioTableLineLabel", 1
        )[0]
        for field in (
            "sceneGlobalSceneIds",
            "sceneGlobalSemanticRoles",
            "sceneGlobalContextStatus",
        ):
            self.assertIn(f"record?.{field}", search_body)
            self.assertIn(f"raw.{field}", panel_body)
        self.assertIn('record?.sceneGlobalContextStatus === "exact"', source)
        self.assertIn('tags.add("sceneGlobalExact")', source)
        self.assertIn('kind === "sceneGlobalAudioEvent"', evidence_body)
        self.assertIn("authored scene-global definition; activation/playback unobserved", evidence_body)

    def test_audio_frontend_renders_native_playback_call_chain_stages(self) -> None:
        source = (
            Path(__file__).resolve().parents[2] / "webui/src/features/audio/index.js"
        ).read_text(encoding="utf-8")
        body = source.split("function runtimeSystemsSection", 1)[1].split(
            "function contextEvidenceLabel", 1
        )[0]

        self.assertIn("system.nativeCallChains", body)
        self.assertIn('chainCard.className = "audio-runtime-call-chain"', body)
        self.assertIn("system.nativeStateGroups", body)
        self.assertIn("system.nativeStateTransitions", body)
        self.assertIn('groupCard.className = "audio-runtime-state-group"', body)
        self.assertIn("Object.entries(system.enumValues)", body)
        self.assertIn("group.groupIdHex", body)
        self.assertIn("transition.stateMaskHex", body)
        self.assertIn("transition.callbackTargetStatus", body)
        self.assertIn("transition.registrations", body)
        self.assertIn("registration.callbackMethod", body)
        self.assertNotIn("systems.slice(0, 40)", body)
        self.assertIn("stage.methodIndex", body)
        self.assertIn("stage.virtualAddress", body)
        self.assertIn("stage.relation", body)
        self.assertIn("chain.alternateEntryPoints", body)
        self.assertIn("alternateEntryPoints", body)
        self.assertIn("chain.branches", body)
        self.assertIn("branch.relation", body)
        self.assertIn("chain.boundary", body)
        self.assertIn("container?.selectorGroupTypes", source)
        self.assertIn("selector.strictSubsetPackages", source)
        self.assertIn("Runtime selector value and audio-object state were not observed", source)
        self.assertIn("catalog.wwiseSelectorGroups", source)
        self.assertIn("controlCatalog?.wwiseSelectorGroups", source)
        self.assertIn("runtimeGroup.semanticEvidence", source)
        self.assertIn("value.resolvedValueIdHex", source)
        self.assertIn("value.resolvedValueName", source)
        self.assertIn("container?.randomSequenceModes", source)
        self.assertIn("randomSequence.orderDiffers", source)
        self.assertIn("container?.randomSequenceMembershipStatuses", source)
        self.assertIn("randomSequence.ownedNotInPlaylist", source)
        self.assertIn("Reciprocal Children prove container ownership", source)
        self.assertIn("node?.selectorValidation?.status", source)
        self.assertIn("recursiveOwnedDescendantIds", source)
        self.assertIn("zeroUnboundLeafIds", source)
        self.assertIn("sameBankMissingLeafIds", source)
        self.assertIn("recursiveOwned", source)
        self.assertIn("Wwise Random/Sequence policy", source)
        self.assertIn("Runtime random seed, shuffle history", source)
        self.assertIn("container?.layerAssignmentStatuses", source)
        self.assertIn("layerBlend.associations", source)
        self.assertIn("Wwise Layer/Blend structure", source)
        self.assertIn("zero-layer assignments remain structural child relations only", source)
        self.assertIn("function sourceEvidenceSummary", source)
        self.assertIn("evidence?.nonMediaSourceEvidence", source)
        self.assertIn('sourceKinds.has("externalSourceCodec")', source)
        self.assertIn('sourceKinds.has("synthesizedSource")', source)
        self.assertIn("Stream type is a buffering policy", source)

    def test_model_view_projection_stably_deduplicates_duplicate_trigger_ids(self) -> None:
        event_hash = 0x12345678
        authored = {
            "kind": "modelViewStateAudioEvent",
            "behaviorTag": 0x0001,
            "isCustom": False,
            "controllerId": "controller-fixture",
            "sourceFile": "controller.json",
            "normalAudioId": event_hash,
        }
        semantics = {
            "eventContexts": {
                identifiers.event_hash_context_key(event_hash): [authored],
            },
        }
        duplicate_event_rows = [
            {"id": "au_duplicate", "hash": event_hash, "media": []},
            {"id": "au_duplicate", "hash": event_hash, "media": []},
        ]
        projected = model_view_projection.project_model_view_state_audio_trigger_contexts(
            semantics,
            duplicate_event_rows,
            native_context=validated_native_context(),
        )
        self.assertEqual(len(projected), 1)
        self.assertEqual(len({row["triggerId"] for row in projected}), len(projected))

    def test_model_view_positioned_three_branches_keep_controls_out_of_events(self) -> None:
        base = {
            "behaviorTag": 0x0002,
            "behaviorType": 8,
            "behaviorKind": "positionEvent",
            "kind": "modelViewStatePositionAudioEvent",
            "controllerId": "position-controller",
            "ownerId": "position-controller",
            "sourceFile": "position.json",
            "semanticPath": "modelAnimatorDatas[0].behaviors[0]",
            "sourcePaths": ["position.json"],
            "audioNodeName": "Point",
            "customAudioId": "custom_state",
            "eAudioTriggerState": 7,
            "stopOnEnd": False,
            "transitionTime": 0,
            "runtimeActivationStatus": "modelViewStateBehaviorExecutionNotObserved",
        }
        direct = {**base, "isDirectlyPlay": True, "isCustom": False, "normalAudioId": 0x1234}
        custom = {**base, "isDirectlyPlay": False, "isCustom": True, "controlBranch": "customStateSwitch", "controlValue": "custom_state"}
        entity = {**base, "isDirectlyPlay": False, "isCustom": False, "normalAudioId": 9, "controlBranch": "entityStateSwitch", "controlValue": 7, "stateValue": 7, "modelLevel": 1}
        semantics = {
            "eventContexts": {identifiers.event_hash_context_key(0x1234): [direct]},
            "positionedControls": [custom, entity],
        }
        rows = model_view_projection.project_model_view_state_audio_trigger_contexts(
            semantics,
            [{"id": "au_position", "hash": 0x1234, "foundInWwise": True, "media": [{"src": "position.flac"}]}],
            native_context=validated_native_context(),
        )
        self.assertEqual({row["semanticKind"] for row in rows}, {
            "modelViewStatePositionAudioEvent",
            "modelViewStatePositionedCustomStateControl",
            "modelViewStatePositionedEntityStateControl",
        })
        event = next(row for row in rows if row["semanticKind"] == "modelViewStatePositionAudioEvent")
        self.assertEqual(event["action"]["playbackSink"], "AudioManager.PlaySoundAtPosition")
        self.assertEqual(event["action"]["playbackSinkStatus"], "staticManagedAdapterRouteVerified")
        self.assertEqual(event["action"]["audioHandleField"], "self+0x28 m_audioHandle")
        self.assertEqual(event["action"]["audioHandleMeaning"], "managedInternalPlayingId")
        self.assertEqual(event["action"]["nativeAkSoundEnginePlayingIdStatus"], "unresolved")
        self.assertEqual(event["action"]["audioHandleWriteStatus"], "verified")
        self.assertEqual(event["runtimeBranch"]["downstreamStatus"], "AkSoundEngineWwiseSelectionExecutionAudibilityUnresolved")
        self.assertEqual(event["runtimeBranch"]["managedAdapterRouteStatus"], "staticManagedAdapterRouteVerified")
        self.assertEqual(event["runtimeBranch"]["asyncBoundaryStatus"], "staticLoadBankPrepareEventBoundaryVerified")
        self.assertEqual(event["action"]["postAndForgetToAudioAdapterConnectionStatus"], "verified")
        self.assertEqual(event["action"]["postEventRuntimeStatus"], "adapterRequestQueuedOrPrepared")
        self.assertEqual(event["action"]["asyncBoundaryStatus"], "staticLoadBankPrepareEventBoundaryVerified")
        self.assertEqual(event["runtimeBranch"]["status"], "unresolved")
        for control in rows:
            if control["semanticKind"].endswith("Control"):
                self.assertEqual(control["wwiseMediaCandidates"], [])
                self.assertEqual(control["mediaRefs"], [])
                self.assertEqual(control["meaning"]["wwiseEventStatus"], "notPromotedToEvent")
                self.assertNotIn("owner", control)
                self.assertEqual(control["controllerEvidence"]["ownerStatus"], "notAnOwnerProof")
        entity_row = next(row for row in rows if row["semanticKind"] == "modelViewStatePositionedEntityStateControl")
        self.assertEqual(entity_row["action"]["stateValue"], 7)
        self.assertEqual(entity_row["action"]["modelLevel"], 1)

    def test_model_view_positioned_projection_rejects_stale_or_key_only_event_rows(self) -> None:
        stale = {
            "behaviorTag": 0x0002,
            "kind": "modelViewStateAudioEvent",
            "isDirectlyPlay": True,
            "isCustom": False,
            "normalAudioId": 0x1234,
            "controllerId": "stale",
        }
        zero_id = {
            **stale,
            "kind": "modelViewStatePositionAudioEvent",
            "normalAudioId": 0,
        }
        key_only = {
            **stale,
            "kind": "modelViewStatePositionAudioEvent",
            "normalAudioId": None,
        }
        valid_wrong_context_key = {
            **stale,
            "kind": "modelViewStatePositionAudioEvent",
            "normalAudioId": 0x1234,
        }
        semantics = {
            "eventContexts": {
                "#0x00001234": [stale],
                "#0x00005678": [zero_id, valid_wrong_context_key],
                "#0x00001234-key-only": [key_only],
            },
            "positionedControls": [],
        }
        projected = model_view_projection.project_model_view_state_audio_trigger_contexts(
            semantics,
            [{"id": "au_position", "hash": 0x1234, "media": [{"src": "position.flac"}]}],
            native_context=validated_native_context(),
        )
        self.assertEqual(len(projected), 1)
        self.assertEqual(projected[0]["situation"]["eventHash"], 0x1234)

    def test_levelscript_audio_lifecycle_joins_exact_paths_and_keeps_postcue_output_only(self) -> None:
        def action(name, start, local_id, fields, ordinal):
            return {
                "action": name,
                "levelScriptId": "map/9001",
                "sourceRoot": "Persistent",
                "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/9001.json",
                "serializedActionOrdinal": ordinal,
                "recordStart": start,
                "recordLocalId": local_id,
                "actionMapRole": f"actionList#{ordinal + 1} linked",
                "runtimeSlotStatus": "active-final-serialized-slot",
                "fields": fields,
            }

        rows = [
            action("PlayAudio", 10, 1, {"audioPlayingId": {"bindingKind": "output", "path": "$1@_audioPlayingId", "paramSource": 0}}, 0),
            action("StopAudio", 20, 2, {"audioId": {"bindingKind": "dynamic", "path": "$1@_audioPlayingId", "paramSource": 0}}, 1),
            action("PlayVoice", 30, 3, {"voiceHandle": {"bindingKind": "output", "path": "$2@_voiceHandle", "paramSource": 0}}, 2),
            action("StopVoice", 40, 4, {"voiceHandle": {"bindingKind": "dynamic", "path": "$2@_voiceHandle", "paramSource": 0}}, 3),
            action("BlockAutoMusicChange", 50, 5, {"blockHandle": {"bindingKind": "output", "path": "$3@_blockHandle", "paramSource": 0}}, 4),
            action("BlockAutoMusicChangeCancel", 60, 6, {"blockHandle": {"bindingKind": "dynamic", "path": "$3@_blockHandle", "paramSource": 0}}, 5),
            action("PostAudioCue", 70, 7, {"cueHandlerId": {"bindingKind": "output", "path": "$4@_cueHandlerId", "paramSource": 0}}, 6),
        ]
        details, summary = audio_semantics._build_levelscript_audio_lifecycle(rows)
        self.assertEqual(summary["exactJoinCount"], 3)
        self.assertEqual(summary["producerOnlyCount"], 1)
        self.assertEqual(summary["unresolvedCount"], 0)
        self.assertEqual({row["lifecycleKind"] for row in details}, {"audioPlayingId", "voiceHandle", "blockHandle", "cueHandlerId"})
        consumer = next(row for row in details if row["role"] == "consumer" and row["lifecycleKind"] == "audioPlayingId")
        self.assertEqual(consumer["joinStatus"], "exact_unique_active_producer")
        self.assertEqual(consumer["sourceKind"], "runtime")
        cue = next(row for row in details if row["lifecycleKind"] == "cueHandlerId")
        self.assertEqual(cue["joinStatus"], "producer_only")
        self.assertEqual(audio_semantics._levelscript_parameter_source({"bindingKind": "constant", "paramSource": 0, "idRef": -1}), "constant")
        self.assertEqual(audio_semantics._levelscript_parameter_source({"bindingKind": "dynamic", "paramSource": 200, "path": "CueName"}), "property")
        self.assertEqual(audio_semantics._levelscript_parameter_source({"bindingKind": "dynamic", "paramSource": 100, "path": "$1@_audioPlayingId"}), "runtime")
        self.assertEqual(audio_semantics._levelscript_parameter_source({"bindingKind": "output", "paramSource": 0, "path": "$1@_audioPlayingId"}), "output")

    def test_levelscript_audio_lifecycle_fails_closed_for_duplicate_or_shadowed_producer(self) -> None:
        path = "$8@_audioPlayingId"
        base = {
            "levelScriptId": "map/9002",
            "sourceRoot": "Persistent",
            "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/9002.json",
            "runtimeSlotStatus": "active-final-serialized-slot",
            "fields": {"audioPlayingId": {"bindingKind": "output", "path": path, "paramSource": 0}},
        }
        rows = [
            {**base, "action": "PlayAudio", "recordStart": 1, "recordLocalId": 1, "serializedActionOrdinal": 0, "actionMapRole": "actionList#1 root"},
            {**base, "action": "PlayAudio", "recordStart": 2, "recordLocalId": 2, "serializedActionOrdinal": 1, "actionMapRole": "actionList#2 linked"},
            {"levelScriptId": "map/9002", "sourceRoot": "Persistent", "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/9002.json", "action": "StopAudio", "recordStart": 3, "recordLocalId": 3, "serializedActionOrdinal": 2, "actionMapRole": "actionList#3 linked", "runtimeSlotStatus": "active-final-serialized-slot", "fields": {"audioId": {"bindingKind": "dynamic", "path": path, "paramSource": 0}}},
        ]
        details, summary = audio_semantics._build_levelscript_audio_lifecycle(rows)
        consumer = next(row for row in details if row["role"] == "consumer")
        self.assertEqual(consumer["joinStatus"], "unresolved_ambiguous_or_shadowed_producer")
        self.assertGreaterEqual(summary["unresolvedCount"], 1)
        shadowed = {**base, "action": "PlayAudio", "recordStart": 4, "recordLocalId": 4, "serializedActionOrdinal": 3, "actionMapRole": "actionList#4 linked", "runtimeSlotStatus": "shadowed", "fields": {"audioPlayingId": {"bindingKind": "output", "path": path, "paramSource": 0}}}
        details, _summary = audio_semantics._build_levelscript_audio_lifecycle([rows[0], shadowed, rows[2]])
        consumer = next(row for row in details if row["role"] == "consumer")
        self.assertEqual(consumer["joinStatus"], "unresolved_ambiguous_or_shadowed_producer")

    def test_levelscript_lifecycle_rejects_runtime_output_and_cross_root_paths(self) -> None:
        path = "$8@_audioPlayingId"
        producer = {
            "action": "PlayAudio",
            "levelScriptId": "map/9003",
            "sourceRoot": "Persistent",
            "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/9003.json",
            "recordStart": 1,
            "recordLocalId": 1,
            "runtimeSlotStatus": "active-final-serialized-slot",
            "fields": {
                "audioPlayingId": {
                    "bindingKind": "output",
                    "paramSource": 100,
                    "path": path,
                },
            },
        }
        consumer = {
            "action": "StopAudio",
            "levelScriptId": "map/9003",
            "sourceRoot": "Persistent",
            "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/9003.json",
            "recordStart": 2,
            "recordLocalId": 2,
            "runtimeSlotStatus": "active-final-serialized-slot",
            "fields": {
                "audioId": {
                    "bindingKind": "dynamic",
                    "paramSource": 100,
                    "path": path,
                },
            },
        }
        details, summary = audio_semantics._build_levelscript_audio_lifecycle(
            [producer, consumer]
        )
        self.assertEqual("runtime", audio_semantics._levelscript_parameter_source(
            producer["fields"]["audioPlayingId"]
        ))
        self.assertEqual(0, summary["exactJoinCount"])
        self.assertIn(
            "unresolved_invalid_producer_parameter_source",
            {row["joinStatus"] for row in details},
        )
        self.assertTrue(
            all(row["role"] == "unresolved" for row in details)
        )

        valid_producer = {
            **producer,
            "sourceRoot": "Persistent",
            "sourcePath": "structured/Persistent/Data/Json/LevelScriptData/map/9003.json",
            "fields": {
                "audioPlayingId": {
                    "bindingKind": "output",
                    "paramSource": 0,
                    "path": path,
                },
            },
        }
        _same_root_details, same_root_summary = audio_semantics._build_levelscript_audio_lifecycle(
            [valid_producer, consumer]
        )
        self.assertEqual(0, same_root_summary["exactJoinCount"])
        valid_consumer = {
            **consumer,
            "fields": {
                "audioId": {
                    "bindingKind": "dynamic",
                    "paramSource": 0,
                    "path": path,
                },
            },
        }
        legal_and_malformed_details, legal_and_malformed_summary = (
            audio_semantics._build_levelscript_audio_lifecycle(
                [valid_producer, producer, valid_consumer]
            )
        )
        self.assertEqual(0, legal_and_malformed_summary["exactJoinCount"])
        legal_and_malformed_consumer = next(
            row
            for row in legal_and_malformed_details
            if row.get("role") == "consumer"
        )
        self.assertEqual(
            "unresolved_ambiguous_or_shadowed_producer",
            legal_and_malformed_consumer["joinStatus"],
        )
        cross_root_consumer = {
            **consumer,
            "sourceRoot": "StreamingAssets",
            "sourcePath": "structured/StreamingAssets/Data/Json/LevelScriptData/map/9003.json",
        }
        _details, cross_root_summary = audio_semantics._build_levelscript_audio_lifecycle(
            [valid_producer, cross_root_consumer]
        )
        self.assertEqual(0, cross_root_summary["exactJoinCount"])
        missing_root = {**consumer, "sourceRoot": None}
        missing_details, missing_summary = audio_semantics._build_levelscript_audio_lifecycle(
            [valid_producer, missing_root]
        )
        self.assertEqual(0, missing_summary["exactJoinCount"])
        self.assertIn(
            "unresolved_missing_or_invalid_source_identity",
            {row["joinStatus"] for row in missing_details},
        )
        for bad_path in (
            "structured/Persistent/Data/Json/LevelScriptData/map/other.json",
            "structured/Persistent/Data/Json/LevelScriptData/map/9003.bin",
            "structured/Persistent/Data/Json/LevelScriptData/map/../9003.json",
            "C:/structured/Persistent/Data/Json/LevelScriptData/map/9003.json",
        ):
            bad_path_consumer = {**valid_consumer, "sourcePath": bad_path}
            bad_details, bad_summary = audio_semantics._build_levelscript_audio_lifecycle(
                [valid_producer, bad_path_consumer]
            )
            self.assertEqual(0, bad_summary["exactJoinCount"])
            self.assertIn(
                "unresolved_missing_or_invalid_source_identity",
                {row["joinStatus"] for row in bad_details},
            )

    def test_levelscript_param_source_and_brief_property_integer_types_fail_closed(self) -> None:
        self.assertEqual(
            "runtime",
            audio_semantics._levelscript_parameter_source({
                "bindingKind": "output", "paramSource": 100, "path": "$1@_id",
            }),
        )
        self.assertEqual(
            "runtime",
            audio_semantics._levelscript_parameter_source({
                "bindingKind": "output", "paramSource": 300, "path": "$1@_id",
            }),
        )
        self.assertEqual(
            "output",
            audio_semantics._levelscript_parameter_source({
                "bindingKind": "output", "paramSource": 0, "path": "$1@_id",
            }),
        )

        brief = {
            "properties": [{
                "name": "CueName",
                "value": {
                    "valueType": 7,
                    "atomCount": 1,
                    "atoms": [{"valueBit64": 0, "text": "au_fixture"}],
                },
            }],
        }
        binding = {
            "bindingKind": "dynamic",
            "paramSource": 200,
            "idRef": -1,
            "path": "CueName",
        }
        self.assertEqual("au_fixture", level_bindings.resolve_levelscript_dynamic_property_string(brief, binding)["value"])
        invalid_bindings = (
            {**binding, "paramSource": 200.0},
            {**binding, "paramSource": True},
            {**binding, "idRef": -1.0},
            {**binding, "idRef": True},
        )
        for invalid_binding in invalid_bindings:
            self.assertIsNone(
                level_bindings.resolve_levelscript_dynamic_property_string(
                    brief, invalid_binding
                )
            )
        invalid_briefs = (
            {"properties": [{**brief["properties"][0], "value": {
                **brief["properties"][0]["value"], "valueType": 7.0,
            }}]},
            {"properties": [{**brief["properties"][0], "value": {
                **brief["properties"][0]["value"], "valueType": True,
            }}]},
            {"properties": [{**brief["properties"][0], "value": {
                **brief["properties"][0]["value"], "atomCount": 1.0,
            }}]},
            {"properties": [{**brief["properties"][0], "value": {
                **brief["properties"][0]["value"], "atomCount": True,
            }}]},
        )
        for invalid_brief in invalid_briefs:
            self.assertIsNone(
                level_bindings.resolve_levelscript_dynamic_property_string(
                    invalid_brief, binding
                )
            )


if __name__ == "__main__":
    unittest.main()
