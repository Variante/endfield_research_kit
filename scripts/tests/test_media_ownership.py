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
        self.assertEqual(events[3]["characterAudioOwnerIds"], ["chr_0032_lizhiyan"])
        self.assertEqual(
            events[3]["characterAudioIdentityStatus"],
            "uniqueCharacterTableTokenPrefix",
        )
        self.assertNotIn("characterAudioOwnerIds", events[4])
        self.assertEqual(counts["eventsWithCharacterAudioIdentity"], 4)

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
        self.assertNotIn("animationCallbackClipResolutions", summary)
        self.assertNotIn("animationCallbackOccurrences", summary)


if __name__ == "__main__":
    unittest.main()
