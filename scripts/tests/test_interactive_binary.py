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


class InteractiveBinaryTests(unittest.TestCase):
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
