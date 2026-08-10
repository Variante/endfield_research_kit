import struct
import unittest

from scripts.story_builder.level_bindings import levelscript_native_action_name
from scripts.story_builder.levelscript_binary import (
    LEVELSCRIPT_NATIVE_AUDIO_ACTION_MAPPING_ID,
    decode_levelscript_record_payload,
)


DEFAULT_TAIL = struct.pack("<iii", -1, 0, -1)


def param_tail(*, id_ref: int = -1, source: int = 0, path: str | None = None) -> bytes:
    raw_path = path.encode("utf-8") if path is not None else b""
    return struct.pack("<iii", id_ref, source, len(raw_path) if path is not None else -1) + raw_path


def string_param(
    value: str | None,
    *,
    id_ref: int = -1,
    source: int = 0,
    path: str | None = None,
) -> bytes:
    raw = value.encode("utf-8") if value is not None else b""
    size = len(raw) if value is not None else -1
    return b"\x04" + struct.pack("<i", size) + raw + param_tail(
        id_ref=id_ref,
        source=source,
        path=path,
    )


def i32_param(
    value: int,
    *,
    id_ref: int = -1,
    source: int = 0,
    path: str | None = None,
) -> bytes:
    return b"\x04" + struct.pack("<i", value) + param_tail(
        id_ref=id_ref,
        source=source,
        path=path,
    )


def float_param(value: float) -> bytes:
    return b"\x04" + struct.pack("<f", value) + DEFAULT_TAIL


def bool_param(value: bool) -> bytes:
    return b"\x04" + bytes([int(value)]) + DEFAULT_TAIL


def vector3_param(
    x: float,
    y: float,
    z: float,
    *,
    id_ref: int = -1,
    source: int = 0,
) -> bytes:
    return b"\x04" + struct.pack("<fff", x, y, z) + param_tail(
        id_ref=id_ref,
        source=source,
    )


def quaternion_param(x: float, y: float, z: float, w: float) -> bytes:
    return b"\x04" + struct.pack("<ffff", x, y, z, w) + DEFAULT_TAIL


def entity_param(logic_id: int, slot_id: int, use_slot_id: bool) -> bytes:
    return (
        b"\x04\x03"
        + struct.pack("<QI", logic_id, slot_id)
        + bytes([int(use_slot_id)])
        + DEFAULT_TAIL
    )


def output_param(path: str, *, source: int = 0) -> bytes:
    raw = path.encode("utf-8")
    return b"\x02" + struct.pack("<ii", source, len(raw)) + raw


def decode_audio(
    payload: bytes,
    tag: int,
    member_count: int,
    *,
    action_map_role: str = "actionList#1 root",
) -> dict:
    source = payload if payload else b"\x00"
    payload_start = len(source) if not payload else 0
    record = {
        "start": 0,
        "payloadStart": payload_start,
        "code": tag,
        "kind": member_count,
        "unionTag": tag,
        "serializedMemberCount": member_count,
    }
    return decode_levelscript_record_payload(
        source,
        record,
        next_start=len(source),
        action_map_role=action_map_role,
    ).get("audioAction") or {}


