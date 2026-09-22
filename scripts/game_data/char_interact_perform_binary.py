"""Fail-closed reader for current CharInteractPerform audio actions.

The maintained boundary is intentionally narrow.  Files without the exact
``AudioEventActData`` union header are ignored.  A file containing that header
must then decode as a complete 27-member ``CharInteractPerformRuntimeCfg`` and
the candidate must be reached through one of its counted action-list fields.
Unknown action tags or changed nested member counts reject the whole owner;
the prefilter is never semantic evidence by itself.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.game_data.contracts import CONTRACTS_DIR


NULL_COUNT = 0xFFFFFFFF
OUTER_MEMBER_COUNT = 27
AUDIO_EVENT_TAG = 0x02
AUDIO_EVENT_MEMBER_COUNT = 15
SCHEMA_MAPPING_ID = "endfield.char-interact-perform-runtime-cfg.v1"
UNION_MAPPING_ID = "endfield.char-interact-perform-native-contract.v1"
CONTRACT_SHA256 = "eda3372ffdb67955b2f216d256f9d583d889a93c5f1f62de1525a891d78816ac"


def _load_action_contract() -> tuple[dict[int, tuple[bool, int]], dict[int, str]]:
    path = CONTRACTS_DIR / "char_interact_perform_native.json"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CONTRACT_SHA256:
        raise RuntimeError(
            f"{path}: contract SHA256 {digest} does not match {CONTRACT_SHA256}"
        )
    payload = json.loads(raw)
    if payload.get("schema") != UNION_MAPPING_ID or payload.get("status") != "validated":
        raise RuntimeError(f"{path}: unsupported or unvalidated contract")
    tags = {int(tag): str(name) for tag, name in payload.get("tags", [])}
    if set(tags) != set(range(37)):
        raise RuntimeError(f"{path}: action union tags are not the exact 0..36 range")
    layouts = {
        int(tag): (bool(row[0]), int(row[1]))
        for tag, row in payload.get("observedLayouts", {}).items()
    }
    return layouts, tags


ACTION_LAYOUTS, ACTION_TAG_NAMES = _load_action_contract()


class CharInteractPerformDecodeError(ValueError):
    """Raised when a candidate owner no longer matches the exact current layout."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0
        self.actions: list[dict[str, Any]] = []
        self.audio_actions: list[dict[str, Any]] = []
        self.owner_actor_collections: dict[str, list[dict[str, Any]]] = {}

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

    def actor(self, field: str) -> dict[str, Any]:
        self.member(10, field)
        return {
            "actorType": self.i32(field + ".actorType"),
            "charType": self.i32(field + ".charType"),
            "decoId": self.u64(field + ".decoId"),
            "effectPath": self.string(field + ".effectPath"),
            "interactivePath": self.string(field + ".interactivePath"),
            "interactiveType": self.i32(field + ".interactiveType"),
            "npcId": self.string(field + ".npcId"),
            "performEndNotDestroy": self.boolean(field + ".performEndNotDestroy"),
            "tmpObjectPath": self.string(field + ".tmpObjectPath"),
            "tmpObjectPathHash": self.i64(field + ".tmpObjectPathHash"),
        }

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
        self.i32(field + ".postWrapMode")
        self.i32(field + ".preWrapMode")
        count = self.count(field + ".keys")
        for index in range(count or 0):
            item = f"{field}.keys[{index}]"
            for name in ("inTangent", "inWeight", "outTangent", "outWeight"):
                self.f32(f"{item}.{name}")
            self.f32(item + ".time")
            self.f32(item + ".value")
            self.i32(item + ".weightedMode")

    def f_animation_curve(self, field: str) -> None:
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
        self.f_animation_curve(field + "._customCurve")

    def special_entry(self, field: str) -> None:
        tag = self.u8(field + ".unionTag")
        if tag == 0xFF:
            return
        if tag != 0:
            raise CharInteractPerformDecodeError(
                f"{field}: unsupported special-entry union tag 0x{tag:02x}"
            )
        self.member(3, field)
        condition_count = self.count(field + ".conditions")
        for index in range(condition_count or 0):
            self.special_condition(f"{field}.conditions[{index}]")
        self.string(field + ".memo")
        self.list(field + ".performIds", self.string)

    def special_condition(self, field: str) -> None:
        tag = self.u8(field + ".unionTag")
        if tag != 0:
            raise CharInteractPerformDecodeError(
                f"{field}: unsupported special-condition union tag 0x{tag:02x}"
            )
        self.member(2, field)
        for axis in "xy":
            self.f32(f"{field}.cdTimeRange.{axis}")
        for axis in "xy":
            self.f32(f"{field}.loopWaitTimeRange.{axis}")

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

    def _char_anim(self, field: str) -> dict[str, Any]:
        """Decode and retain the exact CharAnimActionData payload.

        Earlier callers consumed these fields only to prove the cursor.  Keeping
        the values makes the same exact frame useful to animation reconstruction
        without promoting runtime selection or playback.
        """
        anim_name = self.string(field + ".animName")
        auto_blend_out = self.boolean(field + ".autoBlendOut")
        blend_in_time = self.f32(field + ".blendInTime")
        self.alpha_blend(field + ".blendOut")
        flags = {
            name: self.boolean(f"{field}.{name}")
            for name in ("endFalling", "exitFalling", "overrideBlendOut", "overrideStopBlendOut")
        }
        root_motion_wrap_time = self.f32(field + ".rootMotionWrapTime")
        self.transform(field + ".startTransform")
        stop_blend_out_time = self.f32(field + ".stopBlendOutTime")
        flags.update({
            name: self.boolean(f"{field}.{name}")
            for name in ("useAutoTime", "useCurrent", "useRootMotion", "useRootMotionDest")
        })
        return {
            "animName": anim_name,
            "autoBlendOut": auto_blend_out,
            "blendInTime": blend_in_time,
            **flags,
            "rootMotionWrapTime": root_motion_wrap_time,
            "stopBlendOutTime": stop_blend_out_time,
        }

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

    def _effect_play(self, field: str) -> dict[str, Any]:
        """Decode and retain exact effect admission fields from one action."""
        attached_actor_type = self.i32(field + ".attachedActorType")
        char_index = self.i32(field + ".charIndex")
        effect_move_type = self.i32(field + ".effectMoveType")
        init_use_root_rot = self.boolean(field + ".initUseRootRot")
        is_vfx = self.boolean(field + ".isVFX")
        mount_point = self.i32(field + ".mountPoint")
        self.transform(field + ".mountPointOffset")
        not_rot_follow = self.boolean(field + ".notRotFollow")
        show = self.boolean(field + ".show")
        use_char_ik = self.boolean(field + ".useCharIk")
        return {
            "attachedActorType": attached_actor_type,
            "charIndex": char_index,
            "effectMoveType": effect_move_type,
            "initUseRootRot": init_use_root_rot,
            "isVFX": is_vfx,
            "mountPoint": mount_point,
            "notRotFollow": not_rot_follow,
            "show": show,
            "useCharIk": use_char_ik,
        }

    def _npc_montage(self, field: str) -> None:
        self.boolean(field + ".endStop")
        self.member(5, field + ".montageDesc")
        self.i32(field + ".montageDesc.montageMaskType")
        self.i32(field + ".montageDesc.montageState")
        self.u32(field + ".montageDesc.montageTag")
        self.boolean(field + ".montageDesc.overrideMontageState")
        self.boolean(field + ".montageDesc.useRootMotion")

    def _object_show(self, field: str) -> None:
        self.i32(field + ".attachedActorType")
        self.i32(field + ".charIndex")
        self.i32(field + ".mountPoint")
        self.transform(field + ".mountPointOffset")
        self.i32(field + ".objectMoveType")
        self.boolean(field + ".show")
        self.boolean(field + ".useCharIk")

    def action(self, field: str, placement: str, index: int) -> None:
        start = self.offset
        tag = self.u8(field + ".unionTag")
        layout = ACTION_LAYOUTS.get(tag)
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
        actor_index: int | None = None
        if actor_derived:
            actor_index = self.i32(field + ".actorIndex")
        subtype_fields: dict[str, Any] = {}
        if tag == 1:
            self.list(field + ".activeTags", self.gameplay_tag)
            self.boolean(field + ".endRemove")
            self.list(field + ".guardActiveTags", self.gameplay_tag)
        elif tag == 2:
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
            subtype_fields = self._char_anim(field)
        elif tag == 10:
            self.string(field + ".referenceMontageName")
            self.u32(field + ".referenceMontageTag")
            self.i32(field + ".targetActorIndex")
            self.i32(field + ".targetActorType")
            self.i32(field + ".targetType")
            self.boolean(field + ".useMontageLength")
        elif tag == 11:
            self.f32(field + ".forwardSpeed")
            self.boolean(field + ".noHorizontalDampingInAir")
            self.f32(field + ".upSpeed")
        elif tag == 13:
            self.boolean(field + ".applyToAll")
            self.i32(field + ".meshGroup")
            self.boolean(field + ".show")
        elif tag == 14:
            self.i32(field + ".desiredGait")
            self.transform(field + ".targetTransform")
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
        elif tag in (17, 26):
            pass
        elif tag == 18:
            self.animation_curve(field + ".curve")
            self.boolean(field + ".overrideCurve")
            self.transform(field + ".targetTransform")
        elif tag == 20:
            self.i32(field + ".targetState")
            self.list(field + ".weaponIds", self.i32)
        elif tag == 21:
            self.f32(field + ".intensity")
            for axis in "xyz":
                self.f32(f"{field}.offset.{axis}")
            self.f32(field + ".radius")
        elif tag == 23:
            self.string(field + ".animName")
        elif tag == 25:
            subtype_fields = self._effect_play(field)
        elif tag == 29:
            self._npc_montage(field)
        elif tag == 31:
            self.string(field + ".animName")
            self.boolean(field + ".useTrigger")
        elif tag == 32:
            self._object_show(field)
        elif tag == 33:
            self.i32(field + ".interruptType")
            self.boolean(field + ".removeTag")
        elif tag == 35:
            self.transform(field + ".targetTransform")

        action = {
            "sourceOffset": start,
            "endOffset": self.offset,
            "byteLength": self.offset - start,
            "unionTag": tag,
            "unionTagHex": f"0x{tag:04x}",
            "typeName": ACTION_TAG_NAMES[tag],
            "memberCount": member_count,
            "placement": placement,
            "actionIndex": index,
            "actorDerived": actor_derived,
            **base,
        }
        if subtype_fields:
            action["subtypeFields"] = subtype_fields
        if actor_index is not None:
            action["actorIndex"] = actor_index
        self.actions.append(action)

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
        self.owner_actor_collections["chars"] = self.list("chars", self.actor)
        self.owner_actor_collections["decos"] = self.list("decos", self.actor)
        self.special_entry_data("defaultSubPerformEntry")
        self.boolean("disableIKAndFollow")
        self.owner_actor_collections["effects"] = self.list("effects", self.actor)
        self.action_list("endActions", "endActions")
        self.f32("fixedTime")
        self.boolean("forceExitCommandsContinuous")
        self.list("guardActiveTags", self.gameplay_tag)
        self.list("guardInterruptReasons", self.i32)
        self.boolean("hideWeapon")
        self.list("inheritPerformIds", self.string)
        self.owner_actor_collections["interactives"] = self.list("interactives", self.actor)
        self.list("interruptReasons", self.i32)
        self.boolean("keepFightState")
        self.action_list("loopActions", "loopActions")
        self.owner_actor_collections["npcs"] = self.list("npcs", self.actor)
        self.i32("performType")
        self.action_list("preStartActions", "preStartActions")
        self.action_list("startActions", "startActions")
        self.serialized_dictionary("subPerformEntries", self.string, self.special_entry_data)
        self.owner_actor_collections["tmpObjects"] = self.list("tmpObjects", self.actor)
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


