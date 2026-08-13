import argparse
import base64
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


def sound_source_data(
    media_id: int,
    parent_id: int = 0,
    *,
    plugin_id: int = 0x00040001,
    stream_type: int = 2,
    in_memory_size: int = 0,
    source_bits: int = 0,
    plugin_parameters: bytes = b"",
) -> bytes:
    source = pack(
        "<IBIIB", plugin_id, stream_type, media_id,
        in_memory_size, source_bits,
    )
    if plugin_id & 0x0F == 2:
        source += pack("<I", len(plugin_parameters)) + plugin_parameters
    return source + bytes(4) + pack("<II", 0, parent_id)


class AudioCategoryTests(unittest.TestCase):
    def test_hirc_container_parent_decodes_variable_fx_prefix(self) -> None:
        parent_id = 386813193
        # NodeBase: override FX, one authored effect row, metadata header,
        # override-bus id, then DirectParentID.
        data = (
            bytes([1, 1, 0, 4])
            + pack("<I", 0)
            + bytes([0, 0, 0])
            + pack("<II", 0, parent_id)
            + bytes(32)
        )

        self.assertEqual(build_audio.hirc_object_parent_id(9, data), parent_id)

    def test_variable_fx_parent_restores_exact_sequence_layer_event_graph(self) -> None:
        event_id = 0x8A88723C
        container_id = 386813193
        variable_layer_id = 144808260
        ordinary_layer_id = 337304808
        media_by_sound = {
            369109803: (205675749, variable_layer_id),
            723059349: (748608357, variable_layer_id),
            414986928: (475840163, ordinary_layer_id),
            716252337: (594611880, ordinary_layer_id),
        }
        objects = {
            event_id: {"type": 4, "data": bytes.fromhex("01102ef12d")},
            770780688: {"type": 3, "data": bytes.fromhex("0304094d0e17000000043c72888a1e000000")},
            container_id: {"type": 5, "data": bytes.fromhex(
                "0000000000000000e553d01a0001080000c0c20000086d580507000000000000000000000000000000000001000000000000000001000000000000007a440000000000000000010000000112020000004499a108e8dc1a1402004499a10850c30000e8dc1a1450c30000"
            )},
            variable_layer_id: {"type": 9, "data": bytes.fromhex(
                "010100000000000004000000000000094d0e17000400020308000070c10000c041000074420000c0c20000086d580507000000000000000000000000000000000d010200000000000000020000002b2b00169502192b0000000000"
            )},
            ordinary_layer_id: {"type": 9, "data": bytes.fromhex(
                "0000000000000000094d0e170004000203080000b0c10000c041000018420000c0c20000086d580507000000000000000000000000000000000001000000000000000002000000b032bc18b124b12a0000000000"
            )},
        }
        for sound_id, (media_id, parent_id) in media_by_sound.items():
            objects[sound_id] = {
                "type": 2,
                "data": sound_source_data(media_id, parent_id),
            }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {row[0] for row in media_by_sound.values()}, bank_version=150
        )

        self.assertEqual(set(result["mediaIds"]), {205675749, 748608357, 475840163, 594611880})
        self.assertEqual(result["unresolvedNodes"], [])
        self.assertEqual(
            {(row["objectId"], row["edgeKind"]) for row in result["containerEvidence"]},
            {(container_id, "sequenceItem"), (variable_layer_id, "layerChild"), (ordinary_layer_id, "layerChild")},
        )

    def test_link_conversation_audio_marks_exact_story_line_purpose_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            conv_dir = Path(raw_root)
            conv_path = conv_dir / "dlg_fixture.json"
            conv_path.write_text(json.dumps({
                "lines": [{"id": "line_1", "audioId": "au_dlg_fixture"}],
            }), encoding="utf-8")
            entry = {"id": "au_dlg_fixture", "src": "/audio/fixture.flac"}

            stats = build_audio.link_conversation_audio(
                conv_dir, {"au_dlg_fixture": entry}
            )

            self.assertEqual(stats["lineAudioLinked"], 1)
            self.assertEqual(entry["storyLineBindingCount"], 1)
            self.assertEqual(entry["purposeKnowledgeStatus"], "exactStoryLineBinding")

    def test_numeric_audio_entries_recovers_occurrence_key_only_media(self) -> None:
        surviving = {
            "id": "1040066173",
            "storageRoot": "shared",
            "rel": "wwise/voice_events/1040066173.flac",
        }
        entries = build_audio.numeric_audio_entries_by_media_id({
            "1040066173@shared:wwise/voice_events/1040066173.flac": surviving,
            "955778167792087661": {
                "id": "955778167792087661",
                "storageRoot": "CN",
                "rel": "wwise/unknown/955778167792087661.flac",
            },
        })

        self.assertEqual(entries, {1040066173: surviving})

    def test_event_media_inventory_fingerprint_ignores_uint64_external_ids(self) -> None:
        base = {"1": {"id": "1", "storageRoot": "shared", "rel": "wwise/sfx/1.flac", "bytes": 3}}
        with_external = {**base, "external": {
            "id": "955778167792087661", "storageRoot": "CN",
            "rel": "wwise/unknown/955778167792087661.flac", "bytes": 5,
        }}
        self.assertEqual(
            build_audio.event_media_inventory_fingerprint(base),
            build_audio.event_media_inventory_fingerprint(with_external),
        )

    def test_audio_dialog_external_media_id_matches_game_path_hash(self) -> None:
        self.assertEqual(
            build_audio.audio_dialog_external_media_id(
                "v1d4/Narrating/HS_Part04/c35m3/au_dlg_c35m3_12_025.wem",
                "chinese",
            ),
            10012020101098562764,
        )

    def test_collect_hirc_decoded_sound_definitions_keeps_exact_orphan_object(self) -> None:
        objects = {
            10: {"type": 2, "data": sound_source_data(30151934, 20)},
            11: {"type": 2, "data": sound_source_data(999, 20)},
            20: {"type": 5, "data": b""},
        }

        rows = build_audio.collect_hirc_decoded_sound_definitions(
            objects,
            {30151934},
            bank_name="default_banks.pck",
            bank_id=7,
            bank_version=150,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["mediaId"], 30151934)
        self.assertEqual(rows[0]["soundObjectId"], 10)
        self.assertEqual(rows[0]["parentObjectId"], 20)
        self.assertEqual(rows[0]["parentObjectType"], 5)
        self.assertEqual(rows[0]["evidence"], "exactTypedWwiseSoundCodecMediaObject")

    def test_suppress_redundant_unknown_audio_occurrences_drops_identical_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            unknown_path = audio_root / "shared/wwise/unknown/1.flac"
            resolved_path = audio_root / "shared/wwise/sfx/1.flac"
            unknown_path.parent.mkdir(parents=True)
            resolved_path.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"same decoded media")
            resolved_path.write_bytes(b"same decoded media")
            generic = {
                "1": {
                    "id": "1", "storageRoot": "shared", "rel": "wwise/sfx/1.flac",
                    "bytes": resolved_path.stat().st_size, "audioCategory": "sfx",
                },
                "1@shared:wwise/unknown/1.flac": {
                    "id": "1", "storageRoot": "shared", "rel": "wwise/unknown/1.flac",
                    "bytes": unknown_path.stat().st_size, "audioCategory": "unknown",
                },
            }

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, {}, "CN"
            )

            self.assertEqual(stats["contentIdenticalDuplicateOccurrencesCompared"], 1)
            self.assertEqual(stats["contentIdenticalUnknownOccurrencesSuppressed"], 1)
            self.assertEqual(list(generic), ["1"])
            self.assertTrue(unknown_path.is_file())

    def test_suppress_redundant_unknown_audio_occurrences_preserves_different_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            unknown_path = audio_root / "shared/wwise/unknown/2.flac"
            resolved_path = audio_root / "shared/wwise/sfx/2.flac"
            unknown_path.parent.mkdir(parents=True)
            resolved_path.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"unknown collision")
            resolved_path.write_bytes(b"resolved collision")
            generic = {
                "2": {
                    "id": "2", "storageRoot": "shared", "rel": "wwise/sfx/2.flac",
                    "bytes": resolved_path.stat().st_size, "audioCategory": "sfx",
                },
                "2@shared:wwise/unknown/2.flac": {
                    "id": "2", "storageRoot": "shared", "rel": "wwise/unknown/2.flac",
                    "bytes": unknown_path.stat().st_size, "audioCategory": "unknown",
                },
            }

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, {}, "CN"
            )

            self.assertEqual(stats["contentIdenticalUnknownOccurrencesSuppressed"], 0)
            self.assertEqual(len(generic), 2)

    def test_suppress_redundant_unknown_audio_occurrences_preserves_cross_storage_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            shared_path = audio_root / "shared/wwise/sfx/3.flac"
            language_path = audio_root / "CN/wwise/unknown/3.flac"
            shared_path.parent.mkdir(parents=True)
            language_path.parent.mkdir(parents=True)
            shared_path.write_bytes(b"same id and bytes")
            language_path.write_bytes(b"same id and bytes")
            generic = {
                "3@shared": {
                    "id": "3", "storageRoot": "shared", "rel": "wwise/sfx/3.flac",
                    "bytes": shared_path.stat().st_size, "audioCategory": "sfx",
                },
                "3@CN": {
                    "id": "3", "storageRoot": "CN", "rel": "wwise/unknown/3.flac",
                    "bytes": language_path.stat().st_size, "audioCategory": "unknown",
                },
            }

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, {}, "CN"
            )

            self.assertEqual(stats["contentIdenticalDuplicateOccurrencesCompared"], 0)
            self.assertEqual(stats["contentIdenticalUnknownOccurrencesSuppressed"], 0)
            self.assertEqual(len(generic), 2)

    def test_suppress_redundant_audio_dialog_external_path_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            dialog_path = "v1d4/Narrating/HS_Part04/c35m3/au_dlg_fixture.wem"
            external_id = build_audio.audio_dialog_external_media_id(dialog_path, "chinese")
            unknown_path = audio_root / f"CN/wwise/unknown/{external_id}.flac"
            dialog_file = audio_root / "CN/voice/story/hongshan/au_dlg_fixture.flac"
            unknown_path.parent.mkdir(parents=True)
            dialog_file.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"same external voice bytes")
            dialog_file.write_bytes(b"same external voice bytes")
            generic = {str(external_id): {
                "id": str(external_id),
                "storageRoot": "CN",
                "rel": f"wwise/unknown/{external_id}.flac",
                "bytes": unknown_path.stat().st_size,
                "audioCategory": "unknown",
            }}
            dialog = {"au_dlg_fixture": {
                "id": "au_dlg_fixture",
                "storageRoot": "CN",
                "rel": "voice/story/hongshan/au_dlg_fixture.flac",
                "bytes": dialog_file.stat().st_size,
                "audioDialogPath": dialog_path,
            }}

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, dialog, "CN"
            )

            self.assertEqual(stats["audioDialogExternalCopiesCompared"], 1)
            self.assertEqual(stats["audioDialogExternalCopiesSuppressed"], 1)
            self.assertEqual(generic, {})
            self.assertTrue(unknown_path.is_file())

    def test_suppress_redundant_audio_dialog_external_copy_requires_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            dialog_path = "v1d4/Narrating/HS_Part04/c35m3/au_dlg_fixture.wem"
            external_id = build_audio.audio_dialog_external_media_id(dialog_path, "chinese")
            unknown_path = audio_root / f"CN/wwise/unknown/{external_id}.flac"
            dialog_file = audio_root / "CN/voice/story/hongshan/au_dlg_fixture.flac"
            unknown_path.parent.mkdir(parents=True)
            dialog_file.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"external bytes A")
            dialog_file.write_bytes(b"external bytes B")
            generic = {str(external_id): {
                "id": str(external_id), "storageRoot": "CN",
                "rel": f"wwise/unknown/{external_id}.flac", "bytes": 16,
                "audioCategory": "unknown", "sourceBank": "external",
            }}
            dialog = {"au_dlg_fixture": {
                "id": "au_dlg_fixture", "storageRoot": "CN",
                "rel": "voice/story/hongshan/au_dlg_fixture.flac", "bytes": 16,
                "audioDialogPath": dialog_path,
            }}

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, dialog, "CN"
            )

            self.assertEqual(stats["audioDialogExternalCopiesCompared"], 1)
            self.assertEqual(stats["audioDialogExternalCopiesSuppressed"], 0)
            self.assertEqual(len(generic), 1)

    def test_orphan_external_media_identity_recovers_name_without_trigger(self) -> None:
        external_id = 955778167792087661
        generic = {str(external_id): {
            "id": str(external_id),
            "storageRoot": "CN",
            "rel": f"wwise/unknown/{external_id}.flac",
            "bytes": 1,
            "audioCategory": "unknown",
            "sourceBank": "external",
        }}

        stats = build_audio.suppress_redundant_unknown_audio_occurrences(
            Path("unused"), generic, {}, "CN"
        )

        self.assertEqual(stats["recoveredOrphanExternalMediaIdentities"], 1)
        self.assertEqual(generic[str(external_id)]["externalAuthoredAudioId"], "au_voice_c35m3_3_001")
        self.assertEqual(
            generic[str(external_id)]["identityOnlyPlaybackPlacementStatus"],
            "identityOnlyNoCurrentAudioDialogOrTrigger",
        )
        self.assertEqual(generic[str(external_id)]["audioCategory"], "story_voice")

    def test_audio_dialog_path_recovers_only_exact_current_wwise_event_alias(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            first = root / "StreamingAssets/AudioDialog.json"
            second = root / "Persistent/AudioDialog.json"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            exact_name = "eny_fixture_combat_taunt_sv"
            exact_hash = build_audio.audio_hash_generator_compute(exact_name)
            signed_hash = exact_hash if exact_hash < (1 << 31) else exact_hash - (1 << 32)
            payload = {
                str(signed_hash): {
                    "path": exact_name,
                    "codec": 4,
                    "speakerChannel": "eny_fixture",
                    "voType": 2,
                },
                "123": {"path": "external_only_voice"},
            }
            first.write_text(json.dumps(payload), encoding="utf-8")
            second.write_text(json.dumps(payload), encoding="utf-8")

            rows = build_audio.collect_audio_dialog_wwise_event_aliases(
                [first, second],
                [{"eventHash": exact_hash}, {"eventHash": 123}],
            )

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], exact_name)
            self.assertEqual(rows[0]["voiceId"], signed_hash)
            self.assertEqual(rows[0]["eventHash"], exact_hash)
            self.assertEqual(len(rows[0]["sources"]), 2)
            self.assertEqual(
                rows[0]["evidence"],
                "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
            )

    def test_voice_table_event_aliases_accept_only_typed_current_wwise_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            names = {
                "defaultWwiseEvent": "vo_fixture_default",
                "narratingWwiseEvent": "vo_fixture_narrating",
                "radioWwiseEvent": "vo_fixture_radio",
                "overrideWwiseEvent": "vo_fixture_override",
                "eventTemplate": "vo_fixture_response_{0}",
            }
            payloads = {
                "AudioDialogConfigs.json": {"config": {
                    "defaultWwiseEvent": names["defaultWwiseEvent"],
                    "unrelated": "vo_fixture_unrelated",
                }},
                "AudioDialogChannel.json": {"channel": {
                    "narratingWwiseEvent": names["narratingWwiseEvent"],
                    "radioWwiseEvent": names["radioWwiseEvent"],
                }},
                "AudioDialog.json": {"voice": {
                    "overrideWwiseEvent": names["overrideWwiseEvent"],
                }},
                "ResponsiveTriggers.json": {"trigger": {
                    "eventTemplate": names["eventTemplate"],
                    "nested": {"eventTemplate": "not_in_current_inventory"},
                }},
            }
            for source in ("StreamingAssets", "Persistent"):
                table_root = export_root / "structured" / source / "Table"
                table_root.mkdir(parents=True)
                for filename, payload in payloads.items():
                    (table_root / filename).write_text(json.dumps(payload), encoding="utf-8")
            event_names = list(names.values()) + ["vo_fixture_unrelated"]
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in event_names]

            rows = build_audio.collect_voice_table_wwise_event_aliases(export_root, inventory)

            self.assertEqual({row["name"] for row in rows}, set(names.values()))
            narrating = next(row for row in rows if row["name"] == names["narratingWwiseEvent"])
            self.assertEqual(narrating["usages"][0]["routeKind"], "narratingChannelEvent")
            self.assertEqual(narrating["usages"][0]["occurrenceCount"], 1)
            self.assertEqual(len(narrating["usages"][0]["sources"]), 2)
            self.assertEqual(
                narrating["evidence"],
                "typedVoiceTableEventFieldHashEqualsCurrentWwiseEventId",
            )

    def test_voice_table_event_alias_conflicts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "AudioDialogChannel.json").write_text(json.dumps({
                "channel": {
                    "narratingWwiseEvent": "vo_fixture_a",
                    "radioWwiseEvent": "vo_fixture_b",
                }
            }), encoding="utf-8")
            with mock.patch.object(build_audio, "audio_hash_generator_compute", return_value=123):
                rows = build_audio.collect_voice_table_wwise_event_aliases(
                    export_root,
                    [{"eventHash": 123}],
                )
            self.assertEqual(rows, [])

    def test_typed_ui_table_aliases_require_whitelisted_consumer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            accepted = {
                "audioOnOpen": "Au_UI_Menu_Test_Open",
                "videoAudioKey": "Au_UI_Menu_Test_Video",
            }
            (table_root / "ActivityStaminaRefundBgStateTable.json").write_text(json.dumps({
                "activity": {
                    "audioOnOpen": accepted["audioOnOpen"],
                    "unrelated": "Au_UI_Menu_Unrelated",
                }
            }), encoding="utf-8")
            (table_root / "GachaCharPoolTable.json").write_text(json.dumps({
                "pool": {"videoAudioKey": accepted["videoAudioKey"]}
            }), encoding="utf-8")
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in (
                *accepted.values(), "Au_UI_Menu_Unrelated",
            )]

            rows = build_audio.collect_typed_ui_table_wwise_event_aliases(export_root, inventory)

            self.assertEqual({row["name"] for row in rows}, set(accepted.values()))
            video = next(row for row in rows if row["name"] == accepted["videoAudioKey"])
            self.assertEqual(video["usages"][0]["routeKind"], "uiVideoAudioEvent")
            self.assertIn("VideoPlayer.PlayAudio", video["usages"][0]["runtimeRoute"])
            self.assertTrue(video["usages"][0]["consumerEvidence"])
            self.assertEqual(
                video["evidence"],
                "typedTableGetterAndLuaAudioConsumerHashEqualsCurrentWwiseEventId",
            )

    def test_sns_voice_aliases_require_voice_content_and_first_parameter(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            accepted = "Au_UI_Event_SNS_Fixture_Voice"
            rejected = "Au_UI_Event_SNS_Fixture_Image"
            (table_root / "SNSDialogTable.json").write_text(json.dumps({
                "dialog_fixture": {
                    "dialogId": "dialog_fixture",
                    "dialogContentData": {
                        "1": {"contentId": 1, "contentType": 5, "contentParam": [accepted, "4"], "speaker": "fixture"},
                        "2": {"contentId": 2, "contentType": 2, "contentParam": [rejected]},
                    },
                },
            }), encoding="utf-8")
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in (accepted, rejected)]

            rows = build_audio.collect_sns_voice_wwise_event_aliases(export_root, inventory)

            self.assertEqual([row["name"] for row in rows], [accepted])
            usage = rows[0]["usages"][0]
            self.assertEqual(usage["contentTypeName"], "Voice")
            self.assertEqual(usage["contentParamIndex"], 0)
            self.assertEqual(usage["durationSeconds"], "4")

    def test_skill_id_dictionary_alias_is_identity_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            accepted = "eny_fixture_skill_audio_identity"
            rejected = "eny_fixture_missing_skill_data"
            for source_root in ("StreamingAssets", "Persistent"):
                table_root = export_root / "structured" / source_root / "Table"
                table_root.mkdir(parents=True)
                (table_root / "NumIdStrTable.json").write_text(json.dumps({
                    "skill_id": {"dic": {"7": accepted, "8": rejected}},
                }), encoding="utf-8")
                skill_root = export_root / "structured" / source_root / "Data/Json/SkillData"
                skill_root.mkdir(parents=True)
                (skill_root / f"{accepted}.json").write_bytes(b"fixture-skill-data")
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in (accepted, rejected)]

            rows = build_audio.collect_skill_id_dictionary_wwise_event_aliases(export_root, inventory)

            self.assertEqual([row["name"] for row in rows], [accepted])
            self.assertEqual(rows[0]["dictionaryKind"], "skill_id")
            self.assertEqual(rows[0]["numericSkillIds"], ["7"])
            self.assertEqual(rows[0]["playbackPlacementStatus"], "identityOnlyNoAudioConsumer")

    def test_lua_audio_references_separate_events_rtpc_cues_and_literals(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            path = root / "Data/LuaScripts/Test.lua"
            path.parent.mkdir(parents=True)
            path.write_text(
                '\n'.join((
                    'AudioAdapter.PostEvent(flag and "Au_UI_Test_A" or "au_ui_test_b")',
                    'AudioAdapter.SetRtpc("au_rtpc_test", value)',
                    'AudioManager.PostAudioCue("au_cue_test")',
                    'local fallback = "au_ui_indirect"',
                )),
                encoding="utf-8",
            )

            rows = build_audio.collect_lua_audio_references(root)

            self.assertEqual(len(rows), 5)
            self.assertEqual(
                {row["kind"] for row in rows},
                {"luaPostEvent", "luaRtpcParameter", "luaAudioCue", "luaAudioLiteral"},
            )
            post_names = {row["name"] for row in rows if row["kind"] == "luaPostEvent"}
            self.assertEqual(post_names, {"au_ui_test_a", "au_ui_test_b"})
            for row in rows:
                self.assertEqual(row["hash"], build_audio.fnv1_32(row["name"]))

    def test_lua_audio_references_keep_source_root_and_selected_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            selected = root / "Data/Selected.lua"
            skipped = root / "Data/Skipped.lua"
            selected.parent.mkdir(parents=True)
            selected.write_text('AudioAdapter.PostEvent("au_ui_selected")', encoding="utf-8")
            skipped.write_text('AudioAdapter.PostEvent("au_ui_skipped")', encoding="utf-8")

            rows = build_audio.collect_lua_audio_references(
                root,
                "Persistent",
                {"Data/Selected.lua"},
            )

            self.assertEqual([row["name"] for row in rows], ["au_ui_selected"])
            self.assertEqual(
                rows[0]["source"],
                "structured/Persistent/Lua/Data/Selected.lua",
            )

    def test_event_bank_filter_includes_named_banks_and_hotfix_pcks(self) -> None:
        import re

        pattern = re.compile(build_audio.EVENT_BANK_FILE_REGEX, re.IGNORECASE)
        self.assertTrue(pattern.search("Data/Audio/PCK/Windows/Main/default_banks.pck"))
        self.assertTrue(pattern.search("Data/Audio/PCK/Windows/Hotfix/hotfix_main.pck"))
        self.assertFalse(pattern.search("Data/Audio/PCK/Windows/Main/default_media.pck"))

    def test_event_bank_stream_enumerates_streaming_and_persistent_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            cli = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            cli.write_bytes(b"")
            streaming.mkdir()
            persistent.mkdir()
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                source = Path(command[command.index("--streaming-assets") + 1]).name
                data = b"streaming-bank" if source == "StreamingAssets" else b"persistent-hotfix"
                row = {
                    "blockType": "audio" if source == "StreamingAssets" else "hotfix-audio",
                    "fileName": "default_banks.pck" if source == "StreamingAssets" else "hotfix_main.pck",
                    "dataBase64": base64.b64encode(data).decode("ascii"),
                }
                return mock.Mock(stdout=json.dumps(row), stderr="")

            args = argparse.Namespace(
                audio_dumper=cli,
                streaming_assets=streaming,
                fallback_assets=persistent,
            )
            with mock.patch.object(build_audio.subprocess, "run", side_effect=run):
                payloads = build_audio.event_bank_payloads_from_vfs(args)

            self.assertEqual(len(calls), 2)
            self.assertEqual({Path(call[call.index("--streaming-assets") + 1]).name for call in calls}, {"StreamingAssets", "Persistent"})
            self.assertEqual({Path(name).name for name, _ in payloads}, {"default_banks.pck", "hotfix_main.pck"})

    def test_current_interactive_audio_union_tag_and_complete_rows(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        def string(value: str) -> bytes:
            raw = value.encode("utf-8")
            return pack("<I", len(raw)) + raw

        body = b"".join([
            pack("<I", 0),
            bytes([13]),
            pack("<I", 1),
            pack("<iI", 13, 1),
            string("au_int_fixture_break"),
            pack("<I", 1),
            bytes([3]),
            string("au_int_fixture_open"),
            string("panel_open"),
            string("Open panel"),
            bytes([1] + [0] * 10),
        ])

        self.assertEqual(memorypack_interactive.INTERACTIVE_AUDIO_COMPONENT_TAG, 0x005D)
        self.assertEqual(
            memorypack_interactive.BASE_COMPONENT_UNION_TAGS[0x005D],
            "Core_InteractiveAudioData",
        )
        decoded, end = memorypack_interactive.parse_interactive_audio_component(body, 0, 2)
        self.assertEqual(end, len(body))
        self.assertEqual(decoded["audioRows"][0]["stateName"], "Destroy")
        self.assertEqual(decoded["audioRows"][0]["events"], ["au_int_fixture_break"])
        self.assertEqual(decoded["customRows"][0]["name"], "panel_open")

    def test_current_interactive_model_union_tag_is_0x0126(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        self.assertEqual(
            memorypack_interactive.BASE_COMPONENT_UNION_TAGS[0x0126],
            "View_InteractiveModelComponentData",
        )

    def test_current_interactive_trigger_zone_audio_property_map_is_exact(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        def string(value: str) -> bytes:
            raw = value.encode("utf-8")
            return pack("<I", len(raw)) + raw

        event_id = "au_int_fixture_start"
        property_map = b"".join((
            pack("<I", 1),
            bytes((2,)),
            string("audio_key_start"),
            bytes((2,)),
            pack("<iI", 7, 1),
            bytes((2,)),
            pack("<q", 0),
            string(event_id),
        ))
        body = b"".join((
            pack("<I", 0xFFFFFFFF),
            pack("<I", 1),
            bytes((20,)),
            bytes(60),
            property_map,
            bytes((0, 0)),
        ))

        decoded, end = memorypack_interactive.parse_interactive_trigger_zone_audio_property_component(
            body,
            0,
            3,
        )

        self.assertEqual(end, len(body) - 2)
        self.assertEqual(decoded["tag"], "0x00f5")
        self.assertEqual(decoded["type"], "Core_TriggerZoneComponentForIntData")
        self.assertEqual(decoded["audioPropertyRows"], [{
            "key": "audio_key_start",
            "events": [event_id],
            "valueType": 7,
            "identityKind": "wwiseEvent",
        }])
        self.assertEqual(decoded["runtimePropertyConsumerStatus"], "unresolved")
        self.assertEqual(decoded["runtimeEventPostingStatus"], "notObserved")

        found = memorypack_interactive.find_interactive_audio_property_maps(body)
        self.assertEqual(found[0]["audioPropertyRows"][0]["events"], [event_id])
        self.assertEqual(found[0]["componentResolutionStatus"], "containingComponentUnresolved")

    def test_interactive_template_config_audio_property_has_exact_field_boundary(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        def string(value: str) -> bytes:
            raw = value.encode("utf-8")
            return pack("<I", len(raw)) + raw

        event_id = "au_int_fixture_escape"
        config_map = b"".join((
            pack("<I", 2),
            bytes((2,)), string("audio_escape"),
            bytes((2,)), pack("<iI", 7, 1), bytes((2,)), pack("<q", 0), string(event_id),
            bytes((2,)), string("label"),
            bytes((2,)), pack("<iI", 28, 1), bytes((2,)), pack("<q", 0), string("lang_fixture"),
        ))
        tail = b"".join((
            pack("<ff", 0.0, 0.0), bytes((0,)), pack("<f", 1.0), bytes((0,)),
            pack("<I", 0), pack("<I", 0), pack("<i", 0), config_map,
        ))

        decoded, end = memorypack_interactive.parse_interactive_template_config_properties(
            tail, 0
        )

        self.assertEqual(end, len(tail))
        self.assertEqual(decoded["configPropertyCount"], 2)
        self.assertEqual(decoded["audioPropertyRows"], [{
            "key": "audio_escape",
            "events": [event_id],
            "valueType": 7,
            "identityKind": "wwiseEvent",
        }])
        self.assertEqual(decoded["configPropertiesOffset"], "0x1a")

    def test_current_play_sound_union_tag_matches_binary_formatter_audit(self) -> None:
        from scripts.game_data.memorypack import buff as memorypack_buff

        self.assertEqual(memorypack_buff.BUFF_PLAY_SOUND_ACTION_TAG, 0x010D)
        self.assertEqual(
            memorypack_buff.BUFF_ABILITY_ACTION_TAG_NAMES[0x010D],
            "Core_PlaySoundAction_PlaySoundActionData",
        )
        self.assertEqual(memorypack_buff.BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS[0x010D], 22)

    def test_play_sound_target_settings_uses_typed_memorypack_reader_when_exact(self) -> None:
        from scripts.game_data.memorypack import buff as memorypack_buff

        # Real CN BuffData PlaySoundActionData payloads: the 67-byte default
        # TargetSettings and the 79-byte smart_target variant.  The latter
        # proves the variable string slot and exact nested SelectorData end.
        base = b"".join((
            bytes((13, 8, 1, 0)), pack("<i", 0), bytes((0, 0xFF)), pack("<i", 0),
            bytes((0xFF,)), pack("<i", 0),
            pack("<I", 0), bytes((0,)), pack("<i", 0), bytes((0,)),
            pack("<I", 0),
            bytes((3, 0xFF)), pack("<II", 0, 0),
            pack("<iiii", 0, 1, 0, 0), pack("<I", 0), pack("<i", 4),
        ))
        self.assertEqual(len(base), 67)
        raw = base[:59] + pack("<I", 12) + b"smart_target" + base[63:]
        decoded, end = memorypack_buff.read_buff_target_settings_full_or_partial(
            raw, 0, len(raw), "fixture.targetSettings"
        )

        self.assertEqual(end, len(raw))
        self.assertEqual(decoded["status"], "exact")
        self.assertEqual(decoded["semanticStatus"], "exact-target-settings-selector-data")
        self.assertEqual(decoded["targetGroupKey"], "smart_target")
        self.assertEqual(decoded["targetSource"], 4)
        self.assertEqual(decoded["selectorOwner"], 1)
        self.assertEqual(decoded["selectorData"], {
            "finderData": None,
            "postProcessorData": [],
            "validatorData": [],
        })

    def test_play_sound_target_settings_rejects_unknown_tail_fail_closed(self) -> None:
        from scripts.game_data.memorypack import buff as memorypack_buff

        raw = bytearray(b"".join((
            bytes((13, 8, 1, 0)), pack("<i", 0), bytes((0, 0xFF)), pack("<i", 0),
            bytes((0xFF,)), pack("<i", 0),
            pack("<I", 0), bytes((0,)), pack("<i", 0), bytes((0,)),
            pack("<I", 0),
            bytes((3, 0xFF)), pack("<II", 0, 0),
            pack("<iiii", 0, 1, 0, 0), pack("<I", 0), pack("<i", 4),
        )))
        self.assertEqual(len(raw), 67)
        # Keep the byte layout valid but use an unrecognized candidate tail.
        raw[-4:] = (99).to_bytes(4, "little")
        with self.assertRaises(ValueError):
            memorypack_buff.read_buff_target_settings_full_or_partial(
                bytes(raw), 0, len(raw), "fixture.targetSettings"
            )

    def test_collects_and_merges_decoded_buff_play_sound_actions(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            sources = [
                "structured/StreamingAssets/Data/Json/BuffData/buff_timed.json",
                "structured/Persistent/Data/Json/BuffData/buff_timed.json",
            ]
            for source in sources:
                path = export_root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            decoded = [(
                {
                    "index": 2,
                    "startFrame": 17,
                    "endFrame": 34,
                },
                {
                    "onlyExecuteWhenSourceIsGuard": False,
                    "onlyExecuteWhenSourceIsMainChar": True,
                },
                {
                    "soundEvent": "au_test_timed",
                    "prefix": {"isEnable": True, "serverActionIndex": 9},
                    "stopOnEnd": True,
                    "stopFadeDurationMs": 300,
                    "targetSettingsEnvelopePartial": {
                        "semanticStatus": "partial-target-settings-envelope-opaque",
                        "shape": "string-slot",
                        "stringSlotValue": "smart_target",
                    },
                },
            )]
            result = build_audio.collect_buff_play_sound_actions(
                export_root,
                {"buff_timed": {"sources": set(sources)}},
                decoder=lambda *_args: decoded,
            )

            rows = result["byBuffEvent"]["buff_timed"]["au_test_timed"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["startFrame"], 17)
            self.assertEqual(rows[0]["endFrame"], 34)
            self.assertTrue(rows[0]["onlyExecuteWhenSourceIsMainChar"])
            self.assertTrue(rows[0]["stopOnEnd"])
            self.assertEqual(rows[0]["targetSelector"], "smart_target")
            self.assertEqual(rows[0]["sourcePaths"], sources[::-1])
            self.assertEqual(result["counts"]["buffPlaySoundActionOccurrences"], 1)

    def test_audio_cli_has_one_flac_output_contract(self) -> None:
        args = build_audio.parse_args([])
        for removed_option in (
            "format", "audio_format", "ffmpeg", "audio_conversion_jobs",
        ):
            self.assertFalse(hasattr(args, removed_option))
        self.assertEqual(build_audio.AUDIO_OUTPUT_FORMAT, "flac")
        for option, value in (
            ("--format", "wav"),
            ("--audio-format", "wem"),
            ("--ffmpeg", "ffmpeg.exe"),
            ("--fluffy", "fluffy.exe"),
            ("--audio-conversion-jobs", "4"),
        ):
            with self.subTest(option=option), mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                build_audio.parse_args([option, value])

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

    def test_v150_play_action_decodes_properties_ranges_and_exact_tail(self) -> None:
        data = b"".join([
            pack("<HI", 0x0403, 1234),
            bytes([0x01]),
            bytes([4, 0x39, 0x3A, 0x3B, 0x7F]),
            pack("<ii", 350, 500),
            pack("<f", 25.0),
            b"\x01\x02\x03\x04",
            bytes([2, 0x39, 0x3B]),
            pack("<ii", -25, 50),
            pack("<ff", 5.0, 10.0),
            bytes([0xA6]),
            pack("<II", 9876, 30),
        ])

        result = build_audio.hirc_v150_playback_action(data, 150)

        self.assertEqual(result["actionParserStatus"], "typedExactV150")
        self.assertEqual(result["targetFlagsRaw"], 1)
        self.assertTrue(result["targetIsBus"])
        self.assertEqual(
            [row["propertyName"] for row in result["properties"]],
            ["delayTime", "transitionTime", "probability", "property0x7f"],
        )
        self.assertEqual(result["properties"][0]["value"], 350)
        self.assertEqual(result["properties"][1]["value"], 500)
        self.assertAlmostEqual(result["properties"][2]["value"], 25.0)
        self.assertEqual(result["properties"][3]["encoding"], "rawUnion32")
        self.assertEqual(result["properties"][3]["rawHex"], "01020304")
        self.assertNotIn("value", result["properties"][3])
        self.assertEqual(result["delay"], {
            "serializationStatus": "explicitBaseAndRange",
            "baseValuesMs": [350],
            "modifierRangesMs": [{"minimum": -25, "maximum": 50}],
            "runtimeSelection": "boundedModifierUnresolved",
        })
        self.assertEqual(result["transition"]["baseValuesMs"], [500])
        self.assertEqual(result["probability"]["baseValuesPercent"], [25.0])
        self.assertEqual(
            result["probability"]["modifierRangesPercent"],
            [{"minimum": 5.0, "maximum": 10.0}],
        )
        self.assertEqual(result["probability"]["runtimeSelection"], "actionGateNotEvaluated")
        self.assertEqual(result["fade"], {
            "flagsRaw": 0xA6,
            "curveId": 6,
            "curveLabel": "Exp1",
            "bankId": 9876,
            "bankType": 30,
            "bankTypeLabel": "Event",
        })

    def test_v150_play_event_accepts_zero_tail_and_rejects_extra_bytes(self) -> None:
        data = b"".join([
            pack("<HI", 0x2103, 1234),
            bytes([0]),
            bytes([1, 0x39]),
            pack("<i", 100),
            bytes([0]),
        ])

        result = build_audio.hirc_v150_playback_action(data, 150)
        self.assertEqual(result["actionParserStatus"], "typedExactV150")
        self.assertEqual(result["delay"]["baseValuesMs"], [100])
        self.assertNotIn("fade", result)

        failed = build_audio.hirc_v150_playback_action(data + b"\x00", 150)
        self.assertEqual(failed["actionParserStatus"], "failedClosed")
        self.assertEqual(
            failed["actionParserFailure"]["reason"],
            "unexpectedPlayEventTrailingBytes",
        )
        self.assertNotIn("delay", failed)

    def test_v150_playback_action_failures_are_bounded_and_claim_no_timing(self) -> None:
        valid_empty_play = b"".join([
            pack("<HI", 0x0403, 1234),
            bytes([0, 0, 0, 4]),
            pack("<II", 123, 30),
        ])
        cases = {
            "unsupportedBankVersion": (valid_empty_play, 154),
            "truncatedActionHeader": (pack("<HI", 0x0403, 1234), 150),
            "truncatedScalarPropertyIds": (
                pack("<HI", 0x0403, 1234) + bytes([0, 2, 0x39]),
                150,
            ),
            "truncatedScalarPropertyValues": (
                pack("<HI", 0x0403, 1234) + bytes([0, 1, 0x39, 1, 2]),
                150,
            ),
            "truncatedRangePropertyValues": (
                pack("<HI", 0x0403, 1234)
                + bytes([0, 0, 1, 0x39])
                + pack("<i", 1),
                150,
            ),
            "truncatedPlayTail": (valid_empty_play[:-1], 150),
            "unexpectedPlayTrailingBytes": (valid_empty_play + b"\x00", 150),
        }
        for reason, (data, version) in cases.items():
            with self.subTest(reason=reason):
                result = build_audio.hirc_v150_playback_action(data, version)
                self.assertEqual(result["actionParserStatus"], "failedClosed")
                self.assertEqual(result["actionParserFailure"]["reason"], reason)
                self.assertGreaterEqual(result["actionParserFailure"]["remainingBytes"], 0)
                self.assertNotIn("properties", result)
                self.assertNotIn("delay", result)

    def test_action_dispatch_preserves_ordinals_and_classifies_timing_conservatively(self) -> None:
        def play(target_id: int, delay_ms: int | None = None) -> bytes:
            property_bundle = bytes([0])
            if delay_ms is not None:
                property_bundle = bytes([1, 0x39]) + pack("<i", delay_ms)
            return b"".join([
                pack("<HI", 0x0403, target_id),
                bytes([0]),
                property_bundle,
                bytes([0, 4]),
                pack("<II", 99, 30),
            ])

        sound = sound_source_data(777)
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": play(4)},
            3: {"type": 3, "data": play(4)},
            4: {"type": 2, "data": sound},
        }

        result = build_audio.traverse_hirc_event(1, objects, {777}, bank_version=150)
        self.assertEqual(result["mediaIds"], [777])
        self.assertEqual(
            [row["eventActionOrdinal"] for row in result["actionEvidence"]],
            [0, 1],
        )
        self.assertEqual(
            [row["dispatchEventId"] for row in result["actionEvidence"]],
            [1, 1],
        )
        self.assertEqual(
            result["actionDispatchEvidence"]["timingClass"],
            "coDispatchNoExplicitDelay",
        )
        self.assertEqual(result["actionDispatchEvidence"]["typedPlaybackActionCount"], 2)
        self.assertEqual(result["actionDispatchEvidence"]["failedPlaybackActionCount"], 0)
        self.assertTrue(result["actionDispatchEvidence"]["simultaneityCandidate"])

        objects[3] = {"type": 3, "data": play(4, 350)}
        staggered = build_audio.traverse_hirc_event(1, objects, {777}, bank_version=150)
        self.assertEqual(staggered["mediaIds"], [777])
        self.assertEqual(
            staggered["actionDispatchEvidence"]["timingClass"],
            "coDispatchWithAuthoredDelayDifference",
        )
        self.assertFalse(staggered["actionDispatchEvidence"]["simultaneityCandidate"])
        self.assertEqual(staggered["actionDispatchEvidence"]["explicitDelayActionCount"], 1)

    def test_failed_action_evidence_does_not_change_target_reachability(self) -> None:
        sound = sound_source_data(777)
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            # The legacy typed target prefix is valid, but the evidence bundle is truncated.
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 2, "data": sound},
        }

        result = build_audio.traverse_hirc_event(1, objects, {777}, bank_version=150)
        self.assertEqual(result["mediaIds"], [777])
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["actionDispatchEvidence"]["failedPlaybackActionCount"], 1)
        self.assertTrue(result["actionEvidence"][0]["traversed"])
        self.assertEqual(result["actionEvidence"][0]["actionParserStatus"], "failedClosed")
        self.assertEqual(
            result["actionEvidence"][0]["actionParserFailure"]["reason"],
            "truncatedActionHeader",
        )

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
        children_offset = 40
        container_data = bytearray(children_offset - 24)
        container_data[8:12] = pack("<I", 999)
        # Incidental object/media-looking integers are not typed child edges.
        container_data[12:16] = pack("<I", unrelated_sound)
        container_data.extend(pack("<HHHfffHBBBB", 1, 0, 0, 0.0, 0.0, 0.0, 1, 0, 0, 0, 0x12))
        container_data.extend(pack("<III", 2, sound_a, sound_b))
        container_data.extend(pack("<H", 2))
        container_data.extend(pack("<II", sound_b, 50000))
        container_data.extend(pack("<II", sound_a, 25000))

        def sound_data(media_id: int, parent_id: int) -> bytes:
            return sound_source_data(media_id, parent_id)

        objects = {
            event_id: {"type": 4, "data": event_data},
            play_action: {"type": 3, "data": play_data},
            stop_action: {"type": 3, "data": stop_data},
            container_id: {"type": 5, "data": bytes(container_data)},
            sound_a: {"type": 2, "data": sound_data(401, container_id)},
            sound_b: {"type": 2, "data": sound_data(402, container_id)},
            unrelated_sound: {"type": 2, "data": sound_data(499, 777)},
        }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {401, 402, 499}, bank_version=150
        )
        self.assertTrue(objects[sound_a]["_typedParentIdParsed"])
        self.assertEqual(objects[sound_a]["_typedParentId"], container_id)
        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["rootPlayActionCount"], 1)
        self.assertEqual(result["rootStopActionCount"], 1)
        self.assertEqual(result["containerEvidence"][0]["childrenOffset"], children_offset)
        self.assertEqual(result["containerEvidence"][0]["modeLabel"], "random")
        self.assertEqual(
            result["containerEvidence"][0]["selectorParserStatus"],
            "typedExactV150PlaylistWeights",
        )
        self.assertEqual(
            result["containerEvidence"][0]["playlistChildOrder"],
            [sound_b, sound_a],
        )
        self.assertFalse(result["containerEvidence"][0]["childrenOrderMatchesPlaylist"])
        self.assertEqual(result["containerEvidence"][0]["nonDefaultWeightCount"], 1)
        self.assertEqual(result["containerEvidence"][0]["flagLabels"], [
            "resetPlaylistAtEachPlay", "global",
        ])
        self.assertEqual(
            {tuple(row["relationTypes"]) for row in result["mediaEvidence"]},
            {("randomAlternative",)},
        )
        self.assertNotIn(unrelated_sound, result["visitedObjectIds"])

    def test_state_and_game_parameter_actions_are_control_only(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x1204, 100)},
            3: {"type": 3, "data": pack("<HI", 0x1402, 200)},
        }
        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=150)
        self.assertEqual(
            [row["operation"] for row in result["actionEvidence"]],
            ["setState", "resetGameParameter"],
        )
        self.assertEqual(result["rootPlayActionCount"], 0)
        self.assertEqual(result["mediaIds"], [])
        self.assertTrue(all(not row["traversed"] for row in result["actionEvidence"]))

    def test_named_v150_control_action_operations_are_not_playback_edges(self) -> None:
        operation_types = [0x0203, 0x0303, 0x0602, 0x0702, 0x1302, 0x1902, 0x1B02]
        objects = {
            1: {"type": 4, "data": bytes([len(operation_types)]) + b"".join(
                pack("<I", index + 2) for index in range(len(operation_types))
            )},
            **{
                index + 2: {"type": 3, "data": pack("<HI", action_type, 100 + index)}
                for index, action_type in enumerate(operation_types)
            },
        }

        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=150)

        self.assertEqual(
            [row["operation"] for row in result["actionEvidence"]],
            ["pause", "resume", "mute", "unmute", "setGameParameter", "setSwitch", "trigger"],
        )
        self.assertEqual(result["rootPlayActionCount"], 0)
        self.assertTrue(all(not row["traversed"] for row in result["actionEvidence"]))

    def test_v150_random_sequence_policy_preserves_playlist_order_weights_and_fail_closed_tail(self) -> None:
        children_offset = 24
        child_ids = [10, 20, 30]
        data = bytearray()
        data.extend(pack(
            "<HHHfffHBBBB",
            2, 1, 3, 125.0, 25.0, 50.0, 4, 3, 1, 1, 0x1A,
        ))
        data.extend(pack("<I", len(child_ids)))
        data.extend(b"".join(pack("<I", child_id) for child_id in child_ids))
        data.extend(pack("<H", len(child_ids)))
        for child_id, weight in ((30, 50000), (10, 25000), (20, 75000)):
            data.extend(pack("<II", child_id, weight))

        policy = build_audio.hirc_v150_random_sequence_properties(
            bytes(data), children_offset, child_ids, bank_version=150
        )

        self.assertEqual(policy["selectorParserStatus"], "typedExactV150PlaylistWeights")
        self.assertEqual(policy["modeLabel"], "sequence")
        self.assertEqual(policy["randomModeLabel"], "shuffle")
        self.assertEqual(policy["transitionModeLabel"], "delay")
        self.assertEqual(policy["playlistChildOrder"], [30, 10, 20])
        self.assertEqual(policy["playlistMembershipStatus"], "playlistCoversOwnedChildren")
        self.assertEqual(policy["duplicatePlaylistItemCount"], 0)
        self.assertEqual(policy["ownedChildIdsNotInPlaylist"], [])
        self.assertFalse(policy["childrenOrderMatchesPlaylist"])
        self.assertEqual(policy["loopCount"], 2)
        self.assertEqual(policy["avoidRepeatCount"], 4)
        self.assertEqual(policy["nonDefaultWeightCount"], 2)
        self.assertFalse(policy["uniformWeights"])
        self.assertNotIn("usesWeight", policy["flagLabels"])

        truncated = build_audio.hirc_v150_random_sequence_properties(
            bytes(data[:-8]), children_offset, child_ids, bank_version=150
        )
        self.assertEqual(
            truncated["selectorParserStatus"],
            "unresolvedV150RandomSequenceTail",
        )
        self.assertEqual(truncated["selectorParserFailureReason"], "unexpectedPlaylistTailLength")
        self.assertEqual(truncated["modeLabel"], "sequence")

        repeated = bytearray(data[:children_offset + 4 + len(child_ids) * 4])
        repeated.extend(pack("<H", 2))
        repeated.extend(pack("<II", 10, 50000))
        repeated.extend(pack("<II", 10, 25000))
        repeated_policy = build_audio.hirc_v150_random_sequence_properties(
            bytes(repeated), children_offset, child_ids, bank_version=150
        )
        self.assertEqual(
            repeated_policy["selectorParserStatus"],
            "typedExactV150PlaylistWeights",
        )
        self.assertEqual(
            repeated_policy["playlistMembershipStatus"],
            "playlistWithRepeatedOwnedChildren",
        )
        self.assertEqual(repeated_policy["duplicatePlaylistItemCount"], 1)
        self.assertEqual(repeated_policy["ownedChildIdsNotInPlaylist"], [20, 30])

        empty = bytearray(data[:children_offset + 4 + len(child_ids) * 4])
        empty.extend(pack("<H", 0))
        empty_policy = build_audio.hirc_v150_random_sequence_properties(
            bytes(empty), children_offset, child_ids, bank_version=150
        )
        self.assertEqual(
            empty_policy["playlistMembershipStatus"],
            "emptyPlaylistOwnedChildrenPreserved",
        )
        self.assertEqual(empty_policy["ownedChildIdsNotInPlaylist"], child_ids)

    def test_v150_layer_tail_preserves_rtpc_child_curves(self) -> None:
        child_id = 0x11223344
        tail = bytes.fromhex(
            "01000000"
            "ddccbbaa"
            "0000"
            "78563412"
            "00"
            "01000000"
            "44332211"
            "01000000"
            "00000000"
            "0000803f"
            "09000000"
            "00"
        )

        result = build_audio.hirc_v150_layer_tail(
            tail, 0, [child_id], bank_version=150
        )

        self.assertEqual(result["layerTailParserStatus"], "typedExactV150LayerTail")
        self.assertEqual(result["layerAssignmentStatus"], "nonEmptyCurves")
        self.assertEqual(result["layerCount"], 1)
        self.assertEqual(result["associationCount"], 1)
        self.assertEqual(result["curvePointCount"], 1)
        layer = result["layers"][0]
        self.assertEqual(layer["layerId"], 0xAABBCCDD)
        self.assertEqual(layer["rtpcId"], 0x12345678)
        self.assertEqual(layer["rtpcTypeLabel"], "gameParameter")
        self.assertEqual(layer["associations"][0]["childId"], child_id)
        self.assertEqual(
            layer["associations"][0]["curvePoints"][0]["interpolationLabel"],
            "Constant",
        )
        self.assertFalse(result["continuousValidation"])

        trailing = build_audio.hirc_v150_layer_tail(
            tail + b"\x00", 0, [child_id], bank_version=150
        )
        self.assertEqual(trailing["layerTailParserStatus"], "unresolvedV150LayerTail")
        self.assertEqual(trailing["layerTailFailureReason"], "unexpectedTrailingBytes")

    def test_v150_layer_candidate_without_parent_proof_remains_partial(self) -> None:
        event_id = 100
        action_id = 101
        layer_id = 200
        sound_id = 0x11223344
        media_id = 401
        children_offset = 20
        tail = bytes.fromhex(
            "01000000ddccbbaa00007856341200010000004433221101000000"
            "000000000000803f0900000000"
        )
        layer_data = bytes(children_offset) + pack("<II", 1, sound_id) + tail

        sound_data = sound_source_data(media_id, 999)  # Deliberately not reciprocal.
        objects = {
            event_id: {"type": 4, "data": bytes([1]) + pack("<I", action_id)},
            action_id: {"type": 3, "data": pack("<HI", 0x0403, layer_id)},
            layer_id: {"type": 9, "data": layer_data},
            sound_id: {"type": 2, "data": sound_data},
        }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {media_id}, bank_version=150
        )

        self.assertEqual(result["mediaIds"], [media_id])
        self.assertEqual(result["traversalStatus"], "partial")
        layer = result["containerEvidence"][0]
        self.assertEqual(
            layer["parserConfidence"],
            "typedExactV150CandidateWithoutParentProof",
        )
        self.assertEqual(
            layer["layerTailEvidence"]["layerAssignmentStatus"],
            "nonEmptyCurves",
        )
        self.assertEqual(
            result["unresolvedNodes"][0]["reason"],
            "layerChildrenCandidateWithoutParentProof",
        )

        canonical_empty = bytes(31) + bytes.fromhex("000000000000000000")
        candidate = build_audio.hirc_v150_layer_child_candidate(
            canonical_empty, {}, bank_version=150
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate[0], [])
        self.assertEqual(candidate[1], 31)
        self.assertEqual(candidate[3], "typedExactV150CanonicalEmpty")

    def test_v150_switch_mapping_preserves_flat_value_packages_without_pruning(self) -> None:
        event_id = 100
        action_id = 101
        switch_id = 200
        sound_a = 301
        sound_b = 302
        group_id = 0x3C9C2C56
        default_value_id = 0x8D36849F
        value_id = 0xF44F784A
        children_offset = 40

        switch_data = bytearray(children_offset - 10)
        switch_data.append(0)
        switch_data.extend(pack("<II", group_id, default_value_id))
        switch_data.append(1)
        switch_data.extend(pack("<III", 2, sound_a, sound_b))
        switch_data.extend(pack("<I", 2))
        switch_data.extend(pack("<III", value_id, 1, sound_a))
        switch_data.extend(pack("<II", default_value_id, 0))
        switch_data.extend(pack("<I", 2))
        switch_data.extend(pack("<IBBii", sound_a, 3, 1, 500, -250))
        switch_data.extend(pack("<IBBii", sound_b, 0, 0, 1, 0))

        def sound_data(media_id: int) -> bytes:
            return sound_source_data(media_id, switch_id)

        objects = {
            event_id: {"type": 4, "data": bytes([1]) + pack("<I", action_id)},
            action_id: {"type": 3, "data": pack("<HI", 0x0403, switch_id)},
            switch_id: {"type": 6, "data": bytes(switch_data)},
            sound_a: {"type": 2, "data": sound_data(401)},
            sound_b: {"type": 2, "data": sound_data(402)},
        }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {401, 402}, bank_version=150
        )

        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["traversalStatus"], "complete")
        switch = result["containerEvidence"][0]["switchMappingEvidence"]
        self.assertEqual(switch["parserStatus"], "typedExactV150FlatPackages")
        self.assertEqual(switch["selectionStructure"], "flatValuePackages")
        self.assertEqual(switch["groupType"], "switch")
        self.assertEqual(switch["groupTypeRaw"], 0)
        self.assertEqual(switch["groupId"], group_id)
        self.assertEqual(switch["defaultValueId"], default_value_id)
        self.assertTrue(switch["continuousValidation"])
        self.assertEqual(switch["packages"][0], {
            "packageIndex": 0,
            "valueId": value_id,
            "isDefaultValue": False,
            "mappedChildCount": 1,
            "childIds": [sound_a],
        })
        self.assertTrue(switch["packages"][1]["isDefaultValue"])
        self.assertEqual(switch["unmappedChildIds"], [sound_b])
        self.assertTrue(switch["associations"][0]["isFirstOnly"])
        self.assertTrue(switch["associations"][0]["continuePlayback"])
        self.assertEqual(switch["associations"][0]["onSwitchMode"], "stop")
        self.assertEqual(switch["associations"][0]["fadeOutTimeMs"], 500)
        self.assertEqual(switch["associations"][0]["fadeInTimeMs"], -250)
        self.assertEqual(switch["associations"][1]["onSwitchMode"], "playToEnd")
        self.assertEqual(
            switch["runtimeSelection"],
            "groupValueUnobservedAllChildrenRemainPossible",
        )

        state_data = bytearray(switch_data)
        state_data[children_offset - 10] = 1
        state_mapping = build_audio.hirc_v150_switch_mapping(
            bytes(state_data), children_offset, 2, bank_version=150
        )
        self.assertEqual(state_mapping["groupType"], "state")
        self.assertEqual(state_mapping["groupTypeRaw"], 1)

        no_package_data = bytearray(children_offset - 10)
        no_package_data.append(1)
        no_package_data.extend(pack("<II", 0x3C9C2C56, 0x8D36849F))
        no_package_data.append(0)
        no_package_data.extend(pack("<III", 2, sound_a, sound_b))
        no_package_data.extend(pack("<I", 0))
        no_package = build_audio.hirc_v150_switch_mapping(
            bytes(no_package_data),
            children_offset,
            2,
            bank_version=150,
        )
        self.assertEqual(no_package["parserStatus"], "unresolvedV150SwitchTail")
        self.assertEqual(no_package["failureReason"], "noValuePackages")

    def test_v150_switch_mapping_marks_distinct_layout_unresolved_without_pruning(self) -> None:
        switch_id = 200
        sound_a = 301
        sound_b = 302
        children_offset = 40
        switch_data = bytearray(children_offset - 10)
        # Current distinct-layout objects do not have the flat selector header
        # at C-9; interpreting their final header byte as continuous-validation
        # yields a non-boolean value and must fail before package claims.
        switch_data.extend(bytes.fromhex("0000949cee04bb233163"))
        switch_data.extend(pack("<III", 2, sound_a, sound_b))
        switch_data.extend(pack("<I", 2))
        switch_data.extend(pack("<IBBii", sound_a, 0, 1, 0, 0))
        switch_data.extend(pack("<IBBii", sound_b, 0, 1, 0, 0))

        def sound_data(media_id: int) -> bytes:
            return sound_source_data(media_id, switch_id)

        objects = {
            100: {"type": 4, "data": bytes([1]) + pack("<I", 101)},
            101: {"type": 3, "data": pack("<HI", 0x0403, switch_id)},
            switch_id: {"type": 6, "data": bytes(switch_data)},
            sound_a: {"type": 2, "data": sound_data(401)},
            sound_b: {"type": 2, "data": sound_data(402)},
        }

        result = build_audio.traverse_hirc_event(
            100, objects, {401, 402}, bank_version=150
        )

        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["traversalStatus"], "complete")
        switch = result["containerEvidence"][0]["switchMappingEvidence"]
        self.assertEqual(switch["parserStatus"], "unresolvedV150SwitchTail")
        self.assertEqual(switch["failureReason"], "invalidContinuousValidation")
        self.assertGreater(switch["unresolvedTailByteLength"], 0)
        self.assertEqual(
            switch["runtimeSelection"],
            "groupValueUnobservedAllChildrenRemainPossible",
        )

    def test_typed_hirc_traversal_resolves_v150_music_graph_and_track_media(self) -> None:
        def node_base(parent_id: int) -> bytes:
            return bytes(4) + pack("<II", 0, parent_id)

        def common_music_prefix(parent_id: int, child_ids: list[int]) -> bytes:
            return b"".join([
                bytes([0]),
                node_base(parent_id),
                bytes(7),
                pack("<I", len(child_ids)),
                *(pack("<I", child_id) for child_id in child_ids),
                pack("<ddfBBBI", 1.0, 0.0, 120.0, 4, 4, 0, 0),
            ])

        event_id = 1
        action_id = 2
        switch_id = 10
        ranseq_id = 11
        segment_id = 12
        track_id = 13
        media_id = 777

        switch_data = b"".join([
            common_music_prefix(0, [ranseq_id]),
            pack("<I", 0),  # transition rules
            bytes([1]),
            pack("<II", 1, 0x12345678),
            bytes([0]),
            pack("<I", 24),
            bytes([0]),
            pack("<IIHH", 0, 0x00010001, 1, 100),
            pack("<IIHH", 0x87654321, ranseq_id, 1, 100),
        ])
        ranseq_data = b"".join([
            common_music_prefix(switch_id, [segment_id]),
            pack("<I", 0),  # transition rules
            pack("<I", 2),
            pack("<IIIIhhhIHBB", 0, 100, 1, 0, 1, 1, 1, 50, 0, 1, 0),
            pack("<IIIIhhhIHBB", segment_id, 101, 0, 0xFFFFFFFF, 1, 1, 1, 50, 0, 0, 0),
        ])
        segment_data = b"".join([
            common_music_prefix(ranseq_id, [track_id]),
            pack("<dI", 3000.0, 1),
            pack("<Id", 1, 0.0),
            b"Entry\x00",
        ])
        track_data = b"".join([
            bytes([0]),
            pack("<I", 1),
            pack("<IBIIB", 0x00040001, 2, media_id, 2048, 0x80),
            pack("<I", 1),
            pack("<III4d", 0, media_id, 0, 0.0, 0.0, 0.0, 3000.0),
            pack("<I", 1),  # subtracks
            pack("<I", 0),  # automation items
            node_base(segment_id),
        ])
        objects = {
            event_id: {"type": 4, "data": bytes([1]) + pack("<I", action_id)},
            action_id: {"type": 3, "data": pack("<HI", 0x0403, switch_id)},
            switch_id: {"type": 12, "data": switch_data},
            ranseq_id: {"type": 13, "data": ranseq_data},
            segment_id: {"type": 10, "data": segment_data},
            track_id: {"type": 11, "data": track_data},
        }

        result = build_audio.traverse_hirc_event(event_id, objects, {media_id}, bank_version=150)
        self.assertEqual(result["mediaIds"], [media_id])
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["unresolvedNodes"], [])
        self.assertEqual(
            [row["objectType"] for row in result["musicNodeEvidence"]],
            [12, 13, 10, 11],
        )
        switch = result["musicNodeEvidence"][0]
        self.assertEqual(switch["treeDepth"], 1)
        self.assertEqual(switch["treeLeaves"][0]["audioNodeId"], ranseq_id)
        self.assertEqual(switch["selectorValidation"], {
            "status": "reciprocalChildrenCovered",
            "treeLeafIds": [ranseq_id],
            "reciprocalChildIds": [ranseq_id],
            "treeLeafIdsOutsideReciprocalChildren": [],
            "reciprocalChildrenWithoutTreeLeaf": [],
            "recursiveOwnedDescendantIds": [],
            "zeroUnboundLeafIds": [],
            "sameBankMissingLeafIds": [],
            "localOtherParentLeafIds": [],
            "ownedDirectChildIdsNotInTreeLeaves": [],
            "runtimeBranchStatus": "groupValuesAndActiveLeafNotObserved",
        })
        mismatched_switch = build_audio.hirc_v150_music_switch_structure(
            switch_data,
            1 + 12 + 7,
            1,
            [ranseq_id + 1],
        )
        self.assertEqual(
            mismatched_switch["selectorValidation"]["status"],
            "treeLeafOutsideReciprocalChildren",
        )
        self.assertEqual(
            mismatched_switch["selectorValidation"]["treeLeafIdsOutsideReciprocalChildren"],
            [ranseq_id],
        )
        subset_switch = build_audio.hirc_v150_music_switch_structure(
            switch_data,
            1 + 12 + 7,
            1,
            [ranseq_id, ranseq_id + 1],
        )
        self.assertEqual(
            subset_switch["selectorValidation"]["status"],
            "decisionTreeSubsetOfReciprocalChildren",
        )
        self.assertEqual(
            subset_switch["selectorValidation"]["reciprocalChildrenWithoutTreeLeaf"],
            [ranseq_id + 1],
        )
        ranseq = result["musicNodeEvidence"][1]
        self.assertEqual(ranseq["selectionTypeLabels"], ["continuousSequence", "none"])
        self.assertEqual(ranseq["selectorValidation"], {
            "status": "reciprocalChildrenCovered",
            "playlistTerminalSegmentIds": [segment_id],
            "reciprocalChildIds": [segment_id],
            "playlistTerminalSegmentIdsOutsideReciprocalChildren": [],
            "reciprocalChildrenWithoutPlaylistTerminal": [],
            "terminalPlaylistItemCount": 1,
            "terminalItemsWithSentinelSegmentId": 0,
        })
        mismatched_ranseq = build_audio.hirc_v150_music_random_sequence_structure(
            ranseq_data,
            1 + 12 + 7,
            1,
            [segment_id, segment_id + 1],
        )
        self.assertEqual(
            mismatched_ranseq["selectorValidation"]["status"],
            "playlistSubsetOfReciprocalChildren",
        )
        self.assertEqual(
            mismatched_ranseq["selectorValidation"]["reciprocalChildrenWithoutPlaylistTerminal"],
            [segment_id + 1],
        )
        self.assertEqual(ranseq["playlistItems"][1]["segmentId"], segment_id)
        track = result["musicNodeEvidence"][3]
        self.assertEqual(track["sources"][0]["mediaId"], media_id)
        self.assertEqual(result["mediaEvidence"][0]["musicTrackObjectIds"], [track_id])
        self.assertEqual(result["mediaEvidence"][0]["selectionPaths"], [[
            "musicSwitchCandidate",
            "musicPlaylistCandidate",
            "musicTrack",
            "musicTrackSource",
        ]])

    def test_v150_empty_music_children_require_unique_typed_tail(self) -> None:
        node_base = bytes(4) + pack("<II", 0, 0)
        segment_data = b"".join([
            bytes([0]),
            node_base,
            bytes(7),
            pack("<I", 0),
            pack("<ddfBBBI", 1.0, 0.0, 120.0, 4, 4, 0, 0),
            pack("<dI", 0.0, 0),
        ])
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 10, "data": segment_data},
        }

        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=150)
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["containerEvidence"][0]["childCount"], 0)
        self.assertEqual(result["containerEvidence"][0]["parserConfidence"], "typedTailExactEmpty")

    def test_music_switch_leaf_ownership_distinguishes_recursive_unbound_and_missing(self) -> None:
        def music_node(parent_id: int) -> dict[str, object]:
            return {
                "type": 10,
                "data": bytes([0]) + bytes(4) + pack("<II", 0, parent_id),
            }

        switch_id = 10
        direct_child = 20
        recursive_leaf = 21
        other_parent_leaf = 22
        missing_leaf = 99
        objects = {
            direct_child: music_node(switch_id),
            recursive_leaf: music_node(direct_child),
            other_parent_leaf: music_node(777),
        }
        structure = {
            "treeLeaves": [
                {"audioNodeId": direct_child},
                {"audioNodeId": recursive_leaf},
                {"audioNodeId": 0},
                {"audioNodeId": missing_leaf},
                {"audioNodeId": other_parent_leaf},
            ],
            "transitionRules": [{
                "sourceIds": [recursive_leaf],
                "destinationIds": [0, missing_leaf],
            }],
            "selectorValidation": {
                "status": "treeLeafOutsideReciprocalChildren",
                "treeLeafIds": [0, direct_child, recursive_leaf, other_parent_leaf, missing_leaf],
                "reciprocalChildIds": [direct_child],
                "treeLeafIdsOutsideReciprocalChildren": [
                    0, recursive_leaf, other_parent_leaf, missing_leaf,
                ],
                "reciprocalChildrenWithoutTreeLeaf": [],
            },
        }

        refined = build_audio.refine_hirc_v150_music_switch_selector_ownership(
            structure, switch_id, objects
        )
        validation = refined["selectorValidation"]
        self.assertEqual(validation["status"], "decisionTreeLeafOwnershipUnresolved")
        self.assertEqual(validation["recursiveOwnedDescendantIds"], [recursive_leaf])
        self.assertEqual(validation["zeroUnboundLeafIds"], [0])
        self.assertEqual(validation["sameBankMissingLeafIds"], [missing_leaf])
        self.assertEqual(validation["localOtherParentLeafIds"], [other_parent_leaf])
        by_id = {row["audioNodeId"]: row for row in refined["treeLeaves"]}
        self.assertEqual(by_id[recursive_leaf]["ownershipParentChain"], [direct_child, switch_id])
        self.assertEqual(
            by_id[recursive_leaf]["transitionReferenceRoles"],
            ["transitionSource"],
        )
        self.assertEqual(
            by_id[0]["transitionReferenceRoles"],
            ["transitionDestination"],
        )

        resolved = build_audio.refine_hirc_v150_music_switch_selector_ownership(
            {
                "treeLeaves": [
                    {"audioNodeId": direct_child},
                    {"audioNodeId": recursive_leaf},
                    {"audioNodeId": 0},
                ],
                "transitionRules": [],
                "selectorValidation": {
                    "status": "treeLeafOutsideReciprocalChildren",
                    "reciprocalChildIds": [direct_child],
                    "reciprocalChildrenWithoutTreeLeaf": [],
                },
            },
            switch_id,
            objects,
        )
        self.assertEqual(
            resolved["selectorValidation"]["status"],
            "decisionTreeIndirectAndUnboundLeavesResolved",
        )

    def test_typed_hirc_traversal_fails_closed_on_truncated_music_track(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            # A media-looking U32 in a malformed MusicTrack is not a source edge.
            3: {"type": 11, "data": pack("<II", 1, 777)},
        }
        result = build_audio.traverse_hirc_event(1, objects, {777})
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["traversalStatus"], "partial")
        self.assertEqual(result["unresolvedNodes"][0]["reason"], "musicTrackPrefixUnresolved")

    def test_typed_hirc_traversal_rejects_music_nodes_from_non_v150_bank(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 11, "data": bytes(64)},
        }
        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=154)
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["unresolvedNodes"][0]["reason"], "unsupportedMusicBankVersion")

    def test_play_event_follows_nested_event_actions(self) -> None:
        sound = sound_source_data(99)
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x2103, 3)},
            3: {"type": 4, "data": bytes([1]) + pack("<I", 4)},
            4: {"type": 3, "data": pack("<HI", 0x0403, 5)},
            5: {"type": 2, "data": sound},
        }
        result = build_audio.traverse_hirc_event(1, objects, {99})
        self.assertEqual(result["mediaIds"], [99])
        self.assertEqual([row["operation"] for row in result["actionEvidence"]], ["playEvent", "play"])
        self.assertEqual(
            [
                (row["dispatchEventId"], row["eventActionOrdinal"], row["isRootEventAction"])
                for row in result["actionEvidence"]
            ],
            [(1, 0, True), (3, 0, False)],
        )

    def test_shared_sound_keeps_every_play_root_without_duplicate_media(self) -> None:
        sound = sound_source_data(99)
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            3: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            4: {"type": 2, "data": sound},
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
            "sourceKinds": ["codecMedia"],
            "pluginIds": [0x00040001],
            "pluginNames": ["Wwise Vorbis"],
            "streamTypes": [{"value": 2, "label": "streamedZeroLatency"}],
            "sourceBits": [0],
        }])
        self.assertEqual(result["sourceObjectSummary"]["sourceReferenceCount"], 2)
        self.assertEqual(result["sourceObjectSummary"]["uniqueSourceObjectCount"], 1)
        self.assertEqual(result["sourceObjectSummary"]["sourceKindCounts"], {"codecMedia": 2})
        self.assertEqual(result["nonMediaSourceEvidence"], [])

    def test_v150_sound_sources_separate_codec_external_and_synthesized_audio(self) -> None:
        codec = sound_source_data(
            101, 900, stream_type=1, in_memory_size=4096, source_bits=0x09,
        )
        external = sound_source_data(
            202, 901, plugin_id=0x00080001, stream_type=2,
            in_memory_size=0, source_bits=0,
        )
        synthesized = sound_source_data(
            303, 902, plugin_id=0x00650002, stream_type=0,
            plugin_parameters=b"\x01\x02\x03",
        )

        codec_row = build_audio.hirc_v150_sound_source(codec)
        self.assertEqual(codec_row["sourceKind"], "codecMedia")
        self.assertEqual(codec_row["pluginName"], "Wwise Vorbis")
        self.assertEqual(codec_row["streamTypeLabel"], "streamed")
        self.assertTrue(codec_row["sourceFlags"]["isLanguageSpecific"])
        self.assertTrue(codec_row["sourceFlags"]["nonCachable"])
        self.assertEqual(codec_row["parentId"], 900)
        self.assertEqual(build_audio.hirc_sound_media_id(codec), 101)

        external_row = build_audio.hirc_v150_sound_source(external)
        self.assertEqual(external_row["sourceKind"], "externalSourceCodec")
        self.assertEqual(external_row["pluginName"], "Wwise External Source")
        self.assertIsNone(build_audio.hirc_sound_media_id(external))

        synth_row = build_audio.hirc_v150_sound_source(synthesized)
        self.assertEqual(synth_row["sourceKind"], "synthesizedSource")
        self.assertEqual(synth_row["pluginParameterSize"], 3)
        self.assertEqual(synth_row["nodeBaseOffset"], 21)
        self.assertEqual(build_audio.hirc_object_parent_id(2, synthesized), 902)
        self.assertIsNone(build_audio.hirc_sound_media_id(synthesized))

        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            3: {"type": 3, "data": pack("<HI", 0x0403, 5)},
            4: {"type": 2, "data": external},
            5: {"type": 2, "data": synthesized},
        }
        result = build_audio.traverse_hirc_event(1, objects, {202, 303})
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["sourceMediaIds"], [])
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["sourceObjectSummary"]["sourceKindCounts"], {
            "externalSourceCodec": 1,
            "synthesizedSource": 1,
        })
        self.assertEqual(
            [row["mediaLocationStatus"] for row in result["nonMediaSourceEvidence"]],
            ["unresolvedExternalSource", "synthesizedSource"],
        )


