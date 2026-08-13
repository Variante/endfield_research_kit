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


class LevelScriptSpawnerEventTests(unittest.TestCase):
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
        self.assertEqual(
            {},
            decode_spawner_event_fields(payload + b"\x00", _LIFECYCLE_EVENTS[0]),
        )


if __name__ == "__main__":
    unittest.main()