def decode_char_interact_complete_frame(data: bytes) -> dict[str, Any]:
    """Validate one complete current-build CharInteractPerform frame.

    Unlike :func:`decode_char_interact_audio_actions`, this entry point is a
    framing gate even when the owner contains no audio action.  It consumes
    the complete 27-member owner and requires the cursor to reach EOF.  The
    returned action rows are only the typed action records that the existing
    reader can prove; unknown action unions remain a hard, reproducible
    failure and are never skipped as opaque bytes.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise CharInteractPerformDecodeError("input: expected bytes-like payload")
    payload = bytes(data)
    reader = _Reader(payload)
    actions = reader.decode()
    return {
        "status": "exact_current_char_interact_frame",
        "schemaStatus": "named_exact",
        "wholeSchemaExact": True,
        "schemaMappingId": SCHEMA_MAPPING_ID,
        "unionMappingId": UNION_MAPPING_ID,
        "serializedMemberCount": OUTER_MEMBER_COUNT,
        "bytesConsumed": len(payload),
        "actionCount": len(reader.actions),
        "actionTypeCounts": {
            name: sum(1 for row in reader.actions if row["typeName"] == name)
            for name in sorted({str(row["typeName"]) for row in reader.actions})
        },
        "actions": reader.actions,
        "actorCollections": reader.owner_actor_collections,
        "audioActionCount": len(actions),
        "audioActions": actions,
        "evidenceBoundary": (
            "The exact current 27-member root and every reached concrete action "
            "wrapper are consumed in generated field order through physical EOF. "
            "The byte-pinned native contract supplies the complete 0..36 tag-to-type "
            "mapping; unknown tags, member counts, or trailing bytes fail closed."
        ),
    }


def frame_char_interact_prefix(data: bytes) -> dict[str, Any]:
    """Validate the first two named root members and leave later unions opaque."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise CharInteractPerformDecodeError("input: expected bytes-like payload")
    reader = _Reader(bytes(data))
    if reader.u8("CharInteractPerformRuntimeCfg.memberCount") != OUTER_MEMBER_COUNT:
        raise CharInteractPerformDecodeError(
            "CharInteractPerformRuntimeCfg member count changed"
        )
    active_tags = reader.list("activeTags", reader.gameplay_tag)
    allow_inherit = reader.boolean("allowInheritPerform")
    return {
        "status": "bounded_prefix",
        "schemaStatus": "named_prefix_opaque_remainder",
        "serializedMemberCount": OUTER_MEMBER_COUNT,
        "bytesConsumed": reader.offset,
        "activeTagCount": len(active_tags),
        "activeTags": active_tags,
        "allowInheritPerform": allow_inherit,
        "opaqueRemainderOffset": reader.offset,
        "opaqueRemainderLength": len(data) - reader.offset,
    }