class AudioDumperTests(unittest.TestCase):
    def test_all_mode_runs_primary_once_and_adds_persistent_hotfix_pass(self) -> None:
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
            )

            with mock.patch.object(build_audio.subprocess, "run") as run:
                build_audio.run_audio_dumper(args, "CN", build_audio.LANGUAGES["CN"])

            self.assertEqual(run.call_count, 2)
            primary = run.call_args_list[0].args[0]
            hotfix = run.call_args_list[1].args[0]
            self.assertEqual(primary[primary.index("--block") + 1], "all")
            self.assertEqual(primary[primary.index("--format") + 1], "flac")
            self.assertEqual(Path(primary[primary.index("--streaming-assets") + 1]), streaming)
            self.assertIn("--shared-output", primary)
            self.assertEqual(hotfix[hotfix.index("--block") + 1], "hotfix-audio")
            self.assertEqual(Path(hotfix[hotfix.index("--streaming-assets") + 1]), persistent)
            self.assertNotIn("--shared-output", hotfix)

    def test_explicit_hotfix_mode_uses_persistent_as_primary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            executable = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            executable.touch()
            streaming.mkdir()
            persistent.mkdir()
            args = argparse.Namespace(
                skip_decode=False,
                audio_dumper=executable,
                streaming_assets=streaming,
                fallback_assets=persistent,
                audio_root=root / "Audio",
                block="hotfix-audio",
            )

            with mock.patch.object(build_audio.subprocess, "run") as run:
                build_audio.run_audio_dumper(args, "CN", build_audio.LANGUAGES["CN"])

            self.assertEqual(run.call_count, 1)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--block") + 1], "hotfix-audio")
            self.assertEqual(command[command.index("--format") + 1], "flac")
            self.assertEqual(Path(command[command.index("--streaming-assets") + 1]), persistent)
            self.assertEqual(Path(command[command.index("--fallback-assets") + 1]), streaming)

    def test_event_media_inventory_fingerprint_tracks_numeric_media(self) -> None:
        media = {
            "42": {"id": "42", "storageRoot": "shared", "rel": "wwise/42.flac", "bytes": 10},
            "dialog": {"id": "dialog", "storageRoot": "CN", "rel": "voice/dialog.flac", "bytes": 20},
        }
        initial = build_audio.event_media_inventory_fingerprint(media)
        media["42"]["bytes"] = 11
        self.assertNotEqual(initial, build_audio.event_media_inventory_fingerprint(media))

    def test_audio_file_priority_prefers_flac_over_legacy_wav(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            (root / "same.wav").write_bytes(b"wav")
            (root / "same.flac").write_bytes(b"flac")
            files = build_audio.iter_audio_files(root)
            self.assertEqual([path.suffix for path in files], [".flac", ".wav"])

    def test_flac_file_metrics_read_duration_and_average_bitrate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "test.flac"
            sample_rate = 48_000
            total_samples = 96_000
            packed_stream_info = (
                (sample_rate << 44)
                | (1 << 41)
                | (15 << 36)
                | total_samples
            )
            stream_info = bytes(10) + packed_stream_info.to_bytes(8, "big") + bytes(16)
            path.write_bytes(b"fLaC" + bytes((0x80, 0, 0, 34)) + stream_info + bytes(958))

            metrics = build_audio.audio_file_metrics(path)

            self.assertEqual(metrics["duration"], 2.0)
            self.assertEqual(metrics["bitrate"], path.stat().st_size * 4)

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
    def test_writes_projectile_audio_sidecar_without_mutating_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            projectile_path = webui_root / "data" / "gameplay" / "projectiles.json"
            projectile_path.parent.mkdir(parents=True)
            projectile_payload = {
                "schemaVersion": 3,
                "entries": [{
                    "id": "projectile_test",
                    "sounds": {"launchSound": {"value": -1, "hex": "0xffffffff"}},
                }],
            }
            projectile_path.write_text(json.dumps(projectile_payload), encoding="utf-8")
            original_projectile_bytes = projectile_path.read_bytes()
            key = "au_projectile_named_event"
            stats = build_audio.write_projectile_audio_sidecar(
                webui_root,
                "CN",
                {key: [{
                    "src": "/export_full/structured/Audio/shared/wwise/sfx/7.flac",
                    "mediaId": 7,
                    "format": "flac",
                    "bytes": 120,
                    "audioScope": "shared",
                    "bankId": 9,
                }]},
                [{"eventId": key, "eventHash": 0xFFFFFFFF, "source": "wwiseHirc"}],
            )

            self.assertEqual(projectile_path.read_bytes(), original_projectile_bytes)
            sidecar_path = webui_root / "data/lang/CN/gameplay/projectile_audio.json"
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            launch = payload["links"][0]
            self.assertEqual(stats["projectileSoundRefsLinked"], 1)
            self.assertEqual(payload["schemaVersion"], 1)
            self.assertEqual(launch["projectileId"], "projectile_test")
            self.assertEqual(launch["field"], "launchSound")
            self.assertEqual(launch["eventHash"], 0xFFFFFFFF)
            self.assertTrue(launch["event"]["foundInWwise"])
            self.assertEqual(launch["event"]["runtimeSelection"], "singleCandidate")
            self.assertEqual(launch["event"]["canonicalEventIds"], [key])
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
            (clip_root / "A_actor_unknown_ui_generic_p0000000000000002.anim").write_text(
                """%YAML 1.1
AnimationClip:
  m_Name: A_actor_unknown_ui_generic
  m_Events:
  - time: 0.5
    functionName: PostAudioEvent
    data: au_ui_generic
    floatParameter: 0
    intParameter: 0
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
            self.assertEqual(set(result["unownedEvents"]), {"au_ui_generic"})
            self.assertEqual(result["unownedEvents"]["au_ui_generic"][0]["ownerStatus"], "unresolved")
            self.assertEqual(result["counts"]["animationAudioClipsScanned"], 2)
            self.assertEqual(result["counts"]["animationAudioClipsOwnerUnresolved"], 1)

    def test_animation_controller_index_is_fail_closed_and_annotates_direct_clip_refs(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            clip_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            controller_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController"
            clip_root.mkdir(parents=True)
            controller_root.mkdir(parents=True)
            clip_template = """%YAML 1.1
AnimationClip:
  m_Name: {clip_name}
  m_Events:
  - time: 0.25
    functionName: PostAudioEvent
    data: {event_id}
"""
            (clip_root / "A_actor_test_battle_direct_p0000000000000001.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_direct",
                    event_id="au_direct_controller",
                ),
                encoding="utf-8",
            )
            (clip_root / "A_actor_test_battle_unresolved_p0000000000000002.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_unresolved",
                    event_id="au_unresolved_controller",
                ),
                encoding="utf-8",
            )
            (controller_root / "AnimatorController#fixture_p0000000000000003.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "type": "AnimatorController",
                        "pathId": 3,
                        "sourceFile": "CAB-controller-fixture",
                        "pptrReferences": [
                            {
                                "targetType": "AnimationClip",
                                "targetPathId": 1,
                                "targetSourceFile": "CAB-clip-fixture",
                                "resolutionStatus": "resolved",
                            },
                            {
                                # An unresolved PPtr must not become a name/path guess.
                                "targetType": "AnimationClip",
                                "targetPathId": 2,
                                "targetSourceFile": "CAB-clip-fixture",
                                "resolutionStatus": "unresolved",
                            },
                            {
                                "targetType": "AnimatorController",
                                "targetPathId": 2,
                                "targetSourceFile": "CAB-clip-fixture",
                                "resolutionStatus": "resolved",
                            },
                        ],
                    },
                    "m_Name": "AC_fixture_direct",
                }),
                encoding="utf-8",
            )
            # Missing exporter identity is fail-closed and cannot contribute an index row.
            (controller_root / "malformed.json").write_text(
                json.dumps({"m_Name": "AC_should_not_match"}),
                encoding="utf-8",
            )

            result = build_audio.collect_gameplay_animation_audio(
                export_root,
                [{"kind": "character", "id": "chr_0001_test", "skillGroups": []}],
                [],
            )

            owner = result["owners"][0]
            direct = owner["events"]["au_direct_controller"][0]
            unresolved = owner["events"]["au_unresolved_controller"][0]
            self.assertEqual(direct["clipReachability"], "directAnimatorController")
            self.assertEqual(direct["animatorControllerCount"], 1)
            self.assertEqual(
                direct["animatorControllerContexts"][0]["name"],
                "AC_fixture_direct",
            )
            self.assertEqual(unresolved["clipReachability"], "unresolved")
            self.assertEqual(unresolved["animatorControllerCount"], 0)
            self.assertEqual(unresolved["animatorControllerContexts"], [])
            self.assertEqual(result["counts"]["animationAudioControllerReachableClips"], 1)
            self.assertEqual(result["counts"]["animationAudioControllerUnresolvedClips"], 1)
            self.assertEqual(
                result["counts"]["animationAudioControllerReachableCallbackRows"],
                1,
            )
            self.assertEqual(
                result["animationControllerIndex"]["directReferenceCount"],
                1,
            )
            self.assertEqual(result["animationControllerIndex"]["status"], "partial")

    def test_animation_audio_scans_persistent_and_scopes_controller_path_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            streaming_clip_root = (
                export_root
                / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            )
            persistent_clip_root = (
                export_root
                / "recovered/AnimeStudio-cli/Persistent/convert_by_type/AnimationClip"
            )
            persistent_controller_root = (
                export_root
                / "recovered/AnimeStudio-cli/Persistent/json_by_type/AnimatorController"
            )
            streaming_clip_root.mkdir(parents=True)
            persistent_clip_root.mkdir(parents=True)
            persistent_controller_root.mkdir(parents=True)
            clip_template = """%YAML 1.1
AnimationClip:
  m_Name: {clip_name}
  m_Events:
  - time: 0.25
    functionName: PostAudioEvent
    data: {event_id}
"""
            # PathIDs are serialized-file identities, not global identities.
            # A Persistent controller reference must not annotate the same
            # numeric PathID under StreamingAssets.
            (streaming_clip_root / "A_actor_test_battle_stream_p0000000000000001.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_stream",
                    event_id="au_stream_unresolved",
                ),
                encoding="utf-8",
            )
            (persistent_clip_root / "A_actor_test_battle_patch_p0000000000000001.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_patch",
                    event_id="au_persistent_direct",
                ),
                encoding="utf-8",
            )
            (persistent_controller_root / "AnimatorController#fixture_p0000000000000003.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "type": "AnimatorController",
                        "pathId": 3,
                        "sourceFile": "CAB-persistent-controller",
                        "pptrReferences": [{
                            "targetType": "AnimationClip",
                            "targetPathId": 1,
                            "targetSourceFile": "CAB-persistent-clip",
                            "resolutionStatus": "resolved",
                        }],
                    },
                    "m_Name": "AC_persistent_fixture",
                }),
                encoding="utf-8",
            )

            result = build_audio.collect_gameplay_animation_audio(
                export_root,
                [{"kind": "character", "id": "chr_0001_test", "skillGroups": []}],
                [],
            )

            events = result["owners"][0]["events"]
            self.assertEqual(
                events["au_persistent_direct"][0]["clipReachability"],
                "directAnimatorController",
            )
            self.assertEqual(
                events["au_persistent_direct"][0]["animatorControllerContexts"][0]["storageRoot"],
                "Persistent",
            )
            self.assertEqual(
                events["au_stream_unresolved"][0]["clipReachability"],
                "unresolved",
            )
            self.assertEqual(result["counts"]["animationAudioClipsScanned"], 2)
            self.assertEqual(result["counts"]["animationAudioControllerReachableClips"], 1)
            self.assertEqual(
                result["animationControllerIndex"]["availableSourceRoots"],
                ["recovered/AnimeStudio-cli/Persistent/json_by_type/AnimatorController"],
            )

    def test_animator_controller_state_clip_refs_are_bounded_authored_membership(self) -> None:
        payload = {
            "m_AnimationClips": [
                {"m_FileID": 2, "m_PathID": 101},
                {"m_FileID": 2, "m_PathID": 102},
            ],
            "m_Controller": {
                "m_LayerArray": [{"data": {"m_StateMachineIndex": 0}}],
                "m_StateMachineArray": [{"data": {
                    "m_StateConstantArray": [{"data": {
                        "m_NameID": 11,
                        "m_FullPathID": 22,
                        "m_TagID": 33,
                        "m_BlendTreeConstantArray": [{"data": {
                            "m_NodeArray": [{"data": {
                                "m_ClipID": 1,
                                "m_BlendType": 0,
                            }}],
                        }}],
                    }}],
                }}],
            },
        }
        refs = build_audio.animator_controller_state_clip_refs(payload)
        self.assertEqual(list(refs), [1])
        self.assertEqual(refs[1][0]["clipSlot"], 1)
        self.assertEqual(refs[1][0]["stateMachineLayerIndices"], [0])
        self.assertTrue(refs[1][0]["stateMachineReferencedByLayer"])
        self.assertEqual(refs[1][0]["reachability"], "authoredStateMembership")
        self.assertEqual(refs[1][0]["runtimeExecution"], "unobserved")

        malformed = dict(payload)
        malformed["m_Controller"] = {"m_LayerArray": "not-a-list"}
        self.assertEqual(build_audio.animator_controller_state_clip_refs(malformed), {})

    def test_animator_override_index_keeps_corpus_unique_mapping_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            clip_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            controller_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController"
            override_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorOverrideController"
            clip_root.mkdir(parents=True)
            controller_root.mkdir(parents=True)
            override_root.mkdir(parents=True)
            clip_text = """%YAML 1.1
AnimationClip:
  m_Name: A_actor_test_battle_override
  m_Events:
  - time: 0.25
    functionName: PostAudioEvent
    data: au_override_fixture
"""
            (clip_root / "A_actor_test_battle_override_p0000000000000002.anim").write_text(
                clip_text,
                encoding="utf-8",
            )
            (controller_root / "AnimatorController#fixture_p0000000000000003.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "type": "AnimatorController",
                        "pathId": 3,
                        "sourceFile": "CAB-controller-fixture",
                    },
                    "m_Name": "AC_fixture_override",
                }),
                encoding="utf-8",
            )
            (override_root / "AC_eny_0001_fixture_p0000000000000004.json").write_text(
                json.dumps({
                    "m_Controller": {"m_FileID": 0, "m_PathID": 3, "IsNull": False},
                    "m_Clips": [{
                        "m_OriginalClip": {"m_FileID": 0, "m_PathID": 1, "IsNull": False},
                        "m_OverrideClip": {"m_FileID": 0, "m_PathID": 2, "IsNull": False},
                    }],
                }),
                encoding="utf-8",
            )

            result = build_audio.collect_animation_override_index(export_root)
            self.assertEqual(result["summary"]["overrideControllerCount"], 1)
            self.assertEqual(result["summary"]["replacementReferenceCount"], 1)
            self.assertEqual(result["summary"]["controllerPathIdCorpusUnique"], 1)
            self.assertEqual(result["summary"]["effectiveClipCorpusUniqueReferences"], 1)
            context = result["byClipPathId"][2][0]
            self.assertEqual(context["mappingKind"], "replacement")
            self.assertEqual(context["controllerJoinStatus"], "corpusUniqueControllerPathId")
            self.assertEqual(context["clipJoinStatus"], "corpusUniqueAnimationClipPathId")
            self.assertEqual(context["assetIdentityToken"], "eny_0001_fixture")
            self.assertEqual(context["runtimeActivation"], "unobserved")

            # A missing base controller must remain partial rather than being
            # guessed from the override filename.
            payload = json.loads(
                (override_root / "AC_eny_0001_fixture_p0000000000000004.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["m_Controller"]["m_PathID"] = 99
            (override_root / "AC_eny_0001_fixture_p0000000000000004.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            partial = build_audio.collect_animation_override_index(export_root)
            self.assertEqual(partial["summary"]["status"], "partial")
            self.assertEqual(partial["summary"]["controllerPathIdUnresolved"], 1)
            self.assertEqual(
                partial["byClipPathId"][2][0]["controllerJoinStatus"],
                "missingControllerPathId",
            )

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

    def test_collects_owner_unresolved_exact_gameplay_config_audio_references(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            buff_root = export_root / "structured/Persistent/Data/Json/BuffData"
            skill_root.mkdir(parents=True)
            buff_root.mkdir(parents=True)
            (skill_root / "skill_orphan.json").write_bytes(
                self.memorypack_strings(47, "au_skill_orphan_exact")
            )
            (buff_root / "buff_orphan.json").write_bytes(
                self.memorypack_strings(30, "au_buff_orphan_exact")
            )

            result = build_audio.collect_gameplay_audio_references(
                webui_root,
                export_root,
                "CN",
            )

            references = {
                row["eventId"]: row
                for row in result["authoredConfigEventReferences"]
            }
            self.assertEqual(
                set(references),
                {"au_skill_orphan_exact", "au_buff_orphan_exact"},
            )
            self.assertEqual(references["au_skill_orphan_exact"]["configKind"], "SkillData")
            self.assertEqual(references["au_skill_orphan_exact"]["configId"], "skill_orphan")
            self.assertEqual(references["au_buff_orphan_exact"]["configKind"], "BuffData")
            self.assertEqual(references["au_buff_orphan_exact"]["ownerLinkStatus"], "unresolved")
            self.assertEqual(
                references["au_buff_orphan_exact"]["evidence"],
                "exactMemoryPackLengthPrefixedAudioEventString",
            )
            self.assertEqual(result["counts"]["authoredConfigEventReferences"], 2)
            self.assertEqual(result["counts"]["authoredConfigEventReferenceEvents"], 2)

    def test_exact_play_sound_event_seeds_buff_traversal_and_keeps_owner_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "character",
                "id": "chr_test",
                "skillGroups": [{"id": "normal", "skills": [{"id": "chr_test_normal"}]}],
            }]}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            buff_root = export_root / "structured/StreamingAssets/Data/Json/BuffData"
            skill_root.mkdir(parents=True)
            buff_root.mkdir(parents=True)
            # The generic inventory sees the BuffData dependency, but not the
            # typed PlaySoundActionData Event string supplied by the decoder.
            (skill_root / "chr_test_normal.json").write_bytes(
                self.memorypack_strings(47, "buff_test_timed")
            )
            (buff_root / "buff_test_timed.json").write_bytes(
                self.memorypack_strings(30, "buff_test_timed")
            )
            (buff_root / "buff_orphan.json").write_bytes(
                self.memorypack_strings(30, "buff_orphan")
            )
            linked_action = {
                "buffId": "buff_test_timed",
                "eventId": "au_test_timed",
                "timelineActionIndex": 0,
                "actionDataIndex": 0,
                "startFrame": 17,
                "endFrame": 34,
                "serverActionIndex": 9,
                "runtimeConditionStatus": "unresolved",
            }
            orphan_action = {
                "buffId": "buff_orphan",
                "eventId": "au_test_orphan",
                "timelineActionIndex": 0,
                "actionDataIndex": 0,
                "startFrame": 2,
                "endFrame": 8,
                "serverActionIndex": 10,
                "runtimeConditionStatus": "unresolved",
            }
            decoded = {
                "byBuffEvent": {
                    "buff_test_timed": {"au_test_timed": [linked_action]},
                    "buff_orphan": {"au_test_orphan": [orphan_action]},
                },
                "counts": {
                    "buffPlaySoundActionOccurrences": 2,
                    "buffPlaySoundUniqueEvents": 2,
                },
            }

            with mock.patch.object(
                build_audio,
                "collect_buff_play_sound_actions",
                return_value=decoded,
            ):
                result = build_audio.collect_gameplay_audio_references(
                    webui_root,
                    export_root,
                    "CN",
                )

            owner = next(row for row in result["owners"] if row["ownerKind"] == "character")
            self.assertEqual(set(owner["events"]), {"au_test_timed"})
            evidence = owner["events"]["au_test_timed"][0]
            self.assertEqual(evidence["buffIds"], ["buff_test_timed"])
            self.assertEqual(evidence["playSoundActions"][0]["startFrame"], 17)
            self.assertEqual(
                evidence["playSoundActions"][0]["runtimeConditionStatus"],
                "unresolved",
            )
            catalog = {row["eventId"]: row for row in result["authoredPlaySoundActions"]}
            self.assertEqual(
                catalog["au_test_timed"]["ownerLinkStatus"],
                "linkedThroughBuffDependency",
            )
            self.assertEqual(catalog["au_test_orphan"]["ownerLinkStatus"], "unresolved")
            self.assertEqual(result["counts"]["buffPlaySoundSeededEventRefs"], 2)
            self.assertEqual(
                result["counts"]["buffPlaySoundActionsLinkedToGameplayOwner"],
                1,
            )
            self.assertEqual(result["counts"]["buffPlaySoundActionsOwnerUnresolved"], 1)

    def test_exact_skill_play_sound_event_seeds_direct_skill_owner(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "character",
                "id": "chr_test",
                "skillGroups": [{"id": "normal", "skills": [{"id": "chr_test_normal"}]}],
            }]}), encoding="utf-8")
            skill_path = (
                export_root
                / "structured/StreamingAssets/Data/Json/SkillData/chr_test_normal.json"
            )
            skill_path.parent.mkdir(parents=True)
            skill_path.write_bytes(b"fixture-without-generic-au-prefix")
            skill_action = {
                "buffId": "chr_test_normal",
                "eventId": "eny_fixture_direct_event",
                "timelineActionIndex": 0,
                "actionDataIndex": 0,
                "startFrame": 4,
                "endFrame": 9,
                "serverActionIndex": 2,
                "runtimeConditionStatus": "unresolved",
            }
            skill_decoded = {
                "byBuffEvent": {
                    "chr_test_normal": {"eny_fixture_direct_event": [skill_action]},
                },
                "counts": {
                    "buffPlaySoundActionOccurrences": 1,
                    "buffPlaySoundUniqueEvents": 1,
                },
            }
            empty_decoded = {"byBuffEvent": {}, "counts": {}}

            with mock.patch.object(
                build_audio,
                "collect_buff_play_sound_actions",
                side_effect=[skill_decoded, empty_decoded],
            ):
                result = build_audio.collect_gameplay_audio_references(
                    webui_root,
                    export_root,
                    "CN",
                )

            owner = next(row for row in result["owners"] if row["ownerKind"] == "character")
            evidence = owner["events"]["eny_fixture_direct_event"][0]
            self.assertEqual(evidence["kind"], "skillData")
            self.assertEqual(evidence["playSoundActions"][0]["skillId"], "chr_test_normal")
            self.assertNotIn("buffId", evidence["playSoundActions"][0])
            self.assertEqual(result["counts"]["skillPlaySoundSeededEventRefs"], 1)
            self.assertEqual(result["counts"]["skillPlaySoundActionOccurrences"], 1)

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
                    "ownershipMethod": "gameplaySkillId",
                    "events": {"au_yes": [{"kind": "skillData"}], "au_no": [{"kind": "skillData"}]},
                }, {
                    "ownerKind": "enemy",
                    "ownerId": "eny_test",
                    "groupId": "",
                    "skillId": "eny_test_attack",
                    "confidence": "inferred",
                    "ownershipMethod": "enemyIdPrefix",
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
                "unownedAnimationEvents": {
                    "au_owner_unresolved": [{
                        "kind": "animationClipEvent",
                        "authoredEventId": "au_owner_unresolved",
                        "clip": "UI_Generic",
                        "clipSource": "AnimationClip/UI_Generic.anim",
                        "actionKind": "action",
                        "clipContext": "ui",
                        "function": "PostAudioEvent",
                        "time": 0.5,
                        "ownerStatus": "unresolved",
                    }],
                },
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
            self.assertEqual(stats["gameplaySerializedAudioRefs"], 5)
            self.assertEqual(stats["gameplayReferenceOnlyAudioRefs"], 1)
            self.assertEqual(stats["animationAudioRefsLinked"], 1)
            self.assertEqual(stats["profileVoiceRefsLinked"], 1)
            self.assertEqual([row["id"] for row in events], ["au_no", "au_yes"])
            unresolved, resolved = events
            self.assertFalse(unresolved["foundInWwise"])
            self.assertFalse(unresolved["hasPlayableMedia"])
            self.assertEqual(unresolved["runtimeSelection"], "eventNotFoundInWwise")
            self.assertEqual(resolved["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(resolved["triggerRelationTypes"], ["skillDataEventReference"])
            self.assertEqual(resolved["triggerBindings"][0]["ownershipMethod"], "gameplaySkillId")
            enemy = payload["enemies"]["eny_test"]
            self.assertEqual(enemy["ownershipConfidence"], "inferred")
            self.assertEqual(enemy["skillIds"], ["eny_test_attack"])
            self.assertEqual([row["id"] for row in enemy["events"]], ["au_yes"])
            self.assertEqual(enemy["events"][0]["triggerBindingStatus"], "inferredSkillConfigOwner")
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
            animation_evidence = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects_animation_evidence.json")
                .read_text(encoding="utf-8")
            )
            unresolved_animation = animation_evidence["ownerUnresolved"][0]
            self.assertEqual(unresolved_animation["id"], "au_owner_unresolved")
            self.assertEqual(unresolved_animation["ownerStatus"], "unresolved")
            self.assertEqual(unresolved_animation["animationClipContexts"], ["ui"])
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
                [{
                    "eventId": "player_fol_fs_walk",
                    "bankId": 100,
                    "bankVersion": 150,
                    "traversalStatus": "complete",
                    "rootStopActionCount": 1,
                    "actionDispatchEvidence": {
                        "timingClass": "coDispatchWithAuthoredDelayDifference",
                        "playbackActionCount": 2,
                        "typedPlaybackActionCount": 2,
                        "failedPlaybackActionCount": 0,
                        "multiPlayback": True,
                        "simultaneityCandidate": False,
                        "explicitDelayActionCount": 1,
                        "explicitTransitionActionCount": 0,
                        "probabilityGatedActionCount": 1,
                        "evidenceBoundary": "serialized membership only",
                    },
                    "actionEvidence": [{
                        "actionId": 101,
                        "eventActionOrdinal": 0,
                        "operation": "play",
                        "actionParserStatus": "typedExactV150",
                        "delay": {
                            "serializationStatus": "implicitDefaultNotSerialized",
                            "baseValuesMs": [],
                            "modifierRangesMs": [],
                        },
                        "transition": {},
                        "probability": {},
                    }, {
                        "actionId": 102,
                        "eventActionOrdinal": 1,
                        "operation": "play",
                        "actionParserStatus": "typedExactV150",
                        "delay": {
                            "serializationStatus": "explicitBase",
                            "baseValuesMs": [350],
                            "modifierRangesMs": [],
                        },
                        "transition": {},
                        "probability": {
                            "serializationStatus": "explicitBase",
                            "baseValuesPercent": [5.0],
                            "modifierRangesPercent": [],
                            "runtimeSelection": "actionGateNotEvaluated",
                        },
                    }, {
                        "actionId": 103,
                        "eventActionOrdinal": 2,
                        "operation": "stop",
                        "actionParserStatus": "unsupportedActionKind",
                    }],
                    "containerEvidence": [{
                        "objectId": 10,
                        "objectType": 5,
                        "mode": 0,
                        "childCount": 12,
                    }, {
                        "objectId": 20,
                        "objectType": 6,
                        "childCount": 4,
                    }, {
                        # The same node can be reached from more than one Play root;
                        # compact evidence counts the graph node only once.
                        "objectId": 20,
                        "objectType": 6,
                        "childCount": 4,
                    }],
                }],
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
            self.assertEqual(event_a["selectorEvidence"]["bankDefinitionCount"], 1)
            self.assertEqual(event_a["selectorEvidence"]["rootStopActionCount"], 1)
            self.assertEqual(event_a["selectorEvidence"]["containers"], {
                "randomAlternative": {"nodeCount": 1, "childEdgeCount": 12},
                "switchCandidate": {"nodeCount": 1, "childEdgeCount": 4},
            })
            self.assertEqual(payload["schemaVersion"], 5)
            dispatch = event_a["actionDispatchEvidence"][0]
            self.assertEqual(dispatch["bankId"], 100)
            self.assertEqual(dispatch["bankVersion"], 150)
            self.assertEqual(dispatch["timingClass"], "coDispatchWithAuthoredDelayDifference")
            self.assertEqual(dispatch["playbackActionCount"], 2)
            self.assertEqual(dispatch["explicitDelayActionCount"], 1)
            self.assertEqual(dispatch["probabilityGatedActionCount"], 1)
            self.assertEqual([row["actionId"] for row in dispatch["actions"]], [101, 102])
            self.assertEqual(dispatch["actions"][1]["delay"]["baseValuesMs"], [350])
            self.assertEqual(dispatch["actions"][1]["probability"]["baseValuesPercent"], [5.0])
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

    def test_exact_and_inferred_trigger_statuses_remain_per_event(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            references = {
                "eventNames": {"au_exact", "au_inferred"},
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal",
                    "confidence": "direct",
                    "ownershipMethod": "gameplaySkillId",
                    "sources": ["SkillData/chr_test_normal.json"],
                    "events": {"au_exact": [{"kind": "skillData", "skillId": "chr_test_normal"}]},
                }, {
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal_followup",
                    "confidence": "inferred",
                    "ownershipMethod": "playableSkillFamilyPrefix",
                    "sources": ["SkillData/chr_test_normal_followup.json"],
                    "events": {"au_inferred": [{"kind": "skillBuffData", "buffIds": ["buff_followup"]}]},
                }],
                "animationOwners": [],
                "profileVoiceOwners": [],
                "counts": {},
            }
            build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {
                    "au_exact": [{"src": "data/audio/shared/exact.wav", "mediaId": 1}],
                    "au_inferred": [{"src": "data/audio/shared/inferred.wav", "mediaId": 2}],
                },
                [{"eventId": "au_exact"}, {"eventId": "au_inferred"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8")
            )
            group = payload["characters"]["chr_test"]["groups"]["normal"]
            events = {event["id"]: event for event in group["events"]}
            self.assertEqual(group["ownershipConfidence"], "inferred")
            self.assertEqual(events["au_exact"]["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(events["au_exact"]["triggerBindings"][0]["requestEvidence"], "exactAuthoredDependency")
            self.assertEqual(events["au_exact"]["triggerBindings"][0]["runtimeActivationStatus"], "conditionAndTimingUnresolved")
            self.assertEqual(events["au_inferred"]["triggerBindingStatus"], "inferredSkillConfigOwner")
            self.assertEqual(events["au_inferred"]["triggerRelationTypes"], ["skillBuffChain"])
            self.assertEqual(events["au_inferred"]["triggerBindings"][0]["buffIds"], ["buff_followup"])
            self.assertEqual(group.get("skillIds"), ["chr_test_normal", "chr_test_normal_followup"])
            self.assertEqual(payload["characters"]["chr_test"]["metrics"]["exactSkillTriggerEventCount"], 1)
            self.assertEqual(payload["characters"]["chr_test"]["metrics"]["inferredSkillTriggerEventCount"], 1)
            self.assertEqual(payload["counts"]["exactSkillConfigTriggerRefs"], 1)
            self.assertEqual(payload["counts"]["inferredSkillConfigOwnerRefs"], 1)

    def test_play_sound_action_binding_preserves_frame_window_and_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            play_sound = {
                "buffId": "buff_test_timed",
                "eventId": "au_exact_timed",
                "startFrame": 17,
                "endFrame": 34,
                "stopOnEnd": True,
                "stopFadeDurationMs": 300,
                "targetSettingsStatus": "partial-target-settings-envelope-opaque",
                "targetSelector": "smart_target",
                "sourcePaths": ["structured/StreamingAssets/Data/Json/BuffData/buff_test_timed.json"],
                "runtimeConditionStatus": "unresolved",
            }
            references = {
                "eventNames": {"au_exact_timed"},
                "authoredPlaySoundActions": [play_sound],
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal",
                    "confidence": "direct",
                    "ownershipMethod": "gameplaySkillId",
                    "sources": ["SkillData/chr_test_normal.json"],
                    "events": {"au_exact_timed": [{
                        "kind": "skillBuffData",
                        "skillId": "chr_test_normal",
                        "buffIds": ["buff_test_timed"],
                        "playSoundActions": [play_sound],
                    }]},
                }],
                "animationOwners": [],
                "profileVoiceOwners": [],
                "counts": {},
            }
            build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"au_exact_timed": [{"src": "data/audio/shared/timed.wav", "mediaId": 3}]},
                [{"eventId": "au_exact_timed"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["schemaVersion"], 5)
            self.assertEqual(payload["authoredPlaySoundActions"][0]["startFrame"], 17)
            event = payload["characters"]["chr_test"]["groups"]["normal"]["events"][0]
            binding = event["triggerBindings"][0]
            self.assertEqual(event["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(event["triggerRelationTypes"], ["buffPlaySoundAction", "skillBuffChain"])
            self.assertEqual(binding["requestEvidence"], "exactAuthoredPlaySoundAction")
            self.assertEqual(
                binding["runtimeActivationStatus"],
                "authoredFrameWindowRecoveredConditionUnresolved",
            )
            self.assertEqual(binding["playSoundActions"][0]["startFrame"], 17)
            self.assertEqual(binding["playSoundActions"][0]["endFrame"], 34)
            self.assertTrue(binding["playSoundActions"][0]["stopOnEnd"])
            self.assertTrue(any(path.endswith("buff_test_timed.json") for path in binding["sourcePaths"]))


if __name__ == "__main__":
    unittest.main()
