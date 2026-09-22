"""Exact codec for the LevelScript encounter module target payload.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import math
import struct

from scripts.game_data.codecs.levelscript import top_level_tail as levelscript_top_level_tail
from scripts.game_data.codecs.levelscript import trigger_volumes as levelscript_trigger_volumes
from scripts.game_data.codecs.levelscript.framing_common import _drop_empty
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.framing_common import _round_float
from scripts.game_data.codecs.levelscript.primitives import i32 as _i32
from typing import Any

def decode_levelscript_encounter_module_target(
    data: bytes,
    encounter_pointer: int | str,
    expected_script_id: int | str,
) -> dict[str, Any]:
    """Resolve one exact ``LsmPtr`` to a top-level ``EncounterData`` value.

    The current MemoryPack union has no per-value byte length, so an unknown
    module cannot be skipped safely.  This decoder intentionally accepts only
    a one-entry ``modules`` dictionary whose sole union value is EncounterData,
    consumes that value completely, and validates the remaining top-level
    LevelScriptData tail through EOF.  It returns no partial result.
    """
    try:
        pointer = int(encounter_pointer)
        script_id = int(expected_script_id)
    except (TypeError, ValueError):
        return {}
    if not data or data[0] != 0x1B or pointer <= 0 or script_id <= 0:
        return {}

    class Cursor:
        def __init__(self, offset: int):
            self.offset = offset

        def take(self, size: int) -> bytes:
            if size < 0 or self.offset < 0 or self.offset + size > len(data):
                raise ValueError("truncated")
            value = data[self.offset:self.offset + size]
            self.offset += size
            return value

        def u8(self) -> int:
            return self.take(1)[0]

        def boolean(self) -> bool:
            value = self.u8()
            if value not in (0, 1):
                raise ValueError("invalid bool")
            return bool(value)

        def i32(self) -> int:
            return struct.unpack("<i", self.take(4))[0]

        def u32(self) -> int:
            return struct.unpack("<I", self.take(4))[0]

        def u64(self) -> int:
            return struct.unpack("<Q", self.take(8))[0]

        def f32(self) -> float:
            value = struct.unpack("<f", self.take(4))[0]
            if not math.isfinite(value):
                raise ValueError("non-finite float")
            return value

        def string(self) -> str | None:
            size = self.i32()
            if size == -1:
                return None
            if size < 0 or size > 1_048_576:
                raise ValueError("invalid string size")
            return self.take(size).decode("utf-8", errors="strict")

        def count(self, *, maximum: int = 1024) -> int | None:
            value = self.i32()
            if value == -1:
                return None
            if value < 0 or value > maximum:
                raise ValueError("invalid collection count")
            return value

    def pos_rot(cursor: Cursor) -> None:
        for _ in range(6):
            cursor.f32()

    def slot_ptr(cursor: Cursor) -> dict[str, Any]:
        if cursor.u8() != 3:
            raise ValueError("invalid slot pointer member count")
        return {
            "logicId": str(cursor.u64()),
            "slotId": cursor.u32(),
            "useSlotId": cursor.boolean(),
        }

    def intro_part(cursor: Cursor) -> None:
        if cursor.u8() != 13:
            raise ValueError("invalid intro-part member count")
        cursor.i32()  # airWallShowTiming
        cursor.i32()  # enemySpawnTiming
        cursor.f32()
        cursor.f32()
        cursor.boolean()
        cursor.boolean()
        if cursor.count() is not None:
            # OperaSegment is deliberately unsupported until a current blob
            # requires it; without a byte length it cannot be skipped.
            raise ValueError("unsupported intro opera segments")
        cursor.i32()  # teleportMode
        for _ in range(4):
            pos_rot(cursor)
        cursor.i32()  # teleportTiming

    needle = struct.pack("<Q", pointer)
    candidates: list[dict[str, Any]] = []
    start = 0
    while True:
        key_offset = data.find(needle, start)
        if key_offset < 0:
            break
        start = key_offset + 1
        if key_offset < 4 or _i32(data, key_offset - 4) != 1:
            continue
        try:
            cursor = Cursor(key_offset)
            if cursor.u64() != pointer or cursor.u8() != 2 or cursor.u8() != 16:
                continue
            disabled_when_completed = cursor.boolean()
            if cursor.u64() != pointer:
                continue
            activate_mode = cursor.i32()
            activate_mode_alter = cursor.i32()
            activate_trigger_slot_id = cursor.u32()
            activate_trigger_slot_id_alter = cursor.u32()
            if cursor.count() is not None:
                raise ValueError("unsupported direct air-wall list")
            air_wall_count = cursor.count(maximum=64)
            air_wall_ptrs = [slot_ptr(cursor) for _ in range(air_wall_count or 0)]
            if cursor.u8() != 8:
                raise ValueError("invalid battle-part member count")
            complete_delay = cursor.f32()
            complete_delay_mode = cursor.i32()
            complete_delay_str_param = cursor.string()
            complete_mode = cursor.i32()
            dont_hide_dead_enemy = cursor.boolean()
            exit_trigger_slot_id = cursor.u32()
            keep_hatred = cursor.boolean()
            protect_enemy = cursor.boolean()
            enemy_count = cursor.count(maximum=256)
            enemies = [slot_ptr(cursor) for _ in range(enemy_count or 0)]
            intro_part(cursor)
            if cursor.u8() != 0xFF:
                raise ValueError("unsupported intro-part alter")
            intro_part_mode = cursor.i32()
            spawner_id = cursor.u64()
            if cursor.u8() != 0xFF:
                raise ValueError("unsupported tail part")
            tail_part_mode = cursor.i32()
            encounter_end = cursor.offset

            # Exact current top-level tail after modules.  Non-null NPC or
            # property collections fail closed rather than being scanned.
            npc_count = cursor.count()
            if npc_count not in (None, 0) or cursor.u64() != 0:
                raise ValueError("unsupported npcs or parent script")
            if any(cursor.count() is not None for _ in range(3)):
                raise ValueError("unsupported property/reference collection")
            reset_mode_when_active = cursor.i32()
            reset_mode_when_end = cursor.i32()
            if cursor.u64() != script_id:
                raise ValueError("script id mismatch")
            if cursor.count() is not None:
                raise ValueError("unsupported start shape list")
            start_type = cursor.i32()
            if start_type not in levelscript_top_level_tail.START_TYPE_NAMES:
                raise ValueError("invalid start type")
            if cursor.count() is not None:
                raise ValueError("unsupported task map")
            trigger_offset = cursor.offset
            trigger_map, trigger_end = levelscript_trigger_volumes.decode_trigger_volume_map(
                data,
                trigger_offset,
            )
            if trigger_end != len(data):
                raise ValueError("top-level tail does not end at EOF")

            candidates.append(_drop_empty({
                "status": "exact_top_level_encounter_module_target",
                "moduleType": "EncounterData",
                "moduleUnionTag": "0x02",
                "serializedMemberCount": 16,
                "levelScriptVariablePtr": str(pointer),
                "levelNum": pointer // 100_000_000,
                "moduleLocalId": pointer % 100_000_000,
                "listenerScriptId": str(script_id),
                "dictionaryCount": 1,
                "dictionaryOffset": key_offset - 4,
                "dictionaryOffsetHex": _offset_hex(key_offset - 4),
                "dictionaryKeyOffset": key_offset,
                "dictionaryKeyOffsetHex": _offset_hex(key_offset),
                "encounterEndOffset": encounter_end,
                "encounterEndOffsetHex": _offset_hex(encounter_end),
                "disableWhenCompleted": disabled_when_completed,
                "activateMode": activate_mode,
                "activateModeAlter": activate_mode_alter,
                "activateTriggerSlotId": activate_trigger_slot_id,
                "activateTriggerSlotIdAlter": activate_trigger_slot_id_alter,
                "airWallPointers": air_wall_ptrs,
                "battlePart": {
                    "completeDelay": _round_float(complete_delay),
                    "completeDelayMode": complete_delay_mode,
                    "completeDelayStrParam": complete_delay_str_param,
                    "completeMode": complete_mode,
                    "dontHideDeadEnemyWhenComplete": dont_hide_dead_enemy,
                    "exitTriggerSlotId": exit_trigger_slot_id,
                    "keepHatred": keep_hatred,
                    "protectEnemyBeforeBattlePart": protect_enemy,
                },
                "enemyPointers": enemies,
                "introPartMode": intro_part_mode,
                "spawnerId": str(spawner_id),
                "tailPartMode": tail_part_mode,
                "resetModeWhenActive": reset_mode_when_active,
                "resetModeWhenEnd": reset_mode_when_end,
                "startType": levelscript_top_level_tail.START_TYPE_NAMES[start_type],
                "triggerVolumeCount": trigger_map.get("count"),
                "serializedMissionOrQuestId": False,
                "clientRequest": False,
                "expectedServerReturn": False,
                "ownershipBoundary": (
                    "The exact runtime target is a level-script EncounterData module. "
                    "Its current-build serializer, BattlePart, and event payload contain "
                    "no missionId, questId, or MissionArea foreign key."
                ),
            }))
        except (UnicodeDecodeError, ValueError, struct.error):
            continue
    return candidates[0] if len(candidates) == 1 else {}