class LevelScriptAudioActionTests(unittest.TestCase):
    def test_audio_formatter_tag_collision_requires_action_list_membership(self) -> None:
        valid = (
            bytes.fromhex("ff ff 00 00 00 00 ff ff ff ff")
            + string_param("au_int_example")
        )
        self.assertEqual(
            "AnnounceAudioOnTarget",
            decode_audio(valid, 0x0016, 0x09)["action"],
        )
        self.assertEqual(
            {},
            decode_audio(
                valid,
                0x0016,
                0x09,
                action_map_role="getterList#1",
            ),
        )

    def test_zero_field_audio_controls_decode_with_bounded_list_framing(self) -> None:
        for tag, name in (
            (0x00B7, "ExitCustomMusicMode"),
            (0x00E9, "FlushRadio"),
            (0x0372, "PostAudioStopAllEnemyVoice"),
        ):
            action = decode_audio(b"", tag, 0x08)
            self.assertEqual(name, action["action"])
            self.assertEqual({}, action.get("fields", {}))
            self.assertEqual([], action.get("eventBindings", []))
            self.assertEqual([], action.get("cueBindings", []))
            self.assertEqual([], action.get("radioBindings", []))

            framed = decode_audio(struct.pack("<II", 0, 2), tag, 0x08)
            self.assertEqual([0, 2], framed["trailingActionMapFramingU32s"])

    def test_zero_field_audio_controls_reject_non_framing_payload(self) -> None:
        self.assertEqual({}, decode_audio(b"\x01\x00\x00\x00\x02", 0x00B7, 0x08))

    def test_current_binary_voice_and_music_control_layouts_decode_exactly(self) -> None:
        announce = decode_audio(
            bytes.fromhex("ff ff 00 00 00 00 ff ff ff ff")
            + string_param("e1m10_q#18"),
            0x0016,
            0x09,
        )
        self.assertEqual("AnnounceAudioOnTarget", announce["action"])
        self.assertEqual(
            "announce-target-compact-null-reference",
            announce["fields"]["target"]["serializedShape"],
        )
        self.assertEqual("opaque", announce["fields"]["target"]["bindingKind"])
        self.assertEqual("announceTarget", announce["eventBindings"][0]["role"])

        block = decode_audio(output_param("$64@_blockHandle"), 0x0028, 0x09)
        self.assertEqual("BlockAutoMusicChange", block["action"])
        self.assertEqual("output", block["fields"]["blockHandle"]["bindingKind"])

        cancel = decode_audio(
            i32_param(0, source=100, path="$32@_blockHandle"),
            0x0029,
            0x09,
        )
        self.assertEqual("BlockAutoMusicChangeCancel", cancel["action"])
        self.assertEqual("dynamic", cancel["fields"]["blockHandle"]["bindingKind"])

        battle = decode_audio(bool_param(False), 0x002A, 0x09)
        self.assertEqual("BlockBattleMusic", battle["action"])
        self.assertFalse(battle["fields"]["block"]["value"])

        custom = decode_audio(
            bool_param(False)
            + string_param("au_music_activity_bomb")
            + bool_param(True),
            0x0089,
            0x0B,
        )
        self.assertEqual("EnterCustomMusicMode", custom["action"])
        self.assertEqual("customMusic", custom["eventBindings"][0]["role"])

        voice = decode_audio(
            entity_param(0, 40001, True)
            + output_param("$1@_voiceHandle")
            + string_param("au_prts_tape0003_stem_broken"),
            0x0368,
            0x0B,
        )
        self.assertEqual("PlayVoice", voice["action"])
        self.assertEqual(40001, voice["fields"]["target"]["slotId"])
        self.assertEqual("voice", voice["eventBindings"][0]["role"])

        narrative = decode_audio(
            output_param("$41@_voiceHandle")
            + string_param("au_efos_gmmode_training_end"),
            0x0369,
            0x0A,
        )
        self.assertEqual("PlayVoiceNarrative", narrative["action"])
        self.assertEqual("voiceNarrative", narrative["eventBindings"][0]["role"])

        cue_release = decode_audio(
            b"".join((
                i32_param(2),
                bool_param(True),
                bool_param(False),
                bool_param(True),
                output_param("$12@_cueHandlerId"),
                b"\xff",
                b"\xff",
                string_param("battle_music_start"),
                b"\xff",
                b"\xff",
                float_param(10.0),
                bool_param(False),
            )),
            0x036E,
            0x14,
        )
        self.assertEqual("PostAudioCueOnRelease", cue_release["action"])
        self.assertEqual("battle_music_start", cue_release["cueBindings"][0]["cueName"])
        self.assertFalse(cue_release["fields"]["onlyIfExecuted"]["value"])

    def test_current_binary_audio_layouts_fail_closed_on_wrong_shape(self) -> None:
        compact_target = bytes.fromhex("ff ff 00 00 00 00 ff ff ff ff")
        self.assertFalse(
            decode_audio(b"\xff" + compact_target + string_param("bad"), 0x0016, 0x09)
        )
        self.assertFalse(
            decode_audio(bool_param(False) + string_param("music"), 0x0089, 0x0B)
        )
        self.assertFalse(
            decode_audio(
                output_param("$1@_voiceHandle")
                + entity_param(0, 40001, True)
                + string_param("voice"),
                0x0368,
                0x0B,
            )
        )

    def test_play_audio_preserves_constant_dynamic_and_output_evidence(self) -> None:
        constant_payload = b"".join((
            output_param("$5@_audioPlayingId"),
            string_param("au_music_test"),
            bool_param(True),
        ))
        constant = decode_audio(constant_payload, 0x034E, 0x0B)
        self.assertEqual("PlayAudio", constant["action"])
        self.assertEqual(
            [{"eventName": "au_music_test", "role": "play", "sourceField": "_key"}],
            constant["eventBindings"],
        )
        self.assertEqual("output", constant["fields"]["audioPlayingId"]["bindingKind"])
        self.assertTrue(constant["fields"]["stopOnRelease"]["value"])
        self.assertEqual(LEVELSCRIPT_NATIVE_AUDIO_ACTION_MAPPING_ID, constant["nativeMappingId"])

        dynamic_payload = b"".join((
            output_param("$5@_audioPlayingId"),
            string_param("au_not_a_literal", id_ref=31, source=-1),
            bool_param(False),
        ))
        dynamic = decode_audio(dynamic_payload, 0x034E, 0x0B)
        self.assertEqual("dynamic", dynamic["fields"]["key"]["bindingKind"])
        self.assertEqual(31, dynamic["fields"]["key"]["idRef"])
        self.assertEqual(-1, dynamic["fields"]["key"]["paramSource"])
        self.assertNotIn("eventBindings", dynamic)

    def test_position_target_and_wait_layouts_decode_to_exact_field_boundary(self) -> None:
        at_position = decode_audio(b"".join((
            output_param("$11@_audioPlayingId"),
            string_param("au_int_break"),
            vector3_param(338.87, 29.83, 318.1),
            bool_param(True),
        )), 0x034C, 0x0C)
        self.assertEqual("PlayAudiAtPosition", at_position["action"])
        self.assertAlmostEqual(338.87, at_position["fields"]["position"]["value"]["x"], places=2)
        self.assertTrue(at_position["fields"]["stopOnRelease"]["value"])

        on_target = decode_audio(b"".join((
            string_param("au_enemy_mute"),
            output_param("$8@_audioPlayingId"),
            bool_param(True),
            entity_param(0x2D3A7F, 2, False),
        )), 0x0352, 0x0C)
        self.assertEqual("PlayAudioOnTarget", on_target["action"])
        self.assertEqual(0x2D3A7F, on_target["fields"]["target"]["logicId"])
        self.assertEqual(2, on_target["fields"]["target"]["slotId"])

        play_wait = decode_audio(b"".join((
            string_param("au_radio_test"),
            float_param(0.9),
            output_param("$9@_playingId"),
            i32_param(3),
            vector3_param(296.9, 286.3, -399.1),
            bool_param(True),
            entity_param(0, 0, False),
            string_param("npc_proxy_test"),
        )), 0x034F, 0x10)
        self.assertEqual("PlayAudioAndWait", play_wait["action"])
        self.assertEqual(3, play_wait["fields"]["playType"]["value"])
        self.assertEqual("npc_proxy_test", play_wait["fields"]["targetProxy"]["value"])
        self.assertEqual(len(b"".join((
            string_param("au_radio_test"), float_param(0.9), output_param("$9@_playingId"),
            i32_param(3), vector3_param(296.9, 286.3, -399.1), bool_param(True),
            entity_param(0, 0, False), string_param("npc_proxy_test"),
        ))), play_wait["consumedBytes"])

    def test_radio_play_wait_stop_and_toggle_layouts_preserve_roles(self) -> None:
        play_payload = b"".join((
            bool_param(True),
            i32_param(-1),
            bool_param(False),
            bool_param(False),
            string_param("radio_e0m2_1"),
            struct.pack("<I", 2),
        ))
        play = decode_audio(play_payload, 0x0363, 0x0D)
        self.assertEqual("PlayRadio", play["action"])
        self.assertEqual(
            [{"radioId": "radio_e0m2_1", "role": "play", "sourceField": "_radioId"}],
            play["radioBindings"],
        )
        self.assertTrue(play["fields"]["fromBegin"]["value"])
        self.assertEqual(-1, play["fields"]["index"]["value"])
        self.assertEqual([2], play["trailingActionMapFramingU32s"])

        wait = decode_audio(b"".join((
            bool_param(True),
            i32_param(-1),
            bool_param(False),
            bool_param(False),
            string_param("radio_c16m4_16"),
        )), 0x0364, 0x0D)
        self.assertEqual("PlayRadioAndWait", wait["action"])
        self.assertEqual("playAndWait", wait["radioBindings"][0]["role"])

        stop = decode_audio(string_param("radio_sm1l1m1_5"), 0x04B5, 0x09)
        self.assertEqual("StopRadio", stop["action"])
        self.assertEqual("stop", stop["radioBindings"][0]["role"])

        toggle = decode_audio(
            bool_param(False) + struct.pack("<II", 0, 1),
            0x04CA,
            0x09,
        )
        self.assertEqual("ToggleClearScreenButRadio", toggle["action"])
        self.assertFalse(toggle["fields"]["isShow"]["value"])
        self.assertNotIn("radioBindings", toggle)

    def test_3d_radio_and_wait_share_the_exact_inherited_twelve_fields(self) -> None:
        def payload(radio_id: str) -> bytes:
            return b"".join((
                i32_param(36),
                bool_param(False),
                entity_param(24300010036, 0, False),
                bool_param(True),
                i32_param(-1),
                bool_param(False),
                b"\xff",
                bool_param(False),
                string_param(radio_id),
                float_param(1.0),
                bool_param(False),
                float_param(1.0),
            ))

        play = decode_audio(payload("radio_c17m3_39"), 0x034A, 0x14)
        self.assertEqual("Play3DRadio", play["action"])
        self.assertEqual("play3D", play["radioBindings"][0]["role"])
        self.assertEqual(24300010036, play["fields"]["entityPtr"]["logicId"])
        self.assertFalse(play["fields"]["npcProxyId"]["present"])

        wait = decode_audio(
            payload("radio_e9m2_42") + struct.pack("<II", 0, 2),
            0x034B,
            0x14,
        )
        self.assertEqual("Play3DRadioAndWait", wait["action"])
        self.assertEqual("play3DAndWait", wait["radioBindings"][0]["role"])
        self.assertEqual([0, 2], wait["trailingActionMapFramingU32s"])

        # The same union tag with member count 9 is a getter-list record in
        # the current corpus, not the 20-member Play3DRadio formatter.
        self.assertFalse(decode_audio(payload("radio_false_positive"), 0x034A, 0x09))

    def test_dynamic_radio_ids_remain_evidence_without_literal_bindings(self) -> None:
        dynamic = decode_audio(b"".join((
            bool_param(True),
            i32_param(-1),
            bool_param(False),
            bool_param(False),
            string_param(None, id_ref=1, source=-1),
        )), 0x0363, 0x0D)
        self.assertEqual("dynamic", dynamic["fields"]["radioId"]["bindingKind"])
        self.assertEqual(1, dynamic["fields"]["radioId"]["idRef"])
        self.assertNotIn("radioBindings", dynamic)
        self.assertFalse(decode_audio(b"\x04", 0x04B5, 0x09))

    def test_status_music_and_cue_bindings_keep_lifecycle_roles_separate(self) -> None:
        status = decode_audio(b"".join((
            bool_param(True),
            string_param("au_state_enter"),
            string_param("au_state_exit"),
        )), 0x0371, 0x0B)
        self.assertEqual(
            [("statusEnter", "au_state_enter"), ("statusExit", "au_state_exit")],
            [(row["role"], row["eventName"]) for row in status["eventBindings"]],
        )

        music = decode_audio(b"".join((
            string_param("au_music_start"),
            string_param("au_music_stop"),
            i32_param(2),
            output_param("$38@_playingId"),
        )), 0x0373, 0x0C)
        self.assertEqual("PostMusicEvent", music["action"])
        self.assertEqual(["post", "release"], [row["role"] for row in music["eventBindings"]])
        self.assertEqual(2, music["fields"]["musicEventType"]["value"])

        cue = decode_audio(b"".join((
            i32_param(2),
            bool_param(True),
            bool_param(False),
            bool_param(True),
            output_param("$12@_cueHandlerId"),
            b"\xff",
            b"\xff",
            string_param("battle_music_start"),
            b"\xff",
            b"\xff",
            float_param(10.0),
        )), 0x036B, 0x13)
        self.assertEqual("PostAudioCue", cue["action"])
        self.assertEqual(
            [{"cueName": "battle_music_start", "role": "invoke", "sourceField": "_name"}],
            cue["cueBindings"],
        )
        self.assertFalse(cue["fields"]["floatParam"]["present"])
        self.assertEqual("null", cue["fields"]["floatParam"]["bindingKind"])

    def test_manual_and_standalone_music_controls_decode_exact_fields(self) -> None:
        restore = decode_audio(float_param(1.0) + struct.pack("<I", 1), 0x0306, 0x09)
        self.assertEqual("ManualRestoreMusicState", restore["action"])
        self.assertEqual(1.0, restore["fields"]["delay"]["value"])
        self.assertEqual([1], restore["trailingActionMapFramingU32s"])

        manual = decode_audio(b"".join((
            i32_param(2),
            i32_param(2),
            i32_param(1),
        )), 0x0307, 0x0B)
        self.assertEqual("ManualSetMusicState", manual["action"])
        self.assertEqual(2, manual["fields"]["baseState"]["value"])
        self.assertEqual(2, manual["fields"]["battleIntensityState"]["value"])
        self.assertEqual(1, manual["fields"]["battleState"]["value"])

        standalone = decode_audio(b"".join((
            output_param("$2@_handleId"),
            i32_param(1),
            i32_param(3),
            vector3_param(-78.21, 4.2, 7.7),
            quaternion_param(0.0, 0.0, 0.0, 1.0),
            vector3_param(62.06, 20.55, 87.69),
            string_param("au_music_standalone_start"),
            string_param("au_music_standalone_stop"),
            bool_param(True),
            struct.pack("<II", 0, 1),
        )), 0x0367, 0x11)
        self.assertEqual("PlayStandaloneMusic", standalone["action"])
        self.assertEqual(1.0, standalone["fields"]["rotation"]["value"]["w"])
        self.assertEqual(
            ["standaloneStart", "standaloneStop"],
            [binding["role"] for binding in standalone["eventBindings"]],
        )

    def test_cue_variable_and_placeholder_music_controls_preserve_null_params(self) -> None:
        cue_var = decode_audio(b"".join((
            bool_param(True),
            b"\xff",
            b"\xff",
            i32_param(0),
            b"\xff",
            string_param("au_trigger_music_test"),
            i32_param(0),
        )), 0x03D5, 0x0F)
        self.assertEqual("SetAudioCueVar", cue_var["action"])
        self.assertEqual("au_trigger_music_test", cue_var["fields"]["varName"]["value"])
        self.assertFalse(cue_var["fields"]["floatValue"]["present"])
        self.assertEqual(0, cue_var["fields"]["scope"]["value"])

        start = decode_audio(b"".join((
            i32_param(28),
            i32_param(0),
            float_param(7.0),
            bool_param(False),
            bool_param(True),
            float_param(10.0),
        )), 0x04A7, 0x0E)
        self.assertEqual("StartPlaceholderMusic_DevOnly", start["action"])
        self.assertEqual(28, start["fields"]["musicId"]["value"])
        self.assertEqual(10.0, start["fields"]["volume"]["value"])

        stop = decode_audio(b"".join((
            float_param(1.0),
            i32_param(0),
            bool_param(False),
        )), 0x04B4, 0x0B)
        self.assertEqual("StopPlaceholderMusic_DevOnly", stop["action"])
        self.assertEqual(1.0, stop["fields"]["fadeOutTimeSeconds"]["value"])

    def test_stop_and_switch_controls_preserve_dynamic_handles_and_targets(self) -> None:
        stop_audio = decode_audio(b"".join((
            i32_param(0, source=100, path="$28@_audioPlayingId"),
            i32_param(100, source=100),
        )), 0x04AC, 0x0A)
        self.assertEqual("StopAudio", stop_audio["action"])
        self.assertEqual("dynamic", stop_audio["fields"]["audioId"]["bindingKind"])
        self.assertEqual("$28@_audioPlayingId", stop_audio["fields"]["audioId"]["path"])

        stop_voice = decode_audio(b"".join((
            i32_param(100),
            i32_param(0, source=100, path="$1@_voiceHandle"),
            struct.pack("<II", 0, 2),
        )), 0x04B7, 0x0A)
        self.assertEqual("StopVoice", stop_voice["action"])
        self.assertEqual("dynamic", stop_voice["fields"]["voiceHandle"]["bindingKind"])

        bark = decode_audio(bool_param(False), 0x04BA, 0x09)
        self.assertEqual("SwitchAIBarkEnable", bark["action"])
        self.assertFalse(bark["fields"]["enable"]["value"])

        state = decode_audio(b"".join((
            i32_param(0),
            entity_param(0, 40003, True),
            i32_param(1),
        )), 0x04BC, 0x0B)
        self.assertEqual("SwitchAudioState", state["action"])
        self.assertEqual(40003, state["fields"]["target"]["slotId"])
        self.assertEqual(1, state["fields"]["value"]["value"])

        # The type exists in metadata, but no current LevelScript row proves
        # its serialized field shape, so it remains deliberately unsupported.
        self.assertFalse(decode_audio(string_param("rtpc") + float_param(1.0) + i32_param(100), 0x03D6, 0x0B))

    def test_exact_guards_reject_unknown_member_count_and_malformed_suffix(self) -> None:
        payload = b"".join((
            output_param("$5@_audioPlayingId"),
            string_param("au_music_test"),
            bool_param(True),
        ))
        self.assertFalse(decode_audio(payload, 0x034E, 0x0A))
        self.assertFalse(decode_audio(payload + b"\x01", 0x034E, 0x0B))

        framed = decode_audio(payload + struct.pack("<II", 0, 3), 0x034E, 0x0B)
        self.assertEqual([0, 3], framed["trailingActionMapFramingU32s"])

    def test_new_action_names_use_exact_union_and_member_count(self) -> None:
        for tag, count, name in (
            (0x034F, 0x10, "PlayAudioAndWait"),
            (0x0371, 0x0B, "PostAudioStatusEvent"),
            (0x034A, 0x14, "Play3DRadio"),
            (0x034B, 0x14, "Play3DRadioAndWait"),
            (0x0363, 0x0D, "PlayRadio"),
            (0x0364, 0x0D, "PlayRadioAndWait"),
            (0x04B5, 0x09, "StopRadio"),
            (0x04CA, 0x09, "ToggleClearScreenButRadio"),
        ):
            record = {
                "code": tag,
                "kind": count,
                "unionTag": tag,
                "serializedMemberCount": count,
            }
            self.assertEqual(name, levelscript_native_action_name(record))


if __name__ == "__main__":
    unittest.main()
