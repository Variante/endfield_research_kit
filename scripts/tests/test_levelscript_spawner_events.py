from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.spawner_events import (
    decode_spawner_event_fields,
)


_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
_LIFECYCLE_EVENTS = (
    "LevelEvent_OnSpawnerEntityDie",
    "LevelEvent_OnSpawnerEntityDieStart",
    "LevelEvent_OnSpawnerEntityDieEnd",
)


def _output(source: int, path: str | None) -> bytes:
    if path is None:
        return b"\x02" + struct.pack("<ii", source, -1)
    encoded = path.encode("utf-8")
    return b"\x02" + struct.pack("<ii", source, len(encoded)) + encoded


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return b"\x04" + struct.pack("<i", len(encoded)) + encoded + _PARAM_TAIL


def _lifecycle_payload() -> bytes:
    return b"".join((
        bytes(17),
        b"\x04\x01" + _PARAM_TAIL,
        _output(0, "$7@_entity"),
        b"\x04" + struct.pack("<iiii", 2, -1, 0, -1),
        _string("group-a"),
        _output(0, "$7@_group"),
        b"\x04" + struct.pack("<Q", 10200260004) + _PARAM_TAIL,
        b"\xff",
        _output(100, None),
    ))


def _spawn_payload() -> bytes:
    return b"".join((
        bytes(17),
        b"\x04\x01" + _PARAM_TAIL,
        _output(0, "$170@_entityOutput"),
        b"\x04" + struct.pack("<i", 4) + _PARAM_TAIL,
        b"\xff",
        _output(0, "$170@_groupKeyOutput"),
        b"\x04" + struct.pack("<Q", 10200060003) + _PARAM_TAIL,
        _string("wave2"),
        _output(0, "$170@_waveKeyOutput"),
    ))


def _wave_begin_with_getter_validation() -> bytes:
    return b"".join((
        bytes(17),
        b"\x04\x01" + struct.pack("<iii", 14, -1, -1),
        b"\x04" + struct.pack("<Q", 10100510001) + _PARAM_TAIL,
        b"\xff",
        _string("C"),
        b"\xff",
    ))


def _group_begin_payload() -> bytes:
    return b"".join((
        bytes(17),
        b"\x04\x01" + _PARAM_TAIL,
        _string("group02"),
        b"\xff",
        b"\x04" + struct.pack("<Q", 22800110003) + _PARAM_TAIL,
        b"\xff",
    ))


def _group_begin_nullable_filter_with_outputs() -> bytes:
    return b"".join((
        bytes(17),
        b"\x04\x01" + _PARAM_TAIL,
        b"\xff",
        _output(0, "$42@_groupKeyOutput"),
        b"\x04" + struct.pack("<Q", 200210000) + _PARAM_TAIL,
        _output(0, "$42@_spawnerOutput"),
    ))


