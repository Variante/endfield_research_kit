"""Fail-closed reader for current CharInteractPerform audio actions.

The maintained boundary is intentionally narrow.  Files without the exact
``AudioEventActData`` union header are ignored.  A file containing that header
must then decode as a complete 27-member ``CharInteractPerformRuntimeCfg`` and
the candidate must be reached through one of its counted action-list fields.
Unknown action tags or changed nested member counts reject the whole owner;
the prefilter is never semantic evidence by itself.
"""
from __future__ import annotations

import struct
from typing import Any


NULL_COUNT = 0xFFFFFFFF
OUTER_MEMBER_COUNT = 27
AUDIO_EVENT_TAG = 0x02
AUDIO_EVENT_MEMBER_COUNT = 15
SCHEMA_MAPPING_ID = "gameassembly-0c557367-char-interact-audio-event-v1"
UNION_MAPPING_ID = "gameassembly-0c557367-char-interact-action-union-v1"


class CharInteractPerformDecodeError(ValueError):
    """Raised when a candidate owner no longer matches the exact current layout."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0
        self.audio_actions: list[dict[str, Any]] = []

    def _need(self, size: int, field: str) -> None:
        if size < 0 or self.offset + size > len(self.data):
            raise CharInteractPerformDecodeError(
                f"{field}: truncated at 0x{self.offset:x}"
            )

    def u8(self, field: str) -> int:
        self._need(1, field)
        value = self.data[self.offset]
        self.offset += 1
        return value

    def boolean(self, field: str) -> bool:
        value = self.u8(field)
        if value not in (0, 1):
            raise CharInteractPerformDecodeError(
                f"{field}: invalid bool {value} at 0x{self.offset - 1:x}"
            )
        return bool(value)

    def _number(self, fmt: str, size: int, field: str) -> int | float:
        self._need(size, field)
        value = struct.unpack_from(fmt, self.data, self.offset)[0]
        self.offset += size
        return value

    def i32(self, field: str) -> int:
        return int(self._number("<i", 4, field))

    def u32(self, field: str) -> int:
        return int(self._number("<I", 4, field))

    def i64(self, field: str) -> int:
        return int(self._number("<q", 8, field))

    def u64(self, field: str) -> int:
        return int(self._number("<Q", 8, field))

    def f32(self, field: str) -> float:
        return float(self._number("<f", 4, field))

    def string(self, field: str) -> str | None:
        length = self.u32(field + ".length")
        if length == NULL_COUNT:
            return None
        if length > 10_000:
            raise CharInteractPerformDecodeError(
                f"{field}: invalid string length {length}"
            )
        self._need(length, field)
        try:
            value = self.data[self.offset:self.offset + length].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CharInteractPerformDecodeError(f"{field}: invalid UTF-8") from exc
        self.offset += length
        return value

    def count(self, field: str, maximum: int = 10_000) -> int | None:
        value = self.u32(field + ".count")
        if value == NULL_COUNT:
            return None
        if value > maximum:
            raise CharInteractPerformDecodeError(f"{field}: invalid count {value}")
        return value

    def member(self, expected: int, field: str, *, nullable: bool = False) -> bool:
        value = self.u8(field + ".memberCount")
        if nullable and value == 0xFF:
            return False
        if value != expected:
            raise CharInteractPerformDecodeError(
                f"{field}: member count {value}, expected {expected}"
            )
        return True

    def list(self, field: str, item) -> list[Any]:
        count = self.count(field)
        values = []
        for index in range(count or 0):
            values.append(item(f"{field}[{index}]"))
        return values

    def dictionary(self, field: str, key, value) -> list[tuple[Any, Any]]:
        count = self.count(field)
        values = []
        for index in range(count or 0):
            values.append((
                key(f"{field}[{index}].key"),
                value(f"{field}[{index}].value"),
            ))
        return values

    def serialized_dictionary(self, field: str, key, value) -> list[tuple[Any, Any]] | None:
        if not self.member(1, field, nullable=True):
            return None
        return self.dictionary(field + ".dictionary", key, value)

    def gameplay_tag(self, field: str) -> int:
        self.member(1, field)
        return self.u32(field + ".tagId")

    def body_type(self, field: str) -> None:
        self.member(3, field)
        self.u8(field + ".bodyType")
        self.i32(field + ".CustomId")
        self.string(field + ".CustomName")

    def actor(self, field: str) -> None:
        self.member(10, field)
        self.i32(field + ".actorType")
        self.i32(field + ".charType")
        self.u64(field + ".decoId")
        self.string(field + ".effectPath")
        self.string(field + ".interactivePath")
        self.i32(field + ".interactiveType")
        self.string(field + ".npcId")
        self.boolean(field + ".performEndNotDestroy")
        self.string(field + ".tmpObjectPath")
        self.i64(field + ".tmpObjectPathHash")

    def transform(self, field: str) -> None:
        if not self.member(4, field, nullable=True):
            return
        for axis in "xyz":
            self.f32(f"{field}.pos.{axis}")
        for axis in "xyz":
            self.f32(f"{field}.rot.{axis}")
        self.boolean(field + ".usePos")
        self.boolean(field + ".useRot")

    def animation_curve(self, field: str) -> None:
        if not self.member(3, field, nullable=True):
            return
        count = self.count(field + ".keys")
        for index in range(count or 0):
            item = f"{field}.keys[{index}]"
            self.member(8, item)
            for name in ("inTangent", "inWeight", "outTangent", "outWeight"):
                self.f32(f"{item}.{name}")
            self.i32(item + ".tangentMode")
            self.f32(item + ".time")
            self.f32(item + ".value")
            self.i32(item + ".weightedMode")
        self.i32(field + ".postWrapMode")
        self.i32(field + ".preWrapMode")

    def alpha_blend(self, field: str) -> None:
        self.member(3, field)
        self.i32(field + "._blendOption")
        self.f32(field + "._blendTime")
        self.animation_curve(field + "._customCurve")

    def special_entry(self, field: str) -> None:
        if not self.member(3, field, nullable=True):
            return
        condition_count = self.count(field + ".conditions")
        if condition_count:
            raise CharInteractPerformDecodeError(
                f"{field}.conditions: unsupported non-empty condition union"
            )
        self.string(field + ".memo")
        self.list(field + ".performIds", self.string)

    def special_entry_data(self, field: str) -> None:
        if not self.member(1, field, nullable=True):
            return
        self.list(field + ".entries", self.special_entry)

    def body_type_action_data(self, field: str) -> None:
        if not self.member(1, field, nullable=True):
            return
        self.action_list(field + ".bodyTypeActions", "bodyTypeActions")

    def _base_action(self, field: str) -> dict[str, Any]:
        self.body_type(field + ".bodyType")
        delay = self.f32(field + ".delay")
        dev_only = self.boolean(field + ".devOnly")
        duration = self.f32(field + ".duration")
        event_id = self.string(field + ".eventId")
        if_override = self.boolean(field + ".ifOverridePlayFast")
        logic_id = self.u32(field + ".logicId")
        override = self.boolean(field + ".overridePlayFast")
        play_before_destroy = self.boolean(field + ".playBeforeDestroy")
        use_event = self.boolean(field + ".useEvent")
        return {
            "delay": delay,
            "devOnly": dev_only,
            "duration": duration,
            "eventId": event_id or "",
            "ifOverridePlayFast": if_override,
            "logicId": logic_id,
            "overridePlayFast": override,
            "playBeforeDestroy": play_before_destroy,
            "useEvent": use_event,
        }

    def _char_anim(self, field: str) -> None:
        self.string(field + ".animName")
        self.boolean(field + ".autoBlendOut")
        self.f32(field + ".blendInTime")
        self.alpha_blend(field + ".blendOut")
        for name in ("endFalling", "exitFalling", "overrideBlendOut", "overrideStopBlendOut"):
            self.boolean(f"{field}.{name}")
        self.f32(field + ".rootMotionWrapTime")
        self.transform(field + ".startTransform")
        self.f32(field + ".stopBlendOutTime")
        for name in ("useAutoTime", "useCurrent", "useRootMotion", "useRootMotionDest"):
            self.boolean(f"{field}.{name}")

    def _char_npc_montage(self, field: str) -> None:
        self.boolean(field + ".autoBlendOut")
        self.f32(field + ".blendInTime")
        self.alpha_blend(field + ".blendOut")
        self.boolean(field + ".overrideBlendOut")
        self.u32(field + ".tag")  # direct embedded GameplayTag value
        self.dictionary(field + ".template2Tag", self.string, self.gameplay_tag)
        self.boolean(field + ".useAutoTime")
        self.boolean(field + ".useDynamicEntity")
        self.boolean(field + ".useTemplateSeparateTag")

    def _effect_play(self, field: str) -> None:
        self.i32(field + ".attachedActorType")
        self.i32(field + ".charIndex")
        self.i32(field + ".effectMoveType")
        self.boolean(field + ".initUseRootRot")
        self.boolean(field + ".isVFX")
        self.i32(field + ".mountPoint")
        self.transform(field + ".mountPointOffset")
        self.boolean(field + ".notRotFollow")
        self.boolean(field + ".show")
        self.boolean(field + ".useCharIk")

    def action(self, field: str, placement: str, index: int) -> None:
        start = self.offset
        tag = self.u8(field + ".unionTag")
        layouts = {
            2: (False, 5), 3: (False, 5), 6: (False, 4),
            8: (True, 15), 15: (True, 9), 16: (True, 7),
            25: (True, 10), 33: (False, 2),
        }
        layout = layouts.get(tag)
        if layout is None:
            raise CharInteractPerformDecodeError(
                f"{field}: unsupported current action union tag 0x{tag:02x}"
            )
        actor_derived, subtype_members = layout
        member_count = self.u8(field + ".memberCount")
        expected = 10 + int(actor_derived) + subtype_members
        if member_count != expected:
            raise CharInteractPerformDecodeError(
                f"{field}: tag 0x{tag:02x} member count {member_count}, expected {expected}"
            )
        base = self._base_action(field)
        if actor_derived:
            self.i32(field + ".actorIndex")
        if tag == 2:
            attached_actor_type = self.i32(field + ".attachedActorType")
            audio_event = self.u32(field + ".audioEvent")
            char_index = self.i32(field + ".charIndex")
            end_stop = self.boolean(field + ".endStop")
            is_2d = self.boolean(field + ".is2D")
            self.audio_actions.append({
                "sourceOffset": start,
                "endOffset": self.offset,
                "byteLength": self.offset - start,
                "unionTag": tag,
                "unionTagHex": f"0x{tag:04x}",
                "memberCount": member_count,
                "placement": placement,
                "actionIndex": index,
                "audioEvent": audio_event,
                "audioEventHex": f"0x{audio_event:08x}",
                "attachedActorType": attached_actor_type,
                "charIndex": char_index,
                "endStop": end_stop,
                "is2D": is_2d,
                **base,
                "schemaMappingId": SCHEMA_MAPPING_ID,
                "unionMappingId": UNION_MAPPING_ID,
                "schemaStatus": "exact-current-complete-owner-container",
            })
        elif tag == 3:
            self.i32(field + ".blendStyle")
            self.f32(field + ".blendTime")
            self.string(field + ".id")
            self.boolean(field + ".overrideBlend")
            self.string(field + ".stateConfig")
        elif tag == 6:
            self.i32(field + ".blendStyle")
            self.f32(field + ".blendTime")
            self.string(field + ".id")
            self.boolean(field + ".overrideBlend")
        elif tag == 8:
            self._char_anim(field)
        elif tag == 15:
            self._char_npc_montage(field)
        elif tag == 16:
            self.boolean(field + ".overrideRotateRate")
            self.boolean(field + ".playAnim")
            self.f32(field + ".rotateRate")
            self.i32(field + ".targetActorIndex")
            self.i32(field + ".targetActorType")
            self.transform(field + ".targetTransform")
            self.boolean(field + ".useTargetTransform")
        elif tag == 25:
            self._effect_play(field)
        elif tag == 33:
            self.i32(field + ".interruptType")
            self.boolean(field + ".removeTag")

    def action_list(self, field: str, placement: str) -> None:
        count = self.count(field)
        for index in range(count or 0):
            self.action(f"{field}[{index}]", placement, index)

    def decode(self) -> list[dict[str, Any]]:
        if self.u8("CharInteractPerformRuntimeCfg.memberCount") != OUTER_MEMBER_COUNT:
            raise CharInteractPerformDecodeError(
                "CharInteractPerformRuntimeCfg member count changed"
            )
        self.list("activeTags", self.gameplay_tag)
        self.boolean("allowInheritPerform")
        self.serialized_dictionary("bodyTypeActDataDict", self.u32, self.body_type_action_data)
        self.i32("charPerformType")
        self.list("chars", self.actor)
        self.list("decos", self.actor)
        self.special_entry_data("defaultSubPerformEntry")
        self.boolean("disableIKAndFollow")
        self.list("effects", self.actor)
        self.action_list("endActions", "endActions")
        self.f32("fixedTime")
        self.boolean("forceExitCommandsContinuous")
        self.list("guardActiveTags", self.gameplay_tag)
        self.list("guardInterruptReasons", self.i32)
        self.boolean("hideWeapon")
        self.list("inheritPerformIds", self.string)
        self.list("interactives", self.actor)
        self.list("interruptReasons", self.i32)
        self.boolean("keepFightState")
        self.action_list("loopActions", "loopActions")
        self.list("npcs", self.actor)
        self.i32("performType")
        self.action_list("preStartActions", "preStartActions")
        self.action_list("startActions", "startActions")
        self.serialized_dictionary("subPerformEntries", self.string, self.special_entry_data)
        self.list("tmpObjects", self.actor)
        self.boolean("usePreStartActions")
        if self.offset != len(self.data):
            raise CharInteractPerformDecodeError(
                f"CharInteractPerformRuntimeCfg: trailing bytes at 0x{self.offset:x}"
            )
        return self.audio_actions


def decode_char_interact_audio_actions(data: bytes) -> list[dict[str, Any]]:
    """Return exact AudioEvent actions from one fully bounded current owner.

    No candidate header means the owner is outside this narrow recovery family.
    If a candidate exists, every field required to reach EOF is validated and
    every candidate must equal an action reached through a counted phase list.
    """
    anchor = bytes((AUDIO_EVENT_TAG, AUDIO_EVENT_MEMBER_COUNT))
    candidate_offsets: list[int] = []
    cursor = 0
    while True:
        offset = data.find(anchor, cursor)
        if offset < 0:
            break
        candidate_offsets.append(offset)
        cursor = offset + 1
    if not candidate_offsets:
        return []
    rows = _Reader(data).decode()
    accepted_offsets = [int(row["sourceOffset"]) for row in rows]
    if accepted_offsets != candidate_offsets:
        raise CharInteractPerformDecodeError(
            "AudioEventActData candidates do not equal bounded action-list records: "
            f"candidates={candidate_offsets}, accepted={accepted_offsets}"
        )
    return rows
