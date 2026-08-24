from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from scripts.audio_semantics import event_summary, media_ownership


def _scene_payload(role: str, *, media_id: int = 7, src: str = "/audio/7.flac"):
    event = {"role": role, "possibleMedia": [{"id": media_id, "src": src}]}
    return {
        "scenes": [{
            "sceneId": "map01_lv001",
            "definitions": [{"events": [event]}],
        }],
        "sceneEmitters": [],
    }


class MediaOwnershipTests(unittest.TestCase):
    def test_character_catalog_and_exact_chr_namespace_link_events(self):
        with tempfile.TemporaryDirectory() as temporary:
            export_root = Path(temporary)
            table = export_root / "structured/StreamingAssets/Table/CharacterTable.json"
            table.parent.mkdir(parents=True)
            table.write_text(json.dumps({
                "chr_0028_wulfa": {},
                "chr_0031_mifu": {},
                "chr_0032_lizhiyan": {},
            }), encoding="utf-8")
            catalog = media_ownership.collect_character_audio_identity_catalog(
                export_root
            )

        events = [
            {
                "id": "au_chr_0028_wulfa_normal_skill",
                "category": "sfx",
                "contexts": [{"kind": "characterSkill", "ownerId": "chr_0028_wulfa"}],
            },
            {
                "id": "au_ui_event_sns_topic_chr_0028_wulfa_3_a",
                "category": "ui",
                "contexts": [],
            },
            {
                "id": "au_chr_0031_normal_skill_1_foley",
                "category": "sfx",
                "contexts": [{"kind": "characterSkill", "ownerId": "chr_0031_mifu"}],
            },
            {
                "id": "au_actor_wulfa_ui_overview_start",
                "category": "ui",
                "contexts": [],
            },
            {
                "id": "lizhiyan_relax_sp_01",
                "category": "unknown",
                "contexts": [{
                    "kind": "characterAnimation",
                    "ownerId": "chr_0032_lizhiyan",
                }],
            },
            {"id": "au_chr_combust_debuff_loop", "category": "sfx", "contexts": []},
        ]

        counts = media_ownership.annotate_event_character_audio_identity(
            events,
            catalog,
        )

        self.assertEqual(catalog["status"], "validatedCharacterTableKeys")
        self.assertEqual(events[0]["characterAudioOwnerIds"], ["chr_0028_wulfa"])
        self.assertEqual(
            events[0]["characterAudioIdentityStatus"],
            "exactCharacterTableKeyToken",
        )
        self.assertEqual(
            events[0]["characterAudioContextRelationshipStatus"],
            "exactContextOwnerAgreement",
        )
        self.assertEqual(events[1]["characterAudioOwnerTokens"], ["wulfa"])
        self.assertEqual(
            events[2]["characterAudioIdentityStatus"],
            "uniqueCharacterTableNumericIdPrefix",
        )
        self.assertEqual(events[3]["characterAudioOwnerIds"], ["chr_0028_wulfa"])
        self.assertEqual(events[3]["characterAudioIdentityStatus"], "uniqueCharacterTableActorToken")
        self.assertEqual(events[4]["characterAudioOwnerIds"], ["chr_0032_lizhiyan"])
        self.assertEqual(events[4]["characterAudioIdentityStatus"], "uniqueCharacterTableTokenPrefix")
        self.assertNotIn("characterAudioOwnerIds", events[5])
        self.assertEqual(counts["eventsWithCharacterAudioIdentity"], 5)

    def test_character_namespace_gameplay_projection_keeps_identity_separate(self):
        projected = media_ownership.project_character_namespace_gameplay_audio([
            {
                "id": "au_actor_wulfa_ui_open",
                "category": "ui",
                "foundInWwise": True,
                "possibleMediaCount": 1,
                "playRootCount": 1,
                "characterAudioIdentityStatus": "uniqueCharacterTableTokenPrefix",
                "characterAudioOwnerIds": ["chr_0028_wulfa"],
                "characterAudioNameMatchEvidence": (
                    "uniqueCharacterTableTokenAtWwiseEventPrefix"
                ),
                "media": [{
                    "mediaId": 7,
                    "src": "/export/audio/7.flac",
                    "duration": 1.25,
                    "contentSha256": "abc",
                }],
            },
            {
                "id": "au_unowned",
                "possibleMediaCount": 1,
                "media": [{"mediaId": 8, "src": "/export/audio/8.flac"}],
            },
        ])

        rows = projected["characters"]["chr_0028_wulfa"]
        self.assertEqual([row["id"] for row in rows], ["au_actor_wulfa_ui_open"])
        self.assertEqual(rows[0]["audio"][0]["mediaId"], 7)
        self.assertEqual(
            rows[0]["authoredNamespaceOwnershipStatus"],
            "exactCharacterTableNamespaceIdentity",
        )
        self.assertEqual(rows[0]["runtimeActivationStatus"], "unobserved")
        self.assertNotIn("triggerBindingStatus", rows[0])
        self.assertNotIn("sourceSkillIds", rows[0])
        self.assertEqual(projected["counts"]["uniqueEvents"], 1)
        self.assertEqual(projected["counts"]["mediaOwnerAssociations"], 1)

    def test_actor_namespace_fails_closed_on_duplicate_tokens_and_bad_delimiters(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            table = root / "structured/StreamingAssets/Table/CharacterTable.json"
            table.parent.mkdir(parents=True)
            table.write_text(json.dumps({
                "chr_0001_wulfa": {},
                "chr_0002_wulfa": {},
            }), encoding="utf-8")
            catalog = media_ownership.collect_character_audio_identity_catalog(root)
        events = [
            {"id": "au_actor_wulfa_ui_open", "contexts": []},
            {"id": "au_actor_wulfa2_ui_open", "contexts": []},
            {"id": "prefix_au_actor_wulfa_ui_open", "contexts": []},
        ]
        result = media_ownership.annotate_event_character_audio_identity(events, catalog)
        self.assertEqual(result["eventsWithCharacterAudioIdentity"], 0)
        self.assertTrue(all("characterAudioOwnerIds" not in event for event in events))

    def test_enemy_namespace_projection_requires_exact_catalog_prefix(self):
        projected = media_ownership.project_enemy_namespace_gameplay_audio(
            [
                {
                    "id": "au_eny_0007_mimicw_die",
                    "name": "au_eny_0007_mimicw_die",
                    "eventIdentityStatus": "recoveredAuthoredName",
                    "purposeKnowledgeStatus": "unknownUse",
                    "playbackLocationStatus": "unknown",
                    "possibleMediaCount": 1,
                    "media": [{"mediaId": 7, "src": "/export/audio/7.flac"}],
                },
                {
                    "id": "au_eny_0007_mimicw2_skill01",
                    "eventIdentityStatus": "recoveredAuthoredName",
                    "purposeKnowledgeStatus": "unknownUse",
                    "playbackLocationStatus": "unknown",
                    "possibleMediaCount": 1,
                    "media": [{"mediaId": 8, "src": "/export/audio/8.flac"}],
                },
                {
                    "id": "au_monster_aghornb_hit_fullbody_big_stagger",
                    "eventIdentityStatus": "recoveredAuthoredName",
                    "purposeKnowledgeStatus": "unknownUse",
                    "playbackLocationStatus": "unknown",
                    "possibleMediaCount": 1,
                    "media": [{"mediaId": 9, "src": "/export/audio/9.flac"}],
                },
            ],
            ["eny_0007_mimicw", "eny_0023_aghornb"],
        )
        rows = projected["enemies"]["eny_0007_mimicw"]
        self.assertEqual([row["id"] for row in rows], ["au_eny_0007_mimicw_die"])
        self.assertEqual(rows[0]["authoredNamespaceOwnershipStatus"], "recoveredEnemyNamespaceIdentity")
        self.assertEqual(projected["counts"]["uniqueEvents"], 2)
        monster_rows = projected["enemies"]["eny_0023_aghornb"]
        self.assertEqual([row["id"] for row in monster_rows], ["au_monster_aghornb_hit_fullbody_big_stagger"])
        self.assertEqual(
            monster_rows[0]["namespaceEvidence"],
            "uniqueRecoveredMonsterTokenAgainstCurrentEnemyTable",
        )

    def test_monster_namespace_fails_closed_on_duplicate_token(self):
        projected = media_ownership.project_enemy_namespace_gameplay_audio(
            [{
                "id": "au_monster_aghornb_hit",
                "eventIdentityStatus": "recoveredAuthoredName",
                "purposeKnowledgeStatus": "unknownUse",
                "playbackLocationStatus": "unknown",
                "possibleMediaCount": 1,
                "media": [{"mediaId": 9, "src": "/export/audio/9.flac"}],
            }],
            ["eny_0023_aghornb", "eny_0042_aghornb"],
        )
        self.assertEqual(projected["counts"]["uniqueEvents"], 0)
        self.assertEqual(projected["counts"]["enemies"], 0)

    def test_native_voice_response_projection_requires_unique_longest_enemy_prefix(self):
        context = {
            "kind": "nativeVoiceTriggerCallsite",
            "triggerKey": "combat_dead",
            "triggerRole": "temporarySpeakerDeathResponse",
            "consumerType": "Beyond.Gameplay.Audio.VoiceTempSpeakerProcessor",
            "consumerMethod": "ResponseDeath",
            "targetBinding": "temporarySpeakerEntityAndSpeakerType",
            "triggerBindingStatus": (
                "exactCurrentBuildLiteralArgumentAndAudioDialogEventSuffix"
            ),
            "runtimeActivationStatus": (
                "nativeBranchAndLiveResponseSelectionUnobserved"
            ),
            "runtimeSelectionStatus": (
                "speakerCooldownProbabilityToneAndLiveChoiceUnobserved"
            ),
            "triggerRequestEvidence": [
                "exactNativeLiteralLoadIntoTriggerArgument",
                "exactAudioDialogPathHashEqualsVoiceIdAndWwiseEventId",
            ],
            "nativeMappingId": "current-build-test",
            "methodVa": "0x1000",
            "literalLoadVa": "0x1010",
            "playbackInvocationVa": "0x1020",
        }
        projected = media_ownership.project_enemy_native_voice_response_audio(
            [
                {
                    "id": "eny_0053_hsmob_tx01_combat_dead_sv",
                    "category": "voice",
                    "foundInWwise": True,
                    "possibleMediaCount": 1,
                    "contexts": [context],
                    "media": [{
                        "mediaId": 7,
                        "src": "/export/audio/7.flac",
                        "duration": 1.5,
                    }],
                },
                {
                    "id": "eny_0053_hsmob2_combat_dead_sv",
                    "contexts": [context],
                    "media": [],
                },
                {
                    "id": "eny_generic_combat_dead_sv",
                    "contexts": [context],
                    "media": [],
                },
            ],
            ["eny_0053_hsmob", "eny_0053_hsmob_tx01"],
        )

        rows = projected["enemies"]["eny_0053_hsmob_tx01"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "eny_0053_hsmob_tx01_combat_dead_sv")
        self.assertEqual(rows[0]["triggerKey"], "combat_dead")
        self.assertEqual(rows[0]["mediaRefs"][0]["mediaId"], 7)
        self.assertEqual(
            rows[0]["ownerBindingStatus"],
            "exactCurrentEnemyTableIdPrefixInNativeVoiceEvent",
        )
        self.assertEqual(
            rows[0]["runtimeActivationStatus"],
            "nativeBranchAndLiveResponseSelectionUnobserved",
        )
        self.assertEqual(projected["counts"]["triggerContexts"], 1)
        self.assertEqual(projected["counts"]["unmatchedContexts"], 2)
        self.assertNotIn("eny_0053_hsmob", projected["enemies"])

    def test_enemy_response_candidates_require_explicit_owner_and_skip_native(self):
        projected = media_ownership.project_enemy_response_candidate_audio(
            [
                {
                    "id": "enemy_voice_exact",
                    "category": "voice",
                    "foundInWwise": True,
                    "possibleMediaCount": 1,
                    "contexts": [
                        {"kind": "responsiveDialogVoice", "speakerId": "eny_0007_mimicw", "triggerKey": "combat_hurt", "evidence": "responsive"},
                        {"kind": "abilityVoiceTriggerAction", "ownerId": "eny_0007_mimicw", "triggerKey": "combat_hurt", "evidence": "ability"},
                    ],
                    "media": [{"mediaId": 7, "src": "/audio/7.flac"}],
                },
                {
                    "id": "eny_0007_mimicw_name_only",
                    "contexts": [],
                    "media": [{"mediaId": 8, "src": "/audio/8.flac"}],
                },
                {
                    "id": "enemy_voice_native",
                    "contexts": [
                        {"kind": "responsiveDialogVoice", "speakerId": "eny_0007_mimicw"},
                        {"kind": "nativeVoiceTriggerCallsite", "triggerKey": "combat_dead"},
                    ],
                    "media": [{"mediaId": 9, "src": "/audio/9.flac"}],
                },
            ],
            ["eny_0007_mimicw"],
        )
        rows = projected["enemies"]["eny_0007_mimicw"]
        self.assertEqual([row["id"] for row in rows], ["enemy_voice_exact"])
        self.assertEqual(rows[0]["evidenceKinds"], [
            "abilityVoiceTriggerAction", "responsiveDialogVoice",
        ])
        self.assertEqual(rows[0]["mediaRefs"][0]["mediaId"], 7)
        self.assertEqual(rows[0]["ownerBindingStatus"], "exactResponseContextEnemyId")
        self.assertEqual(projected["counts"]["uniqueEvents"], 1)

    def test_native_voice_response_projection_requires_longest_character_prefix(self):
        context = {
            "kind": "nativeVoiceTriggerCallsite",
            "triggerKey": "combat_heavy_hurt",
            "triggerRole": "temporarySpeakerHeavyHurtResponse",
            "consumerType": "Beyond.Gameplay.Audio.VoiceTempSpeakerProcessor",
            "consumerMethod": "ResponseHeavyHurt",
            "triggerBindingStatus": (
                "exactCurrentBuildLiteralArgumentAndAudioDialogEventSuffix"
            ),
            "runtimeActivationStatus": (
                "nativeBranchAndLiveResponseSelectionUnobserved"
            ),
            "nativeMappingId": "current-build-character-test",
        }
        projected = media_ownership.project_character_native_voice_response_audio(
            [
                {
                    "id": "chr_0003_endminf_combat_heavy_hurt_sv",
                    "category": "voice",
                    "foundInWwise": True,
                    "possibleMediaCount": 1,
                    "contexts": [context],
                    "media": [{"mediaId": 8, "src": "/export/audio/8.flac"}],
                },
                {
                    "id": "chr_0003_endminf2_combat_heavy_hurt_sv",
                    "contexts": [context],
                    "media": [],
                },
                {
                    "id": "chr_generic_combat_heavy_hurt_sv",
                    "contexts": [context],
                    "media": [],
                },
            ],
            ["chr_0003_endmin", "chr_0003_endminf"],
        )

        rows = projected["characters"]["chr_0003_endminf"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["mediaRefs"][0]["mediaId"], 8)
        self.assertEqual(
            rows[0]["ownerBindingStatus"],
            "exactCurrentCharacterTableIdPrefixInNativeVoiceEvent",
        )
        self.assertEqual(
            rows[0]["runtimeActivationStatus"],
            "nativeBranchAndLiveResponseSelectionUnobserved",
        )
        self.assertEqual(projected["counts"]["unmatchedContexts"], 2)
        self.assertNotIn("chr_0003_endmin", projected["characters"])

    def test_animation_callback_link_preserves_non_matching_clip_and_owner(self):
        events = [
            {
                "id": "pograni_stopwatch_open",
                "category": "unknown",
                "contexts": [{
                    "kind": "characterAnimation",
                    "ownerId": "chr_0029_pograni",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": [
                        "A_actor_pograni_relax_sp_02",
                        "A_actor_pograni_ui_relax_sp_02",
                    ],
                    "actionKinds": ["action"],
                    "clipReachability": "unresolved",
                    "animationOccurrenceCount": 2,
                }],
            },
            {
                "id": "not_audio_callback",
                "category": "unknown",
                "contexts": [{
                    "kind": "characterAnimation",
                    "ownerId": "chr_0029_pograni",
                    "animationFunctions": ["OnCustomFootStep"],
                    "animationClips": ["A_actor_pograni_relax_sp_02"],
                }],
            },
        ]

        counts = media_ownership.annotate_event_animation_callback_links(events)

        self.assertEqual(events[0]["category"], "unknown")
        self.assertEqual(
            events[0]["animationCallbackLinkStatus"],
            "exactSerializedAnimationClipAudioCallback",
        )
        self.assertEqual(
            events[0]["animationCallbackOwnerIds"],
            ["chr_0029_pograni"],
        )
        self.assertEqual(
            events[0]["animationCallbackClips"],
            [
                "A_actor_pograni_relax_sp_02",
                "A_actor_pograni_ui_relax_sp_02",
            ],
        )
        self.assertNotIn("animationCallbackLinkStatus", events[1])
        self.assertEqual(counts["eventsWithAnimationCallbackLink"], 1)

        rows = [{
            "id": 9,
            "audioCategory": "unknown",
            "eventIds": ["pograni_stopwatch_open"],
        }]
        media_counts = media_ownership.annotate_media_coarse_ownership(
            rows,
            {},
            event_rows=events,
        )
        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["characterAnimation"])
        self.assertEqual(
            rows[0]["animationCallbackOwnerIds"],
            ["chr_0029_pograni"],
        )
        self.assertEqual(
            rows[0]["animationCallbackOwnershipStatus"],
            "exactAnimationCallbackOwnerToPossibleMedia",
        )
        self.assertEqual(media_counts["mediaWithAnimationCallbackLink"], 1)

    def test_character_event_identity_projects_unique_and_shared_media_owners(self):
        events = [
            {
                "id": "au_chr_0028_wulfa_shared",
                "category": "sfx",
                "characterAudioIdentityStatus": "exactCharacterTableKeyToken",
                "characterAudioOwnerIds": ["chr_0028_wulfa"],
                "characterAudioOwnerTokens": ["wulfa"],
                "characterAudioNameMatchEvidence": (
                    "exactDelimitedCharacterTableKeyInWwiseEventId"
                ),
                "characterAudioContextRelationshipStatus": "nameIdentityOnly",
            },
            {
                "id": "au_chr_0031_mifu_shared",
                "category": "sfx",
                "characterAudioIdentityStatus": "exactCharacterTableKeyToken",
                "characterAudioOwnerIds": ["chr_0031_mifu"],
                "characterAudioOwnerTokens": ["mifu"],
                "characterAudioNameMatchEvidence": (
                    "exactDelimitedCharacterTableKeyInWwiseEventId"
                ),
                "characterAudioContextRelationshipStatus": "nameIdentityOnly",
            },
        ]
        rows = [
            {
                "id": 1,
                "audioCategory": "unknown",
                "eventIds": ["au_chr_0028_wulfa_shared"],
            },
            {
                "id": 2,
                "audioCategory": "unknown",
                "eventIds": [
                    "au_chr_0028_wulfa_shared",
                    "au_chr_0031_mifu_shared",
                ],
            },
        ]

        counts = media_ownership.annotate_media_coarse_ownership(
            rows,
            {},
            event_rows=events,
        )

        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["characterAudio"])
        self.assertEqual(rows[0]["characterAudioOwnerIds"], ["chr_0028_wulfa"])
        self.assertEqual(
            rows[0]["characterAudioOwnershipStatus"],
            "exactNamedCharacterEventToPossibleMedia",
        )
        self.assertEqual(
            rows[1]["characterAudioOwnerIds"],
            ["chr_0028_wulfa", "chr_0031_mifu"],
        )
        self.assertEqual(
            rows[1]["characterAudioOwnershipStatus"],
            "sharedAcrossNamedCharacterEvents",
        )
        self.assertEqual(counts["mediaWithCharacterAudioIdentity"], 2)
        self.assertEqual(counts["mediaSharedAcrossNamedCharacterEvents"], 1)

    def test_exact_same_name_animation_callback_promotes_event_to_action_sfx(self):
        events = [{
            "id": "wulfa_relax_sp_02",
            "category": "unknown",
            "contexts": [{
                "kind": "characterAnimation",
                "ownerId": "chr_0028_wulfa",
                "animationFunctions": ["PostAudioEvent"],
                "animationClips": [
                    "A_actor_wulfa_relax_sp_02",
                    "A_actor_wulfa_ui_relax_sp_02",
                ],
            }],
        }]

        counts = media_ownership.annotate_event_animation_action_identity(events)

        self.assertEqual(events[0]["category"], "sfx")
        self.assertEqual(events[0]["categoryEvidence"], "exactSameNameAnimationActionEvent")
        self.assertEqual(
            events[0]["animationActionMatchingClips"],
            ["A_actor_wulfa_relax_sp_02"],
        )
        self.assertEqual(events[0]["animationActionOwnerIds"], ["chr_0028_wulfa"])
        self.assertEqual(events[0]["animationActionOwnershipDomains"], ["characterAction"])
        self.assertEqual(counts["eventsWithExactAnimationActionNameMatch"], 1)

    def test_similar_but_not_exact_animation_name_does_not_promote(self):
        events = [{
            "id": "wulfa_relax_sp_02",
            "category": "unknown",
            "contexts": [{
                "kind": "characterAnimation",
                "animationFunctions": ["PostAudioEvent"],
                "animationClips": ["A_actor_wulfa_ui_relax_sp_02"],
            }],
        }]

        counts = media_ownership.annotate_event_animation_action_identity(events)

        self.assertEqual(events[0]["category"], "unknown")
        self.assertNotIn("animationActionNameMatchStatus", events[0])
        self.assertEqual(counts["eventsWithExactAnimationActionNameMatch"], 0)

    def test_same_name_without_audio_callback_function_does_not_promote(self):
        events = [{
            "id": "wulfa_relax_sp_02",
            "category": "unknown",
            "contexts": [{
                "kind": "characterAnimation",
                "animationFunctions": ["OnCustomFootStep"],
                "animationClips": ["A_actor_wulfa_relax_sp_02"],
            }],
        }]

        media_ownership.annotate_event_animation_action_identity(events)

        self.assertEqual(events[0]["category"], "unknown")

    def test_exact_animation_action_event_projects_to_media(self):
        events = [{
            "id": "wulfa_relax_sp_02",
            "category": "unknown",
            "contexts": [{
                "kind": "characterAnimation",
                "ownerId": "chr_0028_wulfa",
                "animationFunctions": ["PostAudioEvent"],
                "animationClips": ["A_actor_wulfa_relax_sp_02"],
            }],
        }]
        media_ownership.annotate_event_animation_action_identity(events)
        rows = [{
            "id": 903988843,
            "audioCategory": "unknown",
            "eventIds": ["wulfa_relax_sp_02"],
            "eventContextKinds": ["characterAnimation"],
        }]

        counts = media_ownership.annotate_media_coarse_ownership(
            rows,
            {},
            event_rows=events,
        )

        self.assertEqual(rows[0]["semanticCategory"], "sfx")
        self.assertEqual(
            rows[0]["coarseOwnershipDomains"],
            ["characterAction", "characterAnimation"],
        )
        self.assertEqual(rows[0]["animationActionEventIds"], ["wulfa_relax_sp_02"])
        self.assertEqual(
            rows[0]["animationActionMatchingClips"],
            ["A_actor_wulfa_relax_sp_02"],
        )
        self.assertEqual(rows[0]["animationActionOwnerIds"], ["chr_0028_wulfa"])
        self.assertEqual(counts["mediaWithExactAnimationActionNameMatch"], 1)

    def test_outdoor_room_tone_recovers_scene_ambience(self):
        rows = [{
            "id": "7",
            "src": "/audio/7.flac",
            "audioCategory": "unknown",
            "purposeKnowledgeStatus": "authoredContextKnown",
        }]

        counts = media_ownership.annotate_media_coarse_ownership(
            rows,
            _scene_payload("outdoorRoomToneEvent"),
        )

        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["sceneEnvironment"])
        self.assertEqual(rows[0]["coarseOwnershipSceneIds"], ["map01_lv001"])
        self.assertEqual(rows[0]["semanticCategory"], "ambience")
        self.assertEqual(rows[0]["semanticCategoryEvidence"], "exactCoarseOwnershipRole")
        self.assertEqual(counts["mediaSemanticCategoryFromCoarseOwnership"], 1)

    def test_generic_scene_emitter_recovers_domain_without_guessing_category(self):
        rows = [{"id": 8, "src": "/audio/8.flac", "audioCategory": "unknown"}]
        scene = {
            "scenes": [],
            "sceneEmitters": [{
                "eventRequests": [{
                    "semanticRole": "authoredSceneEmitterEvent",
                    "possibleMedia": [{"id": 8, "src": "/audio/8.flac"}],
                }],
            }],
        }

        media_ownership.annotate_media_coarse_ownership(rows, scene)

        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["sceneObject"])
        self.assertNotIn("semanticCategory", rows[0])
        self.assertEqual(rows[0]["coarseOwnershipSceneIds"], [])

    def test_ambient_emitter_name_evidence_recovers_ambience(self):
        rows = [{"id": 9, "src": "/audio/9.flac", "audioCategory": "unknown"}]
        scene = {
            "scenes": [],
            "sceneEmitters": [{
                "eventRequests": [{
                    "semanticRole": "authoredAmbientEmitterCandidate",
                    "possibleMedia": [{"id": 9, "src": "/audio/9.flac"}],
                }],
            }],
        }

        media_ownership.annotate_media_coarse_ownership(rows, scene)

        self.assertEqual(rows[0]["semanticCategory"], "ambience")
        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["sceneEnvironment"])

    def test_context_domains_are_coarse_and_generic_table_hash_is_not_promoted(self):
        rows = [
            {
                "id": 10,
                "audioCategory": "unknown",
                "eventContextKinds": ["characterAnimation", "tableEventHash"],
            },
            {
                "id": 11,
                "audioCategory": "unknown",
                "eventContextKinds": ["tableEventHash"],
            },
        ]

        counts = media_ownership.annotate_media_coarse_ownership(rows, {})

        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["characterAnimation"])
        self.assertNotIn("semanticCategory", rows[0])
        self.assertNotIn("coarseOwnershipDomains", rows[1])
        self.assertEqual(counts["mediaWithCoarseOwnership"], 1)

    def test_remote_common_lifecycle_context_promotes_authored_domain(self):
        rows = [{
            "id": 12,
            "audioCategory": "unknown",
            "purposeKnowledgeStatus": "unknownUse",
            "eventContextKinds": ["remoteCommonLifecycleAudio"],
        }]

        counts = media_ownership.annotate_media_coarse_ownership(rows, {})

        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["remoteCommonAudio"])
        self.assertEqual(rows[0]["coarseOwnershipRoles"], ["remoteCommonLifecycleAudio"])
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "coarseOwnershipKnown")
        self.assertEqual(counts["mediaPurposeRecoveredByCoarseOwnership"], 1)

    def test_exact_external_narration_identity_resolves_purpose_not_playback(self):
        rows = [{
            "id": "955778167792087661",
            "audioCategory": "story_voice",
            "purposeKnowledgeStatus": "unknownUse",
            "playbackLocationStatus": "unknown",
            "externalMediaIdentityStatus": "recoveredAuthoredPathHash",
            "externalAuthoredAudioId": "au_voice_c35m3_3_001",
            "externalAuthoredPath": (
                "v1d4/Narrating/HS_Part04/c35m3/au_voice_c35m3_3_001.wem"
            ),
        }]

        counts = media_ownership.annotate_media_coarse_ownership(rows, {})

        self.assertEqual(rows[0]["coarseOwnershipDomains"], ["missionNarrationVoice"])
        self.assertEqual(rows[0]["purposeKnowledgeStatus"], "coarseOwnershipKnown")
        self.assertEqual(rows[0]["purposeInvestigationPriority"], "resolved")
        self.assertEqual(rows[0]["playbackLocationStatus"], "unknown")
        self.assertEqual(counts["unknownUseMediaWithCoarseOwnership"], 1)
        self.assertEqual(counts["mediaPurposeRecoveredByCoarseOwnership"], 1)

    def test_duplicate_media_id_without_exact_src_fails_closed(self):
        rows = [
            {"id": 12, "src": "/a/12.flac", "audioCategory": "unknown"},
            {"id": 12, "src": "/b/12.flac", "audioCategory": "unknown"},
        ]
        scene = _scene_payload("outdoorRoomToneEvent", media_id=12, src="")

        counts = media_ownership.annotate_media_coarse_ownership(rows, scene)

        self.assertEqual(counts["mediaWithCoarseOwnership"], 0)
        self.assertNotIn("semanticCategory", rows[0])
        self.assertNotIn("semanticCategory", rows[1])

    def _write_animation_tables(
        self,
        root: Path,
        *,
        ambiguous: bool = False,
        template_only: bool = False,
    ) -> None:
        table_root = root / "structured/StreamingAssets/Table"
        table_root.mkdir(parents=True, exist_ok=True)
        (table_root / "CharacterTable.json").write_text(json.dumps({
            "chr_0028_wulfa": {},
        }), encoding="utf-8")
        enemy_rows = {
            "eny_0042_wgthorns": {"templateId": "eny_0042_wgthorns"},
            "eny_0042_wgthorns_variant": {"templateId": "eny_0042_wgthorns"},
        }
        if ambiguous:
            enemy_rows["eny_0043_wgthorns"] = {"templateId": "eny_0043_wgthorns"}
        (table_root / "EnemyTable.json").write_text(
            json.dumps(enemy_rows), encoding="utf-8"
        )
        templates = {
            "eny_0042_wgthorns": {"templateId": "eny_0042_wgthorns"},
            **(
                {"eny_0043_wgthorns": {"templateId": "eny_0043_wgthorns"}}
                if ambiguous else {}
            ),
            **(
                {"eny_0050_silent": {"templateId": "eny_0050_silent"}}
                if template_only else {}
            ),
        }
        (table_root / "EnemyTemplateTable.json").write_text(
            json.dumps(templates), encoding="utf-8"
        )

    def _write_npc_tables(
        self,
        root: Path,
        *,
        info_rows: dict[str, dict] | None = None,
        group_rows: dict[str, dict] | None = None,
        persistent_info: str | None = None,
        persistent_group: str | None = None,
        write_channel: bool = True,
        persistent_channel: str | None = None,
        channel_tokens: tuple[str, ...] = ("jsspsi",),
    ) -> None:
        table_root = root / "structured/StreamingAssets/Table"
        table_root.mkdir(parents=True, exist_ok=True)
        info_rows = info_rows or {
            "si": {
                "npcId": "si",
                "templateId": "npc_chr_0036_jsspsi",
                "voActor": "jsspsi",
                "wwiseId": "jsspsi",
            }
        }
        group_rows = group_rows or {
            "si": {
                "npcNameId": "si",
                "templateId": "npc_chr_0036_jsspsi",
            }
        }
        (table_root / "NpcInfoTable.json").write_text(
            json.dumps(info_rows), encoding="utf-8"
        )
        (table_root / "NpcTemplateGroupTable.json").write_text(
            json.dumps(group_rows), encoding="utf-8"
        )
        if write_channel:
            channel_rows = {
                token: {
                    "narratingWwiseEvent": f"vo_narrating_{token}_default",
                    "radioWwiseEvent": f"vo_narrating_{token}_radio",
                }
                for token in channel_tokens
            }
            (table_root / "AudioDialogChannel.json").write_text(
                json.dumps(channel_rows), encoding="utf-8"
            )
        if persistent_info is not None or persistent_group is not None:
            persistent_root = root / "structured/Persistent/Table"
            persistent_root.mkdir(parents=True, exist_ok=True)
            (persistent_root / "NpcInfoTable.json").write_text(
                persistent_info if persistent_info is not None else json.dumps(info_rows),
                encoding="utf-8",
            )
            (persistent_root / "NpcTemplateGroupTable.json").write_text(
                persistent_group if persistent_group is not None else json.dumps(group_rows),
                encoding="utf-8",
            )
            if write_channel:
                (persistent_root / "AudioDialogChannel.json").write_text(
                    persistent_channel
                    if persistent_channel is not None
                    else json.dumps({
                        token: {
                            "narratingWwiseEvent": f"vo_narrating_{token}_default",
                            "radioWwiseEvent": f"vo_narrating_{token}_radio",
                        }
                        for token in channel_tokens
                    }),
                    encoding="utf-8",
                )

    def test_animation_callback_exact_npc_owner_requires_both_tables(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "jsspsi_spell_start",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        resolution = events[0]["animationCallbackClipResolutions"][0]
        self.assertEqual(catalog["npcCatalogStatus"], "validatedNpcIdentityCatalog")
        self.assertEqual(
            catalog["audioDialogChannelStatus"],
            "validatedAudioDialogChannelCatalog",
        )
        self.assertEqual(resolution["resolutionStatus"], "exactNpcTableToken")
        self.assertEqual(resolution["ownerKind"], "npc")
        self.assertEqual(resolution["ownerId"], "si")
        self.assertEqual(resolution["ownerTemplateId"], "npc_chr_0036_jsspsi")
        self.assertEqual(resolution["ownerActorToken"], "jsspsi")
        self.assertEqual(events[0]["animationCallbackOwnerIds"], ["si"])
        self.assertEqual(events[0]["animationCallbackNpcOwnerIds"], ["si"])
        self.assertEqual(events[0]["animationCallbackOccurrences"][0]["ownerKind"], "npc")
        media_rows = [{
            "id": 1,
            "src": "/audio/jsspsi.flac",
            "audioCategory": "unknown",
            "eventIds": ["jsspsi_spell_start"],
        }]
        media_ownership.annotate_media_coarse_ownership(
            media_rows, {}, event_rows=events
        )
        self.assertEqual(media_rows[0]["animationCallbackNpcOwnerIds"], ["si"])
        self.assertEqual(
            media_rows[0]["animationCallbackNpcOwnerTemplates"],
            ["npc_chr_0036_jsspsi"],
        )

    def test_animation_callback_exact_npc_statuses_agree_on_one_event_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "jsspsi_two_exact_callbacks",
                "contexts": [
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    },
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerKind": "npc",
                        "ownerId": "si",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_finish"],
                    },
                ],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
            media_rows = [{
                "id": 1,
                "src": "/audio/jsspsi.flac",
                "audioCategory": "unknown",
                "eventIds": ["jsspsi_two_exact_callbacks"],
            }]
            media_ownership.annotate_media_coarse_ownership(
                media_rows, {}, event_rows=events
            )

        event = events[0]
        self.assertEqual(
            set(event["animationCallbackResolutionStatuses"]),
            {"exactNpcTableToken", "exactNpcInfoAndTemplateGroup"},
        )
        self.assertEqual(event["animationCallbackOwnershipStatus"], "exactNpcOwnerAgreement")
        self.assertEqual(event["animationCallbackNpcOwnerIds"], ["si"])
        self.assertEqual(media_rows[0]["animationCallbackOwnershipStatus"], "exactNpcOwnerAgreement")
        self.assertEqual(media_rows[0]["animationCallbackNpcOwnerIds"], ["si"])

    def test_animation_callback_exact_npc_plus_unresolved_does_not_promote(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "jsspsi_exact_plus_unresolved",
                "contexts": [
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    },
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerKind": "npc",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_missing_dialog_state_spell_finish"],
                    },
                ],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        event = events[0]
        self.assertIn("exactNpcTableToken", event["animationCallbackResolutionStatuses"])
        self.assertIn("unresolved", event["animationCallbackResolutionStatuses"])
        self.assertEqual(event["animationCallbackOwnershipStatus"], "unresolved")
        self.assertEqual(event["animationCallbackNpcOwnerIds"], [])
        self.assertEqual(event["animationCallbackEntityIds"], [])

    def test_animation_callback_multiple_exact_npc_owners_does_not_promote(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            info_rows = {
                "si": {
                    "npcId": "si",
                    "templateId": "npc_chr_0036_jsspsi",
                    "voActor": "jsspsi",
                    "wwiseId": "jsspsi",
                },
                "other": {
                    "npcId": "other",
                    "templateId": "npc_chr_other",
                    "voActor": "other",
                    "wwiseId": "other",
                },
            }
            group_rows = {
                key: {"npcNameId": key, "templateId": value["templateId"]}
                for key, value in info_rows.items()
            }
            self._write_npc_tables(
                root,
                info_rows=info_rows,
                group_rows=group_rows,
                channel_tokens=("jsspsi", "other"),
            )
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "two_npc_exact_owners",
                "contexts": [
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    },
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerKind": "npc",
                        "ownerId": "other",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_other_dialog_state_spell_finish"],
                    },
                ],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
            media_rows = [{
                "id": 1,
                "src": "/audio/shared.flac",
                "audioCategory": "unknown",
                "eventIds": ["two_npc_exact_owners"],
            }]
            media_ownership.annotate_media_coarse_ownership(
                media_rows, {}, event_rows=events
            )

        event = events[0]
        self.assertEqual(event["animationCallbackOwnershipStatus"], "shared")
        self.assertEqual(event["animationCallbackNpcOwnerIds"], [])
        self.assertEqual(media_rows[0]["animationCallbackNpcOwnerIds"], [])

    def test_media_shared_events_exact_npc_states_agree_on_one_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [
                {
                    "id": "shared_exact_table",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    }],
                },
                {
                    "id": "shared_exact_info",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerKind": "npc",
                        "ownerId": "si",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_finish"],
                    }],
                },
            ]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
            media_rows = [{
                "id": 1,
                "src": "/audio/shared-jsspsi.flac",
                "audioCategory": "unknown",
                "eventIds": ["shared_exact_table", "shared_exact_info"],
            }]
            media_ownership.annotate_media_coarse_ownership(
                media_rows, {}, event_rows=events
            )

        media_row = media_rows[0]
        self.assertEqual(media_row["animationCallbackOwnershipStatus"], "exactNpcOwnerAgreement")
        self.assertEqual(media_row["animationCallbackNpcOwnerIds"], ["si"])
        self.assertEqual(media_row["animationCallbackOwnerIds"], ["si"])
        self.assertEqual(
            set(media_row["animationCallbackResolutionStatuses"]),
            {"exactNpcTableToken", "exactNpcInfoAndTemplateGroup"},
        )

    def test_media_shared_events_exact_npc_plus_unresolved_stays_conservative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [
                {
                    "id": "shared_exact_table",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    }],
                },
                {
                    "id": "shared_unresolved",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerKind": "npc",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_missing_dialog_state_spell_finish"],
                    }],
                },
            ]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
            media_rows = [{
                "id": 1,
                "src": "/audio/shared-unresolved.flac",
                "audioCategory": "unknown",
                "eventIds": ["shared_exact_table", "shared_unresolved"],
            }]
            media_ownership.annotate_media_coarse_ownership(
                media_rows, {}, event_rows=events
            )

        self.assertNotEqual(media_rows[0]["animationCallbackOwnershipStatus"], "exactNpcOwnerAgreement")
        self.assertEqual(media_rows[0]["animationCallbackNpcOwnerIds"], [])

    def test_media_shared_events_multiple_npc_owners_stays_conservative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            info_rows = {
                "si": {
                    "npcId": "si",
                    "templateId": "npc_chr_0036_jsspsi",
                    "voActor": "jsspsi",
                    "wwiseId": "jsspsi",
                },
                "other": {
                    "npcId": "other",
                    "templateId": "npc_chr_other",
                    "voActor": "other",
                    "wwiseId": "other",
                },
            }
            self._write_npc_tables(
                root,
                info_rows=info_rows,
                group_rows={
                    key: {"npcNameId": key, "templateId": value["templateId"]}
                    for key, value in info_rows.items()
                },
                channel_tokens=("jsspsi", "other"),
            )
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [
                {
                    "id": "shared_exact_si",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    }],
                },
                {
                    "id": "shared_exact_other",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerKind": "npc",
                        "ownerId": "other",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_other_dialog_state_spell_finish"],
                    }],
                },
            ]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
            media_rows = [{
                "id": 1,
                "src": "/audio/shared-multiple-npc.flac",
                "audioCategory": "unknown",
                "eventIds": ["shared_exact_si", "shared_exact_other"],
            }]
            media_ownership.annotate_media_coarse_ownership(
                media_rows, {}, event_rows=events
            )

        self.assertNotEqual(media_rows[0]["animationCallbackOwnershipStatus"], "exactNpcOwnerAgreement")
        self.assertEqual(media_rows[0]["animationCallbackNpcOwnerIds"], [])

    def test_media_shared_events_cross_domain_stays_conservative(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [
                {
                    "id": "shared_exact_npc",
                    "contexts": [{
                        "kind": "animationCallbackOwnerUnresolved",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                    }],
                },
                {
                    "id": "shared_exact_character",
                    "contexts": [{
                        "kind": "characterAnimation",
                        "ownerKind": "character",
                        "ownerId": "chr_0028_wulfa",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_actor_wulfa_relax_sp_02"],
                    }],
                },
            ]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
            media_rows = [{
                "id": 1,
                "src": "/audio/shared-cross-domain.flac",
                "audioCategory": "unknown",
                "eventIds": ["shared_exact_npc", "shared_exact_character"],
            }]
            media_ownership.annotate_media_coarse_ownership(
                media_rows, {}, event_rows=events
            )

        self.assertNotEqual(media_rows[0]["animationCallbackOwnershipStatus"], "exactNpcOwnerAgreement")
        self.assertEqual(media_rows[0]["animationCallbackNpcOwnerIds"], [])

    def test_animation_callback_duplicate_npc_token_stays_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            rows = {
                npc_id: {
                    "npcId": npc_id,
                    "templateId": f"npc_{npc_id}",
                    "voActor": "gentleman",
                    "wwiseId": "gentleman",
                }
                for npc_id in ("generic_a", "generic_b")
            }
            groups = {
                npc_id: {"npcNameId": npc_id, "templateId": f"npc_{npc_id}"}
                for npc_id in rows
            }
            self._write_npc_tables(
                root,
                info_rows=rows,
                group_rows=groups,
                channel_tokens=("gentleman",),
            )
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "generic_gentleman",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "ownerKind": "npc",
                    "ownerId": "generic_a",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_actor_gentleman_dialog_state_spell_start"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        resolution = events[0]["animationCallbackClipResolutions"][0]
        self.assertEqual(catalog["npcCatalog"]["counts"]["duplicateTokens"], 1)
        for generic_token in ("gentleman", "lady", "boy", "nefys"):
            self.assertNotEqual(
                len(catalog["npcTokenIds"].get(generic_token) or []),
                1,
                generic_token,
            )
        self.assertEqual(resolution["resolutionStatus"], "ambiguous")
        self.assertEqual(events[0]["animationCallbackNpcOwnerIds"], [])
        self.assertEqual(events[0]["animationCallbackOwnerIds"], [])

    def test_animation_callback_generic_npc_without_audio_channel_stays_unresolved(self):
        for token in ("nefys", "gentleman"):
            with self.subTest(token=token):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self._write_animation_tables(root)
                    npc_id = f"{token}_only"
                    self._write_npc_tables(
                        root,
                        info_rows={npc_id: {
                            "npcId": npc_id,
                            "templateId": f"npc_{npc_id}",
                            "voActor": token,
                            "wwiseId": token,
                        }},
                        group_rows={npc_id: {
                            "npcNameId": npc_id,
                            "templateId": f"npc_{npc_id}",
                        }},
                        write_channel=False,
                    )
                    catalog = media_ownership.collect_animation_entity_catalog(root)
                    events = [{
                        "id": f"generic_{token}",
                        "contexts": [{
                            "kind": "animationCallbackOwnerUnresolved",
                            "animationFunctions": ["PostAudioEvent"],
                            "animationClips": [f"A_actor_{token}_dialog_state_spell_start"],
                        }],
                    }]
                    media_ownership.annotate_event_animation_callback_links(
                        events, entity_catalog=catalog
                    )
                    resolution = events[0]["animationCallbackClipResolutions"][0]
                    self.assertEqual(
                        catalog["audioDialogChannelStatus"],
                        "audioDialogChannelUnavailable",
                    )
                    self.assertEqual(resolution["resolutionStatus"], "unresolved")
                    self.assertEqual(resolution["npcTableIds"], [])
                    self.assertEqual(events[0]["animationCallbackNpcOwnerIds"], [])

    def test_animation_callback_character_context_cannot_upgrade_npc_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "character_context_jsspsi",
                "contexts": [{
                    "kind": "characterAnimation",
                    "ownerKind": "character",
                    "ownerId": "chr_9999_missing",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        resolution = events[0]["animationCallbackClipResolutions"][0]
        self.assertEqual(resolution["resolutionStatus"], "unresolved")
        self.assertEqual(resolution["npcTableIds"], [])
        self.assertNotIn("si", events[0]["animationCallbackEntityIds"])
        self.assertEqual(events[0]["animationCallbackNpcOccurrenceOwnerIds"], [])

    def test_animation_callback_malformed_audio_channel_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(
                root,
                persistent_info=json.dumps({"si": {
                    "npcId": "si",
                    "templateId": "npc_chr_0036_jsspsi",
                    "voActor": "jsspsi",
                    "wwiseId": "jsspsi",
                }}),
                persistent_channel="{malformed",
            )
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "malformed_channel_jsspsi",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        self.assertEqual(
            catalog["audioDialogChannelStatus"],
            "audioDialogChannelMalformed",
        )
        self.assertEqual(
            events[0]["animationCallbackClipResolutions"][0]["resolutionStatus"],
            "unresolved",
        )

    def test_animation_callback_npc_overlay_conflict_and_malformed_fail_closed(self):
        for persistent_info, expected_status in (
            (
                json.dumps({"si": {
                    "npcId": "si",
                    "templateId": "npc_chr_9999_other",
                    "voActor": "jsspsi",
                    "wwiseId": "jsspsi",
                }}),
                "npcCatalogConflicted",
            ),
            ("{malformed", "npcCatalogMalformed"),
        ):
            with self.subTest(expected_status=expected_status):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self._write_animation_tables(root)
                    self._write_npc_tables(
                        root,
                        persistent_info=persistent_info,
                    )
                    catalog = media_ownership.collect_animation_entity_catalog(root)
                    events = [{
                        "id": "conflicted_npc",
                        "contexts": [{
                            "kind": "animationCallbackOwnerUnresolved",
                            "animationFunctions": ["PostAudioEvent"],
                            "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                        }],
                    }]
                    media_ownership.annotate_event_animation_callback_links(
                        events, entity_catalog=catalog
                    )
                    self.assertEqual(catalog["npcCatalogStatus"], expected_status)
                    self.assertEqual(
                        events[0]["animationCallbackClipResolutions"][0]["resolutionStatus"],
                        "unresolved",
                    )
                    self.assertEqual(events[0]["animationCallbackNpcOwnerIds"], [])

    def test_animation_callback_npc_template_mismatch_stays_unresolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(
                root,
                group_rows={"si": {
                    "npcNameId": "si",
                    "templateId": "npc_chr_9999_other",
                }},
            )
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "mismatched_npc",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_actor_jsspsi_dialog_state_spell_start"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        self.assertEqual(catalog["npcCatalogStatus"], "npcCatalogInvalid")
        self.assertEqual(
            events[0]["animationCallbackClipResolutions"][0]["resolutionStatus"],
            "unresolved",
        )

    def test_animation_callback_mixed_event_keeps_npc_owner_at_occurrence_level(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            self._write_npc_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "au_dlg_foley_state_spell_start",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": [
                        "A_actor_gentleman_dialog_state_spell_start",
                        "A_actor_jsspsi_dialog_state_spell_start",
                        "A_actor_lady_dialog_state_spell_start",
                    ],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        event = events[0]
        self.assertIn(event["animationCallbackOwnershipStatus"], {"ambiguous", "unresolved"})
        self.assertNotEqual(event["animationCallbackOwnerIds"], ["si"])
        self.assertEqual(event["animationCallbackNpcOwnerIds"], [])
        self.assertEqual(event["animationCallbackNpcOccurrenceOwnerIds"], ["si"])
        self.assertNotIn("si", event["animationCallbackResolvedEntityIds"])
        self.assertNotIn("si", event["animationCallbackEntityIds"])
        self.assertNotIn("si", event["animationCallbackCandidateEntityIds"])
        npc_rows = [
            row for row in event["animationCallbackOccurrences"]
            if row.get("ownerId") == "si"
        ]
        self.assertEqual(len(npc_rows), 1)
        self.assertEqual(npc_rows[0]["ownerKind"], "npc")

    def test_animation_callback_exact_enemy_instance_and_template(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "enemy_hit",
                "category": "unknown",
                "contexts": [{
                    "kind": "enemyAnimation",
                    "ownerId": "eny_0042_wgthorns",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_monster_wgthorns_hit_mid_right"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
        row = events[0]["animationCallbackClipResolutions"][0]
        self.assertEqual(row["resolutionStatus"], "exactEnemyTableInstance")
        self.assertEqual(events[0]["animationCallbackOwnershipStatus"], "exactEnemyTableInstance")
        self.assertEqual(row["enemyTemplateIds"], ["eny_0042_wgthorns"])

    def test_animation_callback_exact_enemy_template_is_not_instance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root, template_only=True)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "enemy_template_hit",
                "contexts": [{
                    "kind": "enemyAnimation",
                    "ownerId": "eny_0050_silent",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_enemy_silent_attack01"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
        self.assertEqual(
            events[0]["animationCallbackClipResolutions"][0]["resolutionStatus"],
            "exactEnemyTemplate",
        )

    def test_animation_callback_unique_token_is_reported_without_forcing_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "ownerless_enemy_hit",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_monster_wgthorns_attack01"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
        row = events[0]["animationCallbackClipResolutions"][0]
        self.assertEqual(row["resolutionStatus"], "uniqueToken")
        self.assertEqual(events[0]["animationCallbackOwnerIds"], [])

    def test_animation_callback_ambiguous_enemy_token_stays_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root, ambiguous=True)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "ambiguous_enemy_hit",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_monster_wgthorns_attack01"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
        self.assertEqual(
            events[0]["animationCallbackClipResolutions"][0]["resolutionStatus"],
            "ambiguous",
        )
        self.assertEqual(events[0]["animationCallbackOwnershipStatus"], "ambiguous")

    def test_animation_callback_shared_event_remains_shared(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root, ambiguous=True)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "shared_enemy_foley",
                "contexts": [
                    {
                        "kind": "enemyAnimation",
                        "ownerId": "eny_0042_wgthorns",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_monster_wgthorns_attack01"],
                    },
                    {
                        "kind": "enemyAnimation",
                        "ownerId": "eny_0043_wgthorns",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_monster_wgthorns_attack01"],
                    },
                ],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
        self.assertEqual(events[0]["animationCallbackOwnershipStatus"], "shared")
        self.assertEqual(
            events[0]["animationCallbackOwnerIds"],
            ["eny_0042_wgthorns", "eny_0043_wgthorns"],
        )

    def test_animation_callback_unknown_clip_stays_unresolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "unknown_animation",
                "contexts": [{
                    "kind": "enemyAnimation",
                    "ownerId": "eny_0042_wgthorns",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_enemy_unknownunit_attack01"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )
        self.assertEqual(
            events[0]["animationCallbackClipResolutions"][0]["resolutionStatus"],
            "unresolved",
        )

    def test_malformed_persistent_enemy_table_fails_closed_over_streaming(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            persistent = root / "structured/Persistent/Table/EnemyTable.json"
            persistent.parent.mkdir(parents=True, exist_ok=True)
            persistent.write_text("{malformed", encoding="utf-8")

            catalog = media_ownership.collect_animation_entity_catalog(root)

        self.assertEqual(catalog["enemyInstanceIds"], [])
        self.assertEqual(
            catalog["malformedSources"]["EnemyTable"],
            ["structured/Persistent/Table/EnemyTable.json"],
        )
        self.assertEqual(
            catalog["tableStatuses"]["EnemyTable"],
            "malformedPersistentOverlay",
        )
        self.assertEqual(catalog["status"], "animationEntityCatalogMalformed")

    def test_animation_callback_candidate_ids_do_not_leak_into_resolved_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "ownerless_candidate_only",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_monster_wgthorns_attack01"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        event = events[0]
        resolution = event["animationCallbackClipResolutions"][0]
        self.assertEqual(event["animationCallbackEntityIds"], [])
        self.assertTrue(event["animationCallbackCandidateEntityIds"])
        self.assertEqual(
            set(resolution["candidateEntityIds"]),
            set(event["animationCallbackCandidateEntityIds"]),
        )
        self.assertEqual(resolution["resolvedEntityIds"], [])
        self.assertEqual(event["animationCallbackOwnershipStatus"], "candidateOnly")

    def test_unsupported_callback_owner_does_not_make_event_shared(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "valid_plus_invalid_callback_owner",
                "contexts": [
                    {
                        "kind": "enemyAnimation",
                        "ownerId": "eny_0042_wgthorns",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_monster_wgthorns_attack01"],
                    },
                    {
                        "kind": "animationCallbackOwnerUnresolved",
                        "ownerId": "eny_invalid_callback_owner",
                        "animationFunctions": ["PostAudioEvent"],
                        "animationClips": ["A_monster_wgthorns_attack01"],
                    },
                ],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        event = events[0]
        self.assertEqual(
            event["animationCallbackOwnerIds"],
            ["eny_0042_wgthorns"],
        )
        self.assertEqual(
            event["animationCallbackOwnershipStatus"],
            "resolved",
        )
        self.assertNotEqual(event["animationCallbackOwnershipStatus"], "shared")

    def test_ownerless_unique_token_has_candidate_only_ownership_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_animation_tables(root, template_only=True)
            catalog = media_ownership.collect_animation_entity_catalog(root)
            events = [{
                "id": "ownerless_unique_status",
                "contexts": [{
                    "kind": "animationCallbackOwnerUnresolved",
                    "animationFunctions": ["PostAudioEvent"],
                    "animationClips": ["A_monster_silent_attack01"],
                }],
            }]
            media_ownership.annotate_event_animation_callback_links(
                events, entity_catalog=catalog
            )

        event = events[0]
        self.assertEqual(event["animationCallbackTokenResolutionStatus"], "uniqueToken")
        self.assertEqual(event["animationCallbackOwnershipStatus"], "candidateOnly")
        self.assertEqual(event["animationCallbackEntityIds"], [])

    def test_event_summary_keeps_callback_aggregate_fields_without_clip_detail(self):
        summary = event_summary.event_summary_row(
            {
                "id": "ownerless_unique_status",
                "category": "sfx",
                "contexts": [],
                "animationCallbackOwnershipStatus": "candidateOnly",
                "animationCallbackTokenResolutionStatus": "uniqueToken",
                "animationCallbackResolutionStatuses": ["uniqueToken"],
                "animationCallbackResolvedEntityIds": ["eny_0050_silent"],
                "animationCallbackCandidateEntityIds": ["eny_0050_silent"],
                "animationCallbackNpcOwnerIds": ["si"],
                "animationCallbackNpcOwnerTemplates": ["npc_chr_0036_jsspsi"],
                "animationCallbackNpcActorTokens": ["jsspsi"],
                "animationCallbackClipResolutions": [{
                    "clip": "A_monster_silent_attack01",
                    "candidateEntityIds": ["eny_0050_silent"],
                }],
                "animationCallbackOccurrences": [{"occurrence": 0}],
            },
            "events_detail.json",
        )

        self.assertEqual(summary["animationCallbackOwnershipStatus"], "candidateOnly")
        self.assertEqual(summary["animationCallbackTokenResolutionStatus"], "uniqueToken")
        self.assertEqual(summary["animationCallbackResolutionStatuses"], ["uniqueToken"])
        self.assertEqual(
            summary["animationCallbackResolvedEntityIds"],
            ["eny_0050_silent"],
        )
        self.assertEqual(
            summary["animationCallbackCandidateEntityIds"],
            ["eny_0050_silent"],
        )
        self.assertEqual(summary["animationCallbackNpcOwnerIds"], ["si"])
        self.assertEqual(
            summary["animationCallbackNpcOwnerTemplates"],
            ["npc_chr_0036_jsspsi"],
        )
        self.assertNotIn("animationCallbackClipResolutions", summary)
        self.assertNotIn("animationCallbackOccurrences", summary)

    def test_event_summary_promotes_exact_npc_animation_display_context(self):
        summary = event_summary.event_summary_row(
            {
                "id": "jsspsi_spell_start",
                "category": "sfx",
                "contexts": [{"kind": "animationCallbackOwnerUnresolved"}],
                "animationCallbackOwnershipStatus": "exactNpcTableToken",
                "animationCallbackNpcOwnerIds": ["si"],
            },
            "events_detail.json",
        )

        self.assertIn("npcAnimation", summary["contextKinds"])
        self.assertIn("animationCallbackNpcOwner", summary["contextKinds"])
        self.assertNotIn("animationCallbackOwnerUnresolved", summary["contextKinds"])
        self.assertEqual(summary["contextGroups"], ["animation"])
        self.assertIn("npcAnimation", summary["contextSearch"])
        self.assertIn("animationCallbackNpcOwner", summary["contextSearch"])
        self.assertNotIn("animationCallbackOwnerUnresolved", summary["contextSearch"])

    def test_event_summary_keeps_mixed_npc_occurrence_unresolved_display_context(self):
        summary = event_summary.event_summary_row(
            {
                "id": "au_dlg_foley_state_spell_start",
                "category": "sfx",
                "contexts": [{"kind": "animationCallbackOwnerUnresolved"}],
                "animationCallbackOwnershipStatus": "unresolved",
                "animationCallbackNpcOwnerIds": [],
                "animationCallbackNpcOccurrenceOwnerIds": ["si"],
            },
            "events_detail.json",
        )

        self.assertIn("animationCallbackOwnerUnresolved", summary["contextKinds"])
        self.assertNotIn("npcAnimation", summary["contextKinds"])
        self.assertNotIn("animationCallbackNpcOwner", summary["contextKinds"])
        self.assertIn("animationCallbackOwnerUnresolved", summary["contextSearch"])

    def test_event_summary_accepts_exact_npc_owner_agreement_contract(self):
        summary = event_summary.event_summary_row(
            {
                "id": "jsspsi_two_exact_callbacks",
                "contexts": [{"kind": "animationCallbackOwnerUnresolved"}],
                "animationCallbackOwnershipStatus": "exactNpcOwnerAgreement",
                "animationCallbackResolutionStatuses": [
                    "exactNpcTableToken",
                    "exactNpcInfoAndTemplateGroup",
                ],
                "animationCallbackNpcOwnerIds": ["si"],
            },
            "events_detail.json",
        )

        self.assertIn("npcAnimation", summary["contextKinds"])
        self.assertIn("animationCallbackNpcOwner", summary["contextKinds"])
        self.assertNotIn("animationCallbackOwnerUnresolved", summary["contextKinds"])


if __name__ == "__main__":
    unittest.main()
