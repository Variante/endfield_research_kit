import importlib.util
import math
import unittest
from pathlib import Path
from struct import pack, unpack


SCRIPT = Path(__file__).resolve().parents[1] / "story_builder/interactive_binary.py"
SPEC = importlib.util.spec_from_file_location("interactive_binary_test", SCRIPT)
interactive_binary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(interactive_binary)


def mp_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return pack("<I", len(encoded)) + encoded


PHYSICS_VALUES = {
    "need_track_movement": True,
    "on_hit_acceleration_sqr_threshold": 9.0,
    "on_start_move_audio_event": "au_int_kickable_ball_start",
    "on_stop_move_audio_event": "au_int_kickable_ball_stop",
    "on_hit_audio_event": "au_int_kickable_ball_hit",
    "on_hit_max_player_per_move": -1,
    "on_hit_min_interval_time": 0.3,
    "velocity_sqr_rtpc": "rtpc_int_kickable_ball_speed",
    "acceleration_sqr_rtpc": "",
    "need_track_rotation": True,
    "on_rotation_loop_audio_event": "",
    "on_rotation_loop_start_angular_velocity_sqr": 19.73921,
    "on_rotation_loop_end_angular_velocity_sqr": 11.843527,
    "on_rotation_one_shot_audio_event": "au_int_kickable_ball_rolling_scatter",
    "on_rotation_one_shot_trigger_ratio": 1.0,
    "on_rotation_ground_loop_audio_event": "au_int_kickable_ball_rolling_loop",
    "on_rotation_ground_loop_start_angular_velocity_sqr": 19.73921,
    "on_rotation_ground_loop_end_angular_velocity_sqr": 11.843527,
    "on_rotation_ground_one_shot_audio_event": "au_int_kickable_ball_rolling_ground",
    "on_rotation_ground_one_shot_trigger_audio_event": 1.0,
    "angular_velocity_sqr_rtpc": "",
}


def property_bits(value_type: int, value: object) -> int:
    if value_type == interactive_binary.PROPERTY_BOOL:
        return int(bool(value))
    if value_type == interactive_binary.PROPERTY_INT32:
        return int(value)
    if value_type == interactive_binary.PROPERTY_FLOAT:
        return unpack("<I", pack("<f", float(value)))[0]
    return 0


def physics_component_fixture() -> bytes:
    rows = []
    for schema in interactive_binary.PHYSICS_AUDIO_PROPERTIES:
        key = schema["authoredKey"]
        value_type = schema["valueType"]
        value = PHYSICS_VALUES[key]
        tail = mp_string(str(value)) if value_type == interactive_binary.PROPERTY_STRING else pack("<i", -1)
        rows.append(
            b"\x02"
            + mp_string(key)
            + b"\x02"
            + pack("<iI", value_type, 1)
            + b"\x02"
            + pack("<q", property_bits(value_type, value))
            + tail
        )
    return (
        bytes((interactive_binary.PHYSICS_AUDIO_COMPONENT_TAG, 1))
        + pack("<I", len(rows))
        + b"".join(rows)
    )


def interactive_table_fixture() -> bytes:
    core = [("int_kickable_ball", "Data/Json/Interactive/InteractiveData/data_int_kickable_ball.json")]
    consumers = [
        ("int_kickable_ball", "int_kickable_ball"),
        ("int_tumble_weed", "int_kickable_ball"),
    ]
    return (
        b"\x02"
        + pack("<I", len(core))
        + b"".join(mp_string(key) + mp_string(value) for key, value in core)
        + pack("<I", len(consumers))
        + b"".join(mp_string(key) + b"\x01" + mp_string(value) for key, value in consumers)
    )


def model_view_behavior(tag: int, behavior_type: int, body: bytes = b"") -> bytes:
    member_count = interactive_binary.MODEL_VIEW_BEHAVIOR_LAYOUTS[tag][0]
    base = b"\x00\x01\x00" + pack("<fii", 0.25, 2, behavior_type)
    return bytes((tag, member_count)) + base + body


