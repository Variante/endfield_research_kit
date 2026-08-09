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


def i32_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + DEFAULT_TAIL


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


def decode_audio(payload: bytes, tag: int, member_count: int) -> dict:
    record = {
        "start": 0,
        "payloadStart": 0,
        "code": tag,
        "kind": member_count,
        "unionTag": tag,
        "serializedMemberCount": member_count,
    }
    return decode_levelscript_record_payload(
        payload,
        record,
        next_start=len(payload),
        action_map_role="actionList#1 root",
    ).get("audioAction") or {}


class LevelScriptAudioActionTests(unittest.TestCase):
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