class LevelScriptSpawnerEventTests(unittest.TestCase):
    def test_start_pause_group_and_wave_complete_decode_constant_spawners(self) -> None:
        prefix = bytes(17) + b"\x04\x01" + _PARAM_TAIL
        spawner = b"\x04" + struct.pack("<Q", 35300010001) + _PARAM_TAIL
        fixtures = {
            "LevelEvent_OnSpawnerStart": prefix + spawner + b"\xff",
            "LevelEvent_OnSpawnerPause": prefix + _string("Pause") + b"\xff" + spawner + b"\xff",
            "LevelEvent_OnSpawnerGroupComplete": prefix + _string("B") + b"\xff" + spawner + b"\xff",
            "LevelEvent_OnSpawnerWaveComplete": prefix + spawner + b"\xff" + _string("wave2") + b"\xff",
        }
        for event_name, payload in fixtures.items():
            with self.subTest(event_name=event_name):
                detail = decode_spawner_event_fields(payload, event_name)
                self.assertEqual(35300010001, detail["spawnerFilterId"])
                self.assertEqual(len(payload), detail["subtypeConsumedBytes"])

    def test_wave_begin_retains_constant_spawner_with_getter_validation(self) -> None:
        payload = _wave_begin_with_getter_validation()
        detail = decode_spawner_event_fields(payload, "LevelEvent_OnSpawnerWaveBegin")
        self.assertEqual(10100510001, detail["spawnerFilterId"])
        self.assertEqual("C", detail["waveKeyFilter"])

    def test_wave_begin_retains_getter_spawner_and_nullable_outputs(self) -> None:
        prefix = bytes(17) + b"\x04\x01" + _PARAM_TAIL
        getter_spawner = b"\x04" + struct.pack("<Qiii", 0, 6, -1, -1)
        payload = prefix + getter_spawner + b"\xff\xff" + _output(0, "$7@_waveKeyOutput")
        detail = decode_spawner_event_fields(payload, "LevelEvent_OnSpawnerWaveBegin")
        self.assertIsNone(detail["spawnerFilterId"])
        self.assertEqual(6, detail["spawnerFilterParam"]["idRef"])
        self.assertIsNone(detail["waveKeyFilter"])
        self.assertEqual(
            "$7@_waveKeyOutput",
            detail["waveKeyOutputParam"]["path"],
        )

    def test_group_begin_accepts_exact_subtype_before_following_lists(self) -> None:
        payload = _group_begin_payload()
        detail = decode_spawner_event_fields(
            payload + b"\x01\x00\x00\x00",
            "LevelEvent_OnSpawnerGroupBegin",
        )
        self.assertEqual(22800110003, detail["spawnerFilterId"])
        self.assertEqual(len(payload), detail["subtypeConsumedBytes"])
        self.assertTrue(detail["payloadShape"].endswith("exact-prefix"))

    def test_group_begin_accepts_nullable_filter_and_present_outputs(self) -> None:
        payload = _group_begin_nullable_filter_with_outputs()
        detail = decode_spawner_event_fields(payload, "LevelEvent_OnSpawnerGroupBegin")
        self.assertIsNone(detail["groupKeyFilter"])
        self.assertEqual(200210000, detail["spawnerFilterId"])
        self.assertEqual(
            {"paramSource": 0, "path": "$42@_groupKeyOutput"},
            detail["groupKeyOutputParam"],
        )
        self.assertEqual(
            {"paramSource": 0, "path": "$42@_spawnerOutput"},
            detail["spawnerOutputParam"],
        )
        self.assertEqual(len(payload), detail["subtypeConsumedBytes"])

    def test_entity_spawn_decodes_nullable_group_and_constant_wave(self) -> None:
        payload = _spawn_payload()
        detail = decode_spawner_event_fields(payload, "LevelEvent_OnSpawnerEntitySpawn")
        self.assertEqual(10200060003, detail["spawnerFilterId"])
        self.assertEqual(4, detail["filterType"])
        self.assertNotIn("entityTemplateIdFilter", detail)
        self.assertIsNone(detail["groupKeyFilter"])
        self.assertEqual("wave2", detail["waveKeyFilter"])
        self.assertEqual(len(payload), detail["subtypeConsumedBytes"])

    def test_entity_lifecycle_family_decodes_exact_schema(self) -> None:
        payload = _lifecycle_payload()
        for event_name in _LIFECYCLE_EVENTS:
            with self.subTest(event_name=event_name):
                detail = decode_spawner_event_fields(payload, event_name)
                self.assertEqual(10200260004, detail["spawnerFilterId"])
                self.assertEqual("group-a", detail["groupKeyFilter"])
                self.assertIsNone(detail["waveKeyFilter"])
                self.assertEqual(
                    {"value": 2, "idRef": -1, "paramSource": 0, "path": None},
                    detail["filterType"],
                )
                self.assertEqual(
                    {"paramSource": 100, "path": None},
                    detail["waveKeyOutputParam"],
                )

    def test_entity_lifecycle_family_rejects_wrong_owner_or_trailing_bytes(self) -> None:
        payload = _lifecycle_payload()
        self.assertEqual({}, decode_spawner_event_fields(payload, "LevelEvent_OnSpawnerStop"))
        detail = decode_spawner_event_fields(payload + b"\x00", _LIFECYCLE_EVENTS[0])
        self.assertEqual(len(payload), detail["subtypeConsumedBytes"])
        self.assertEqual(
            "spawner-entity-lifecycle-filters-and-outputs-exact-prefix",
            detail["payloadShape"],
        )


if __name__ == "__main__":
    unittest.main()