def model_view_camera_behavior() -> bytes:
    curve = b"\x03" + pack("<iii", 1, 2, 3)
    envelope = (
        b"\x07\xff"
        + pack("<f", 0.1)
        + curve
        + pack("<f", 0.2)
        + b"\x00\x01"
        + pack("<f", 0.3)
    )
    impulse = (
        b"\x12"
        + pack("<f", 1.0)
        + b"\x00"
        + curve
        + pack("<ifi", 0, 10.0, 1)
        + pack("<fff", 0.5, 1.0, 2.0)
        + pack("<ifii", 1, 0.75, 2, 3)
        + pack("<f", 100.0)
        + b"\x01"
        + mp_string("camera/raw_signal")
        + pack("<i", 0)
        + envelope
    )
    return model_view_behavior(
        6,
        14,
        impulse
        + mp_string("CameraPoint")
        + pack("<fffq", 0.0, 1.0, 2.0, 123456)
        + b"\x00\x01",
    )


def model_view_controller_fixture() -> bytes:
    event = model_view_behavior(
        1,
        1,
        mp_string("audio_node")
        + mp_string("")
        + pack("<i", 1)
        + b"\x00\x01"
        + pack("<i", -9606891)
        + b"\x01"
        + pack("<i", 200),
    )
    position = model_view_behavior(
        2,
        8,
        mp_string("position_node")
        + mp_string("")
        + pack("<i", 2)
        + b"\x00\x01"
        + pack("<i", 1348303159)
        + b"\x00"
        + pack("<i", 300),
    )
    rtpc = model_view_behavior(
        3,
        9,
        mp_string("rtpc_node")
        + pack("<f", 0.5)
        + mp_string("au_rtpc_int_delta_progress")
        + pack("<i", 2)
        + b"\x01\x01"
        + mp_string("Progress"),
    )
    spatial = model_view_behavior(
        4,
        13,
        b"\x00\x01" + mp_string("Progress") + b"\x01" + pack("<ff", 0.75, 1.5),
    )
    non_audio = model_view_behavior(7, 10)
    behaviors = [event, position, rtpc, spatial, non_audio, model_view_camera_behavior()]
    state = (
        b"\x12"
        + pack("<II", 0xFFFFFFFF, 0xFFFFFFFF)
        + pack("<I", len(behaviors))
        + b"".join(behaviors)
        + pack("<I", 0xFFFFFFFF)
        + b"\x00\x00\x01\x01\x00\x01\x00"
        + pack("<ff", 0.1, 1.0)
        + pack("<I", 0xFFFFFFFF)
        + mp_string("Rotating")
        + pack("<ifI", 4, 2.0, 0xFFFFFFFF)
    )
    layer = b"\x05\x01" + pack("<i", 3) + mp_string("audioLayer") + pack("<I", 1) + state + pack("<f", 1.0)
    model = b"\x02" + pack("<I", 1) + layer + mp_string("P_fixture_model")
    return (
        b"\x07"
        + pack("<IIII", 0, 0, 0, 0)
        + pack("<I", 1)
        + model
        + mp_string("fixture_controller")
        + b"\x01"
    )


