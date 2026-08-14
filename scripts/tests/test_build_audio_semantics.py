import json
import tempfile
import unittest
from pathlib import Path
from struct import pack
from unittest.mock import patch

from scripts import build_audio_semantics as audio_semantics
from scripts.audio_semantics import (
    authored_components,
    event_projection,
    event_summary,
    identifiers,
    interactive_components,
    managed_literals,
    native_evidence,
    purpose,
    responsive_voice,
    table_contexts,
    voice_requests,
)


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

    def test_complete_shared_wwise_media_set_records_leaf_equivalence_only(self) -> None:
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
        self.assertEqual(unknown["category"], "unknown")
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
        self.assertEqual(rows[0]["playbackLocationStatus"], "unknown")

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
        self.assertEqual(event_projection.event_category("unproven_name"), "unknown")

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

        adapter_chains = {row["id"]: row for row in adapter["nativeCallChains"]}
        post = adapter_chains["adapterPostEventToWwise"]
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
        self.assertEqual(
            [row["methodIndex"] for row in external["stages"]],
            [479931, 480011, 444124, 444128, 444126, 446376, 480009, 39041, 39052],
        )
        self.assertIn("0x18f361150", external["stages"][5]["relation"])
        action = adapter_chains["playingIdActionQueueToWwise"]
        self.assertEqual(
            [row["methodIndex"] for row in action["stages"]],
            [480012, 480160, 480165, 446431],
        )
        self.assertEqual(len(animator["nativeCallChains"]), 2)
        self.assertEqual(skill["nativeCallChains"][0]["id"], "skillPlaySoundActionRouting")
        self.assertEqual(levelscript["nativeCallChains"][0]["id"], "levelScriptAudioActionRouting")
        self.assertEqual(len(wwise["nativeCallChains"]), 7)
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
        self.assertGreaterEqual(len(catalog), 134)
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

            semantics = table_contexts.collect_audio_cue_semantics(root)

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
            self.assertEqual(spawn["authoredFieldRole"], "_spawnAudioEvent")
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
                "authoredFieldRole": "_onHitAudioEvent",
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
        self.assertEqual(rows[0]["triggerRole"], "_onHitAudioEvent")
        self.assertEqual(
            rows[0]["runtimeActivationStatus"],
            "monoBehaviourComponentExecutionNotObserved",
        )

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
            self.assertEqual(spawn["authoredFieldRole"], "soundSpawn")
            self.assertEqual(spawn["managedReferenceClass"], "PlayLineSound")
            self.assertEqual(spawn["managedReferencePayloadLength"], 24)
            self.assertEqual(spawn["gameObjectName"], "Line FX")
            finish = result["eventContexts"]["#0x87654321"][0]
            self.assertEqual(finish["authoredFieldRole"], "soundFinish")
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
            self.assertEqual(semantics["stats"]["audioBehaviorCount"], 5)
            self.assertEqual(semantics["stats"]["normalEventContextCount"], 2)
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

        direct_media_check = 'if (record?.audioDialogKey || record?.audioDialogPath) return ["directDialogMedia"]'
        self.assertIn(direct_media_check, relation_body)
        self.assertLess(
            relation_body.index(direct_media_check),
            relation_body.index("record?.eventIds"),
        )

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


if __name__ == "__main__":
    unittest.main()