class InteractiveBinaryTests(unittest.TestCase):
    def test_decodes_complete_model_view_graph_and_four_audio_unions(self) -> None:
        fixture = model_view_controller_fixture()

        decoded = interactive_binary.decode_model_view_state_controller(fixture)

        self.assertEqual(decoded["endOffset"], len(fixture))
        self.assertEqual(decoded["modelId"], "fixture_controller")
        self.assertEqual(decoded["behaviorCount"], 6)
        self.assertEqual(decoded["audioBehaviorCount"], 4)
        self.assertEqual([row["unionTag"] for row in decoded["audioBehaviors"]], [1, 2, 3, 4])
        event, position, rtpc, spatial = decoded["audioBehaviors"]
        self.assertEqual(event["normalAudioId"], -9606891)
        self.assertEqual(event["unionTagHex"], "0x0001")
        self.assertEqual(position["normalAudioId"], 1348303159)
        self.assertEqual(rtpc["audioRTPCValue"], "au_rtpc_int_delta_progress")
        self.assertEqual(rtpc["rtpcBehaviourType"], 2)
        self.assertTrue(spatial["directSet"])
        for row in decoded["audioBehaviors"]:
            self.assertEqual(row["modelAnimatorName"], "P_fixture_model")
            self.assertEqual(row["layerName"], "audioLayer")
            self.assertEqual(row["layerFsmIndex"], 3)
            self.assertEqual(row["stateName"], "Rotating")

    def test_model_view_decoder_fails_closed_on_union_or_graph_drift(self) -> None:
        fixture = model_view_controller_fixture()
        decoded = interactive_binary.decode_model_view_state_controller(fixture)
        behavior_offset = decoded["audioBehaviors"][0]["sourceOffset"]

        changed_members = bytearray(fixture)
        changed_members[behavior_offset + 1] = 15
        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "member count"):
            interactive_binary.decode_model_view_state_controller(bytes(changed_members))

        changed_type = bytearray(fixture)
        changed_type[behavior_offset + 2 + 3 + 4 + 4:behavior_offset + 2 + 3 + 4 + 8] = pack("<i", 8)
        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "behavior type"):
            interactive_binary.decode_model_view_state_controller(bytes(changed_type))

        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "trailing bytes"):
            interactive_binary.decode_model_view_state_controller(fixture + b"\x00")

    def test_decodes_exact_physics_audio_property_map_and_offsets(self) -> None:
        prefix = b"fixture-prefix"
        data = prefix + physics_component_fixture() + b"\x33\x01"

        components = interactive_binary.find_physics_audio_components(data)

        self.assertEqual(len(components), 1)
        component = components[0]
        self.assertEqual(component["sourceOffset"], len(prefix))
        self.assertEqual(component["memberCount"], 1)
        self.assertEqual(component["propertyCount"], 21)
        self.assertEqual(component["endOffset"], len(data) - 2)
        values = {row["authoredKey"]: row["value"] for row in component["properties"]}
        self.assertEqual(values["on_start_move_audio_event"], "au_int_kickable_ball_start")
        self.assertEqual(values["velocity_sqr_rtpc"], "rtpc_int_kickable_ball_speed")
        self.assertEqual(values["on_hit_max_player_per_move"], -1)
        self.assertTrue(math.isclose(values["on_hit_min_interval_time"], 0.3, rel_tol=1e-6))
        fields = {row["authoredKey"]: row["runtimeField"] for row in component["properties"]}
        self.assertEqual(fields["on_hit_max_player_per_move"], "onHitMaxPlayPerMove")
        self.assertEqual(
            fields["on_rotation_ground_one_shot_trigger_audio_event"],
            "onRotationGroundOneShotTriggerRatio",
        )
        self.assertTrue(all(row["propertySourceOffset"] >= len(prefix) for row in component["properties"]))

    def test_physics_audio_decoder_fails_closed_on_shape_drift(self) -> None:
        fixture = physics_component_fixture()
        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "member count"):
            interactive_binary.decode_physics_audio_component(fixture[:1] + b"\x02" + fixture[2:])
        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "member count"):
            interactive_binary.find_physics_audio_components(fixture[:1] + b"\x02" + fixture[2:])

        decoded = interactive_binary.decode_physics_audio_component(fixture)
        value_offset = decoded["properties"][2]["valueSourceOffset"]
        changed_type = bytearray(fixture)
        changed_type[value_offset + 1:value_offset + 5] = pack("<i", interactive_binary.PROPERTY_BOOL)
        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "value type"):
            interactive_binary.decode_physics_audio_component(bytes(changed_type))

        with self.assertRaises(interactive_binary.InteractiveBinaryDecodeError):
            interactive_binary.decode_physics_audio_component(fixture[:-1])

    def test_interactive_table_preserves_exact_definition_and_alias_join(self) -> None:
        decoded = interactive_binary.decode_interactive_table(interactive_table_fixture())

        self.assertEqual(decoded["coreTemplateCount"], 1)
        self.assertEqual(decoded["interactiveDataCount"], 2)
        self.assertEqual(
            decoded["coreTemplatePaths"]["int_kickable_ball"],
            "Data/Json/Interactive/InteractiveData/data_int_kickable_ball.json",
        )
        self.assertEqual(decoded["objectToTemplate"]["int_tumble_weed"], "int_kickable_ball")
        self.assertEqual(decoded["endOffset"], len(interactive_table_fixture()))

        with self.assertRaisesRegex(interactive_binary.InteractiveBinaryDecodeError, "trailing bytes"):
            interactive_binary.decode_interactive_table(interactive_table_fixture() + b"\x00")


if __name__ == "__main__":
    unittest.main()
