"""Sequential, fail-closed ActionSerializedMap reader for reviewed layouts.

The adjacent byte-pinned contract owns selected-build union identities and
typed field order. This reader never searches for UIDs or guesses a body end.
It establishes stored data, not that an action or event executes at runtime.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from . import params
from . import send_lua_event


CONTRACT_SHA256 = "03f998d07feb23ade1fcac5e9cba0484fa426da59555f70412cfbd234e8e9d57"
CONTRACT_PATH = Path(__file__).with_name("action_map_layouts.json")


class ActionMapCodecError(ValueError):
    """The next declared field has no proven exact cursor."""


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    raw = CONTRACT_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONTRACT_SHA256:
        raise ActionMapCodecError("actionMap.layoutContract:sha256-mismatch")
    contract = json.loads(raw)
    if contract.get("schema") != "endfield.action-map-layouts.v2":
        raise ActionMapCodecError("actionMap.layoutContract:unsupported-schema")
    return contract


@lru_cache(maxsize=1)
def _layouts() -> dict[tuple[str, int], dict[str, Any]]:
    return {(row["family"], row["tag"]): row for row in _contract()["layouts"]}


@lru_cache(maxsize=1)
def _condition_layouts() -> dict[int, dict[str, Any]]:
    return {row["tag"]: row for row in _contract().get("conditionLayouts", [])}


#: Fixed-width primitives a derived declaration can name directly.  These are
#: written raw, with no member-count header, exactly as the reviewed rows read
#: `int32` and `float32`.
_DERIVED_SCALARS = {
    "int8": "<b", "uint8": "<B", "byte": "<B", "sbyte": "<b",
    "int16": "<h", "uint16": "<H", "short": "<h", "ushort": "<H",
    "int": "<i", "uint": "<I", "long": "<q", "ulong": "<Q",
    "int64": "<q", "uint64": "<Q", "uint32": "<I",
    "float32": "<f", "float": "<f", "double": "<d", "char": "<H",
    # A stepped Unity keyframe tangent is +/-Infinity, so this width is read
    # without the finiteness check the ordinary float carries.
    "floatAllowInfinite": "<f",
}


#: Unity math types are plain unmanaged structs written as raw floats.
_UNITY_VECTORS = {
    "Quaternion": ("<ffff", ("x", "y", "z", "w")),
    "Vector4": ("<ffff", ("x", "y", "z", "w")),
    "Vector2Int": ("<ii", ("x", "y")),
    "Vector3Int": ("<iii", ("x", "y", "z")),
    "Color": ("<ffff", ("r", "g", "b", "a")),
    "Color32": ("<BBBB", ("r", "g", "b", "a")),
}


def _align_up(offset: int, alignment: int) -> int:
    """Round `offset` up to a multiple of `alignment`, as .NET lays out fields."""

    if alignment <= 1:
        return offset
    remainder = offset % alignment
    return offset if remainder == 0 else offset + (alignment - remainder)


class _NotDeclared:
    """Sentinel: no derived declaration covers this kind.

    A distinct object rather than `None`, because `None` is a real decoded
    value here -- a null struct or a null list.
    """

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return "<not-declared>"


_NOT_DECLARED = _NotDeclared()


def _split_generic_arguments(text: str) -> list[str]:
    """Split `a,b` at depth zero, so a nested `List<x,y>` stays one argument."""

    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    if current:
        parts.append(current)
    return parts


#: `Beyond.SerializeFieldDictionary<K,V>` and its `Paired`/`Sorted` siblings
#: each have a registered `MemoryPackFormatter`, so their wire form is not the
#: bare counted map that `Dictionary<K,V>` writes: the formatter emits the
#: one-member object header first, and its null is the one-byte `0xff` marker
#: rather than a four-byte `ff ff ff ff` count. `_Cursor.declared_inner` owns
#: that header; these heads are still listed as counted containers so they
#: route there instead of through the generic null marker, which would
#: misread a legitimate count byte.
SERIALIZE_FIELD_DICTIONARY_HEADS = (
    "SerializeFieldDictionary",
    "SerializeFieldDictionaryPaired",
    "SerializeFieldDictionarySorted",
)


def _serialize_field_dictionary_arguments(kind: str) -> list[str] | None:
    """The `K, V` of a `SerializeFieldDictionary`-family kind, or None."""

    for head in SERIALIZE_FIELD_DICTIONARY_HEADS:
        pair = _generic_argument(kind, head)
        if pair is None:
            continue
        arguments = _split_generic_arguments(pair)
        return arguments if len(arguments) == 2 else None
    return None


def _is_counted_container(kind: str) -> bool:
    """Whether a kind is routed to the declared container reader.

    `List<T>`, `T[]` and `Dictionary<K,V>` are written as a nullable count and
    then their elements. The `SerializeFieldDictionary` family carries a
    one-member object header before that count; it is routed here too so the
    generic null marker never sees it.
    """

    if kind.endswith("[]"):
        return True
    if _generic_argument(kind, "Nullable") is not None:
        return False
    return any(
        _generic_argument(kind, head) is not None
        for head in ("List", "Dictionary", *SERIALIZE_FIELD_DICTIONARY_HEADS)
    )


def _generic_argument(kind: str, head: str) -> str | None:
    """The single argument of `head<...>`, or None if `kind` is not that."""

    prefix = head + "<"
    if not kind.startswith(prefix) or not kind.endswith(">"):
        return None
    return kind[len(prefix) : -1]


class Declarations:
    """Derived declarations a caller opts into, at the `direct` tier.

    `scripts.game_data.levelscript_union_layouts` derives the full union table
    plus the structs and enums it refers to from the build's managed image.
    Those rows are corroborated on every reviewed row but are not read from
    the native dispatcher, so they never load by default: a caller passes them
    in, and by doing so accepts that its result is `direct` rather than
    `exact`. Passing nothing leaves this codec byte-identical to the reviewed
    contract alone.
    """

    def __init__(
        self,
        layouts: dict[tuple[str, int], dict[str, Any]],
        structs: dict[str, dict[str, Any]],
        enums: dict[str, str],
    ) -> None:
        self.layouts = layouts
        self.structs = structs
        self.enums = enums

    @classmethod
    def from_report(cls, report: dict[str, Any]) -> "Declarations":
        """Build from a `levelscript_union_layouts` report."""

        if report.get("evidenceBoundary") != "direct":
            raise ActionMapCodecError(
                "actionMap.declarations:unexpected-evidence-boundary="
                f"{report.get('evidenceBoundary')}"
            )
        layouts = {
            (family, row["tag"]): row
            for family, rows in (report.get("families") or {}).items()
            for row in rows
        }
        return cls(layouts, report.get("structs") or {}, report.get("enums") or {})


class _Cursor:
    def __init__(
        self,
        data: bytes,
        offset: int,
        declarations: Declarations | None = None,
    ):
        self.data = data
        self.offset = offset
        self.declarations = declarations

    def need(self, size: int, field: str) -> None:
        if self.offset < 0 or size < 0 or self.offset + size > len(self.data):
            raise ActionMapCodecError(f"{field}:truncated,offset={self.offset},size={size}")

    def byte(self, field: str) -> int:
        self.need(1, field)
        value = self.data[self.offset]
        self.offset += 1
        return value

    def i32(self, field: str) -> int:
        self.need(4, field)
        value = struct.unpack_from("<i", self.data, self.offset)[0]
        self.offset += 4
        return value

    def string(self, field: str) -> str | None:
        size = self.i32(field + ".length")
        if size == -1:
            return None
        if not 0 <= size <= 1 << 20:
            raise ActionMapCodecError(f"{field}:unsupported-length={size}")
        self.need(size, field)
        try:
            value = self.data[self.offset:self.offset + size].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ActionMapCodecError(f"{field}:invalid-utf8,offset={self.offset}") from exc
        self.offset += size
        return value

    def value(self, kind: str, field: str) -> Any:
        if kind == "GameCondition":
            return self.condition(field)
        if kind == "List<GameCondition>":
            count = self.i32(field + ".count")
            if count == -1:
                return None
            if not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            return [self.condition(f"{field}[{index}]") for index in range(count)]
        if kind == "int32":
            return self.i32(field)
        if kind == "string":
            return self.string(field)
        if kind == "bool":
            value = self.byte(field)
            if value not in (0, 1):
                raise ActionMapCodecError(f"{field}:invalid-bool={value}")
            return bool(value)
        if kind == "Vector3":
            self.need(12, field)
            values = struct.unpack_from("<fff", self.data, self.offset)
            self.offset += 12
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return dict(zip(("x", "y", "z"), values))
        if kind == "Vector2":
            self.need(8, field)
            values = struct.unpack_from("<ff", self.data, self.offset)
            self.offset += 8
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return dict(zip(("x", "y"), values))
        if kind == "float32":
            self.need(4, field)
            value = struct.unpack_from("<f", self.data, self.offset)[0]
            self.offset += 4
            if not math.isfinite(value):
                raise ActionMapCodecError(f"{field}:non-finite")
            return value
        if kind == "GameplayTag":
            self.need(4, field)
            value = struct.unpack_from("<I", self.data, self.offset)[0]
            self.offset += 4
            return {"raw": f"0x{value:08x}", "signed": struct.unpack("<i", struct.pack("<I", value))[0]}
        # Derived scalars and counted containers must resolve here, above the
        # generic null marker below. Both start with bytes that marker would
        # misread: an unmanaged byte can legitimately be 0xff, and a null
        # count is 0xff_ff_ff_ff, of which it would swallow exactly one byte.
        if self.declarations is not None:
            scalar = kind
            if scalar in self.declarations.enums:
                scalar = self.declarations.enums[scalar]
            if scalar in _DERIVED_SCALARS:
                return self.scalar(
                    _DERIVED_SCALARS[scalar], field,
                    allow_infinite=scalar == "floatAllowInfinite",
                )
            if _is_counted_container(kind):
                return self.declared_inner(kind, field)
        if kind == "Param<bool>[]":
            count = self.i32(field + ".count")
            if count == -1:
                return None
            if not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            return [self.value("Param<bool>", f"{field}[{index}]") for index in range(count)]
        if kind in ("List<int>", "List<ulong>", "List<string>", "List<Vector3>", "List<float>"):
            count = self.i32(field + ".count")
            if count == -1:
                return None
            if not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            if kind == "List<int>":
                reader = self.i32
            elif kind == "List<ulong>":
                def reader(name: str) -> int:
                    self.need(8, name)
                    value = struct.unpack_from("<Q", self.data, self.offset)[0]
                    self.offset += 8
                    return value
            elif kind == "List<string>":
                reader = self.string
            else:
                reader = lambda name: self.value(
                    "Vector3" if kind == "List<Vector3>" else "float32", name
                )
            return [reader(f"{field}[{index}]") for index in range(count)]
        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        if kind in ("Param<List<PosRot>>", "Param<List<GameplayTag>>"):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                return self.param_tail(None, field)
            if count == 0:
                return self.param_tail([], field)
            if kind == "Param<List<GameplayTag>>":
                # This element layout is still unreviewed; only PosRot is read.
                raise ActionMapCodecError(f"{field}:unsupported-GameplayTag-count={count}")
            if not 0 < count <= 4096:
                raise ActionMapCodecError(f"{field}:unsupported-PosRot-count={count}")
            return self.param_tail(self.pos_rot_list(count, field), field)
        if kind == "Param<CameraControllerBase>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-camera-constant-members={marker}/{value_marker}"
                )
            return self.param_tail(None, field)
        if kind == "Param<CameraBlendCurveKey>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 1:
                raise ActionMapCodecError(
                    f"{field}:unsupported-curve-key-members={marker}/{value_marker}"
                )
            return self.param_tail({"key": self.string(field + ".value.key")}, field)
        if kind == "Param<CameraControlState>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-camera-state-members={marker}/{value_marker}"
                )
            return self.param_tail(None, field)
        if kind == "Param<List<BlackboardKVPair>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                values = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                values = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    members = self.byte(item + ".memberCount")
                    if members != 4:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={members}"
                        )
                    values.append({
                        "key": self.string(item + ".key"),
                        "useString": self.value("bool", item + ".useString"),
                        "valueFloat": self.value("float32", item + ".valueFloat"),
                        "valueString": self.string(item + ".valueString"),
                    })
            return self.param_tail(values, field)
        if kind in (
            "Param<List<int>>", "Param<List<ulong>>", "Param<List<string>>",
            "Param<List<Vector3>>", "Param<List<float>>",
        ):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            value = self.value(kind[6:-1], field + ".value")
            return self.param_tail(value, field)
        if kind == "Param<List<LangKey>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                value = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                value = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    item_marker = self.byte(item + ".memberCount")
                    if item_marker != 1:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={item_marker}"
                        )
                    value.append({"key": self.string(item + ".key")})
            return self.param_tail(value, field)
        if kind == "Param<GameplayTag>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(
                    f"{field}:unsupported-gameplay-tag-param-members={marker}"
                )
            return self.param_tail(
                {"tagId": self.i32(field + ".value.tagId")}, field
            )
        # These enums have signed Int32 underlying types in the reviewed
        # wrappers. Their raw values do not select another wire layout.
        if kind in (
            "Param<BoolComparer>", "Param<NumberComparer>",
            "Param<SP_INTERACTIVE_OP_TYPE>",
            "Param<InteractiveAudioComponent.EAudioTriggerState>",
            "Param<TweenManager.TweenEase>",
            "Param<FacBuildingState>",
            "Param<CinemachineBlendDefinition.Style>",
            "Param<CommonBlendCamResetType>",
            "Param<AudioCueSystem.EBehaviourType>",
            "Param<AudioPlaceholderMusicUtil.EPlaceholderMusicFadeInType>",
            "Param<RadioVoiceAttenuationType>",
            "Param<AudioMusicSystem.EMusicEventPreAction>",
            "Param<LimitedGuideIconType>",
            "Param<LimitedGuideType>",
            "Param<OnQuestStateChanged.FilterQuestStateEnum>",
            "Param<MovementComponent.GroundedMoveGait>",
            "Param<MountPoint>",
            "Param<PlayerController.InputActionType>",
            "Param<EnemyAIModeType>",
            "Param<ENPCAnimationAvatarMaskType>",
            "Param<NPCMontageAnim.EMontageStateType>",
            "Param<MissionSystem.QuestState>",
            "Param<SetCharSkillButtonActive.CharSkillTypeMask>",
            "Param<CharacterAIModeType>",
            "Param<GameAction.EAudioMusicBaseState>",
            "Param<GameAction.EAudioBattleMusicIntensityState>",
            "Param<GameAction.EAudioBattleMusicState>",
            "Param<CompareOperator>",
            "Param<ECharTutorialStepState>",
            "Param<ShowUIToast.ShowToastType>",
            "Param<ForbidType>",
            "Param<GeneralAbilityType>",
            "Param<GeneralAbilitySystem.TempAbilityActiveState>",
            "Param<CastTargetType>",
            "Param<PlayerController.InputActionType>",
        ):
            kind = "Param<int>"
        # Both AudioBlackScreenBehaviour enums explicitly use Byte as their
        # underlying type in the selected generated wrapper.
        if kind in (
            "Param<AudioBlackScreenBehaviour.ERetainFlag>",
            "Param<AudioBlackScreenBehaviour.EPresetBehaviour>",
        ):
            kind = "Param<byte>"
        if kind in (
            "Param<byte>", "Param<uint>", "Param<ulong>",
            "Param<float>", "Param<Vector2>", "Param<Vector3>",
        ):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            if kind in ("Param<Vector2>", "Param<Vector3>"):
                return self.param_tail(
                    self.value(kind[6:-1], field + ".value"), field
                )
            fmt = {
                "Param<byte>": "<B", "Param<uint>": "<I",
                "Param<ulong>": "<Q", "Param<float>": "<f",
            }[kind]
            size = struct.calcsize(fmt)
            self.need(size, field + ".value")
            values = struct.unpack_from(fmt, self.data, self.offset)
            self.offset += size
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return self.param_tail(values[0], field)
        if kind in ("Param<LsmPtr>", "Param<FunctionAreaPtr>"):
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(
                    f"{field}:unsupported-member-count={marker}"
                )
            self.need(8, field + ".value.id")
            value = struct.unpack_from("<Q", self.data, self.offset)[0]
            self.offset += 8
            return self.param_tail({"id": value}, field)
        if kind in ("Param<EventArgsPtr>", "Param<LangKey>", "Param<CameraShakeConfigPtr>"):
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 1:
                raise ActionMapCodecError(
                    f"{field}:unsupported-wrapped-string-members={marker}/{value_marker}"
                )
            return self.param_tail({"key": self.string(field + ".value.key")}, field)
        if kind == "Param<GlobalBuffId>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 1:
                raise ActionMapCodecError(
                    f"{field}:unsupported-global-buff-id-members={marker}/{value_marker}"
                )
            return self.param_tail({"id": self.string(field + ".value.id")}, field)
        if kind == "Param<ObjectPtr<GlobalBuff>>":
            marker = self.byte(field + ".memberCount")
            value_marker = self.byte(field + ".value.memberCount")
            if marker != 4 or value_marker != 2:
                raise ActionMapCodecError(
                    f"{field}:unsupported-global-buff-pointer-members="
                    f"{marker}/{value_marker}"
                )
            self.need(4, field + ".value.cachedUid")
            cached_uid = struct.unpack_from("<I", self.data, self.offset)[0]
            self.offset += 4
            obj_marker = self.byte(field + ".value.obj")
            if obj_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-nonnull-global-buff=0x{obj_marker:02x}"
                )
            return self.param_tail({"cachedUid": cached_uid, "obj": None}, field)
        if kind == "Param<BuffPtr>":
            marker = self.byte(field + ".memberCount")
            buff_ptr_marker = self.byte(field + ".value.memberCount")
            object_ptr_marker = self.byte(field + ".value.ptr.memberCount")
            if (marker, buff_ptr_marker, object_ptr_marker) != (4, 1, 2):
                raise ActionMapCodecError(
                    f"{field}:unsupported-buff-pointer-members="
                    f"{marker}/{buff_ptr_marker}/{object_ptr_marker}"
                )
            self.need(4, field + ".value.ptr.cachedUid")
            cached_uid = struct.unpack_from("<I", self.data, self.offset)[0]
            self.offset += 4
            obj_marker = self.byte(field + ".value.ptr.obj")
            if obj_marker != 0xFF:
                raise ActionMapCodecError(
                    f"{field}:unsupported-nonnull-buff=0x{obj_marker:02x}"
                )
            return self.param_tail(
                {"ptr": {"cachedUid": cached_uid, "obj": None}}, field
            )
        if kind == "Param<List<EntityPtr>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                value = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-entity-list-count={count}")
            else:
                value = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    item_marker = self.byte(item + ".memberCount")
                    if item_marker != 3:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={item_marker}"
                        )
                    self.need(13, item)
                    logic_id, slot_id, use_slot_id = struct.unpack_from(
                        "<QIB", self.data, self.offset
                    )
                    self.offset += 13
                    if use_slot_id not in (0, 1):
                        raise ActionMapCodecError(
                            f"{item}:invalid-use-slot-id={use_slot_id}"
                        )
                    value.append({
                        "logicId": logic_id,
                        "slotId": slot_id,
                        "useSlotId": bool(use_slot_id),
                    })
            tail = params.decode_param_tail(self.data, self.offset)
            if tail is None:
                raise ActionMapCodecError(f"{field}:invalid-param-tail,offset={self.offset}")
            detail, self.offset = tail
            return {"value": value, **detail}
        if kind == "Param<List<NpcProxyOverrideEnvTalk.EnvTalkStruct>>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            count = self.i32(field + ".value.count")
            if count == -1:
                value = None
            elif not 0 <= count <= 10_000:
                raise ActionMapCodecError(f"{field}:unsupported-count={count}")
            else:
                value = []
                for index in range(count):
                    item = f"{field}.value[{index}]"
                    members = self.byte(item + ".memberCount")
                    if members != 2:
                        raise ActionMapCodecError(
                            f"{item}:unsupported-member-count={members}"
                        )
                    value.append({
                        "envTalkId": self.string(item + ".envTalkId"),
                        "odds": self.i32(item + ".odds"),
                    })
            return self.param_tail(value, field)
        if kind == "Param<CommonMaskBlendData>":
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            value_marker = self.byte(field + ".value.memberCount")
            if value_marker == 0xFF:
                return self.param_tail(None, field)
            if value_marker != 6:
                raise ActionMapCodecError(
                    f"{field}:unsupported-value-member-count={value_marker}"
                )
            self.need(16, field + ".value.audioBlackScreenBehaviour")
            audio = self.data[self.offset:self.offset + 16]
            self.offset += 16
            preset, retain_flags = audio[0], audio[1]
            fade_in_override, fade_out_override = audio[2], audio[8]
            override_in = struct.unpack_from("<f", audio, 4)[0]
            override_out = struct.unpack_from("<f", audio, 12)[0]
            if (
                preset not in (0, 1, 2, 64, 65, 128)
                or retain_flags > 0x1F
                or fade_in_override not in (0, 1)
                or fade_out_override not in (0, 1)
                or audio[3] != 0
                or audio[9:12] != b"\x00\x00\x00"
                or not math.isfinite(override_in)
                or not math.isfinite(override_out)
            ):
                raise ActionMapCodecError(
                    f"{field}:unsupported-audio-black-screen-behaviour"
                )
            curve_marker = self.byte(field + ".value.curve.memberCount")
            if curve_marker == 0xFF:
                curve = None
            elif curve_marker == 3:
                post_wrap = self.i32(field + ".value.curve.postWrapMode")
                pre_wrap = self.i32(field + ".value.curve.preWrapMode")
                key_count = self.i32(field + ".value.curve.keys.count")
                if key_count != 0:
                    raise ActionMapCodecError(
                        f"{field}:unsupported-curve-key-count={key_count}"
                    )
                curve = {"postWrapMode": post_wrap, "preWrapMode": pre_wrap, "keys": []}
            else:
                raise ActionMapCodecError(
                    f"{field}:unsupported-curve-member-count={curve_marker}"
                )
            fade_in = self.value("float32", field + ".value.fadeInDuration")
            fade_out = self.value("float32", field + ".value.fadeOutDuration")
            mask_type = self.i32(field + ".value.maskType")
            use_curve = self.byte(field + ".value.useCurve")
            if mask_type not in (0, 1, 2, 3) or use_curve not in (0, 1):
                raise ActionMapCodecError(
                    f"{field}:unsupported-mask={mask_type},useCurve={use_curve}"
                )
            return self.param_tail({
                "audioBlackScreenBehaviour": {
                    "presetBehaviour": preset,
                    "customRetainFlags": retain_flags,
                    "isOverrideFadeInTime": bool(fade_in_override),
                    "overrideFadeInTimeSeconds": override_in,
                    "isOverrideFadeOutTime": bool(fade_out_override),
                    "overrideFadeOutTimeSeconds": override_out,
                },
                "curve": curve,
                "fadeInDuration": fade_in,
                "fadeOutDuration": fade_out,
                "maskType": mask_type,
                "useCurve": bool(use_curve),
            }, field)
        decoder = (
            params.decode_param_output if kind.startswith("ParamOutput<") else {
                "Param<string>": params.decode_string_param,
                "Param<bool>": params.decode_bool_param,
                "Param<int>": params.decode_i32_param,
                "Param<EntityPtr>": params.decode_constant_entity_ptr_param,
                "Param<LevelScriptPtr>": params.decode_levelscript_ptr_param,
            }.get(kind)
        )
        if decoder is None:
            declared = self.declared_value(kind, field)
            if declared is not _NOT_DECLARED:
                return declared
            raise ActionMapCodecError(f"{field}:unsupported-field-type={kind}")
        result = decoder(self.data, self.offset)
        if result is None:
            raise ActionMapCodecError(f"{field}:invalid-{kind},offset={self.offset}")
        detail, self.offset = result
        return detail

    # -- derived-tier decoding ------------------------------------------
    #
    # Everything below reads a shape stated by a derived declaration rather
    # than by the reviewed contract.  It is reached only when a caller passed
    # `Declarations`, and only after the reviewed vocabulary has declined the
    # kind, so the reviewed path's behaviour is unchanged.

    def scalar(self, fmt: str, field: str, *, allow_infinite: bool = False) -> Any:
        size = struct.calcsize(fmt)
        self.need(size, field)
        value = struct.unpack_from(fmt, self.data, self.offset)[0]
        self.offset += size
        if fmt in ("<f", "<d") and not allow_infinite and not math.isfinite(value):
            raise ActionMapCodecError(f"{field}:non-finite")
        return value

    def raw_struct(self, name: str, declared: dict[str, Any], field: str) -> Any:
        """A struct written as raw memory, read at its declared offsets.

        The bytes are the type's memory image, so members sit at the offsets
        its real field order and alignment put them at -- not in serialized
        order, and with padding in between. Padding must be zero: the reviewed
        `Param<LevelScriptPtr>` decoder already requires that of the same eight
        bytes, which is what keeps a mis-sized read from sliding silently.
        """

        layout = declared.get("rawLayout")
        if layout is None:
            raise ActionMapCodecError(
                f"{field}:unresolved-unmanaged-struct-layout={name}"
            )
        base = self.offset
        self.need(layout["size"], field)
        value: dict[str, Any] = {}
        covered = []
        for member, kind, offset, size in layout["fields"]:
            self.offset = base + offset
            value[member] = self.declared_member(kind, f"{field}.{member}")
            if self.offset != base + offset + size:
                raise ActionMapCodecError(
                    f"{field}.{member}:declared-size-mismatch={self.offset - base - offset},"
                    f"expected={size}"
                )
            covered.append((offset, offset + size))
        cursor = 0
        for start, end in sorted(covered):
            if any(self.data[base + cursor : base + start]):
                raise ActionMapCodecError(
                    f"{field}:non-zero-struct-padding,offset={base + cursor}"
                )
            cursor = max(cursor, end)
        if any(self.data[base + cursor : base + layout["size"]]):
            raise ActionMapCodecError(
                f"{field}:non-zero-struct-padding,offset={base + cursor}"
            )
        self.offset = base + layout["size"]
        return value

    def declared_struct(self, name: str, field: str, *, allow_raw: bool = False) -> Any:
        """One declared struct, framed the way its real type requires.

        MemoryPack frames a value holding any reference as an object: a null
        marker or a member count, then the members in declared order. A struct
        holding no reference is written as raw bytes instead, with no marker
        and no count. The reviewed contract already encodes both by hand --
        `Param<EventArgsPtr>` reads a header then a string, `Param<LsmPtr>`
        reads a bare uint64 -- so the framing is a per-type fact, and
        `containsReferences` is where the derivation records it.

        The raw case is only decodable when the struct has a single member.
        With more than one, the bytes are the type's in-memory layout, with
        whatever ordering and padding the runtime chose, and that is not
        something the declaration states. `AirWallPtr` is the live example:
        three unmanaged members whose serialized order is not their field
        order. Those fail closed rather than being read in member order.
        """

        declared = self.declarations.structs[name]
        # A type with no MemoryPack wrapper has no generated object formatter,
        # so the unmanaged formatter writes it raw wherever it appears --
        # collection elements included. `StringPathHash` is one bare int64 and
        # never carries a header.
        always_raw = declared.get("wrapperName") is None
        if (allow_raw or always_raw) and not declared.get("containsReferences", True):
            return self.raw_struct(name, declared, field)
        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        # A SendLuaEvent's nested `manualValue` is the action written by its own
        # formatter, not by the wrapper whose property type the derivation
        # recorded, so the declared member count describes the wrong object.
        # `send_lua_event` owns that shape and why it cannot be derived.
        if send_lua_event.is_send_lua_event(name) and field.endswith(".manualValue"):
            try:
                value, self.offset = send_lua_event.decode_nested_send_lua_event(
                    self.data,
                    self.offset,
                    field,
                    send_lua_event.json_param_count(declared),
                )
            except send_lua_event.SendLuaEventDecodeError as exc:
                raise ActionMapCodecError(str(exc)) from exc
            return value
        members = self.byte(field + ".memberCount")
        if members != declared["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-declared-member-count={members},"
                f"expected={declared['memberCount']}"
            )
        value = {
            member: self.declared_member(kind, f"{field}.{member}")
            for member, kind in declared["fields"]
        }
        if declared.get("provenBoundary") == "empty-collection-only":
            # The declaration's evidence covers only the empty shape. A
            # populated one is a different, unestablished layout, so say so
            # here rather than let a wrong length surface as a desync four
            # members later.
            for member, decoded in value.items():
                if isinstance(decoded, list) and decoded:
                    raise ActionMapCodecError(
                        f"{field}.{member}:unproven-populated-collection="
                        f"{name},count={len(decoded)}"
                    )
        return value

    def declared_member(self, kind: str, field: str) -> Any:
        """One member of an enclosing object, which may be raw.

        A generated formatter writes each member with the writer's own value
        call, so an unmanaged member goes out as raw bytes. A collection
        element takes the element formatter instead, which writes the object
        header -- that is the whole of the difference.
        """

        if self.declarations is not None and kind in self.declarations.structs:
            decoded = self.declared_inner(kind, field, allow_raw=True)
            if decoded is not _NOT_DECLARED:
                return decoded
        return self.value(kind, field)

    def declared_value(self, kind: str, field: str) -> Any:
        """Decode `kind` from a derived declaration, or return the sentinel.

        The cursor has already consumed a leading null marker for the object
        shapes that carry one, so a `Param<...>` here starts at its member
        count. Anything this method does not recognise is handed back, so the
        caller still raises `unsupported-field-type` rather than guessing.
        """

        if self.declarations is None:
            return _NOT_DECLARED
        inner = _generic_argument(kind, "Param")
        if inner is not None:
            marker = self.byte(field + ".memberCount")
            if marker != 4:
                raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
            value = self.declared_inner(inner, field + ".value", allow_raw=True)
            if value is _NOT_DECLARED:
                raise ActionMapCodecError(f"{field}:unsupported-field-type={kind}")
            return self.param_tail(value, field)
        return self.declared_inner(kind, field)

    def declared_inner(self, kind: str, field: str, *, allow_raw: bool = False) -> Any:
        """The value side of a declared type, with no Param envelope.

        `allow_raw` says whether an unmanaged struct here is written as raw
        memory. It is true only directly inside a `Param<T>`: the reviewed
        decoders show `Param<LsmPtr>` reading a bare uint64 and
        `Param<LevelScriptPtr>` reading sixteen raw bytes, while the reviewed
        shape decoder reads a member-count header for every
        `List<LevelScriptShape>` element -- and `LevelScriptShape` is just as
        unmanaged as those. So the framing is decided by where the value sits,
        not by the type alone.
        """

        if kind in self.declarations.enums:
            kind = self.declarations.enums[kind]
        if kind in _DERIVED_SCALARS:
            return self.scalar(
                _DERIVED_SCALARS[kind], field,
                allow_infinite=kind == "floatAllowInfinite",
            )
        if kind in ("bool", "string", "int32", "float32", "Vector2", "Vector3"):
            return self.value(kind, field)
        if kind in _UNITY_VECTORS:
            fmt, names = _UNITY_VECTORS[kind]
            size = struct.calcsize(fmt)
            self.need(size, field)
            values = struct.unpack_from(fmt, self.data, self.offset)
            self.offset += size
            if fmt[-1] == "f" and not all(math.isfinite(v) for v in values):
                raise ActionMapCodecError(f"{field}:non-finite")
            return dict(zip(names, values))
        inner = _generic_argument(kind, "Nullable")
        if inner is not None:
            return self.declared_nullable(inner, field)
        element = _generic_argument(kind, "List")
        if element is not None:
            return self.counted_declared(element, field)
        if kind.endswith("[]"):
            # An array of an unmanaged element takes MemoryPack's unmanaged
            # array path: a count, then the elements as raw memory with no
            # per-element header. `List<T>` does not -- it writes each element
            # through T's own formatter -- so the two are not interchangeable.
            return self.counted_declared(kind[:-2], field, allow_raw=True)
        if any(
            _generic_argument(kind, head) is not None
            for head in SERIALIZE_FIELD_DICTIONARY_HEADS
        ):
            arguments = _serialize_field_dictionary_arguments(kind)
            if arguments is None:
                return _NOT_DECLARED
            return self.serialize_field_dictionary(
                arguments[0], arguments[1], field
            )
        pair = _generic_argument(kind, "Dictionary")
        if pair is not None:
            arguments = _split_generic_arguments(pair)
            if len(arguments) != 2:
                return _NOT_DECLARED
            return self.declared_dictionary(arguments[0], arguments[1], field)
        declared = self.declarations.structs.get(kind)
        if declared is None:
            return _NOT_DECLARED
        if declared.get("isUnionBase"):
            return self.declared_union(kind, field)
        return self.declared_struct(kind, field, allow_raw=allow_raw)

    def pos_rot_list(self, count: int, field: str) -> list[dict[str, Any]]:
        """`List<PosRot>` elements, each written by PosRot's own formatter.

        `List<T>` writes every element through T's formatter rather than as raw
        memory, so each carries its own two-member header before the two
        `Vector3`s -- twenty-five bytes per element, not twenty-four.

        **The two vectors are written eulerAngles first.** `PosRot` declares
        `position` then `eulerAngles`, but `Beyond_PosRotForMemoryPack`'s
        setters are `set___eulerAngles__` then `set___position__`, and the
        generated formatter follows its own member order. The payload agrees:
        read this way the second vector is a map02 world position and the first
        a yaw/pitch/roll, while the declared order gives eulers past 1300
        degrees. Declaration order is not wire order here, the same lesson
        `RunePuzzleData` taught.
        """

        poses: list[dict[str, Any]] = []
        for index in range(count):
            item = f"{field}.value[{index}]"
            members = self.byte(item + ".memberCount")
            if members != 2:
                raise ActionMapCodecError(
                    f"{item}:unsupported-member-count={members}"
                )
            self.need(24, item)
            values = struct.unpack_from("<6f", self.data, self.offset)
            if not all(math.isfinite(value) for value in values):
                raise ActionMapCodecError(f"{item}:non-finite")
            self.offset += 24
            poses.append({
                "eulerAngles": {"x": values[0], "y": values[1], "z": values[2]},
                "position": {"x": values[3], "y": values[4], "z": values[5]},
            })
        return poses

    def declared_nullable(self, inner: str, field: str) -> Any:
        """`T?` for an unmanaged T, written as its raw memory image.

        .NET lays `Nullable<T>` out as a `hasValue` flag followed by the value
        at T's alignment, so a `float?` is eight bytes: the flag, three bytes
        of padding, then the float. The padding must be zero for the same
        reason it must in any other raw struct.
        """

        if inner in self.declarations.enums:
            inner = self.declarations.enums[inner]
        fmt = _DERIVED_SCALARS.get(inner)
        if fmt is None:
            return _NOT_DECLARED
        width = struct.calcsize(fmt)
        self.need(width * 2 if width > 1 else 2, field)
        base = self.offset
        has_value = self.data[base]
        if has_value not in (0, 1):
            raise ActionMapCodecError(f"{field}:invalid-has-value={has_value}")
        if any(self.data[base + 1 : base + width]):
            raise ActionMapCodecError(
                f"{field}:non-zero-nullable-padding,offset={base + 1}"
            )
        self.offset = base + max(width, 1)
        value = self.scalar(fmt, field + ".value")
        return value if has_value else None

    def serialize_field_dictionary(self, key: str, value: str, field: str) -> Any:
        """`Beyond.SerializeFieldDictionary<K,V>`: an object, then a map.

        The type is serialized by a registered `MemoryPackFormatter`, not by a
        generated one, so its member list does not describe the wire. What the
        formatter writes is the ordinary one-member object framing -- a null
        marker or a member count of one -- followed by the same counted map a
        `Dictionary<K,V>` member writes. The reviewed CharInteractPerform
        reader reads exactly that shape and reaches EOF on all 202 current
        owners; reading the header as the map's own count instead consumes
        four bytes where one belongs and desynchronises the rest of the file.
        """

        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        members = self.byte(field + ".memberCount")
        if members != 1:
            raise ActionMapCodecError(
                f"{field}:unsupported-serialize-field-dictionary-member-count="
                f"{members}"
            )
        return self.declared_dictionary(key, value, field)

    def unmanaged_width(self, kind: str) -> int | None:
        """The raw width of an unmanaged kind, or None if it is not one.

        An enum is written as its storage type, so it resolves to that width
        rather than being treated as unknown.
        """

        if self.declarations is not None and kind in self.declarations.enums:
            kind = self.declarations.enums[kind]
        if kind == "bool":
            return 1
        fmt = _DERIVED_SCALARS.get(kind)
        return struct.calcsize(fmt) if fmt else None

    def declared_dictionary(self, key: str, value: str, field: str) -> Any:
        """A counted map: a nullable count, then that many key/value pairs.

        When both sides are unmanaged the pair is a `KeyValuePair<K,V>` struct
        written as raw memory, so it carries .NET's layout padding and not just
        the two values back to back. `Dictionary<ulong,int>` is the case the
        corpus proves: the key is eight bytes, the value four, and the pair is
        sixteen, so every entry ends with four bytes the two fields do not
        account for. Reading them back to back desynchronises by four bytes per
        entry, which is how `RunePuzzleData` surfaced -- its first field after
        the map read a count out of the drifted cursor.

        This is the same shape `SerializeFieldDictionary` already cost four
        bytes per value for, so it is a property of the unmanaged pair rather
        than of one dictionary. The padding must be zero, which keeps the rule
        self-checking: a wrong layout shows up as a refusal rather than as
        plausible values.
        """

        count = self.i32(field + ".count")
        if count == -1:
            return None
        if not 0 <= count <= 100_000:
            raise ActionMapCodecError(f"{field}:unsupported-count={count}")

        key_width = self.unmanaged_width(key)
        value_width = self.unmanaged_width(value)
        value_offset = 0
        pair_size = 0
        if key_width and value_width:
            alignment = max(key_width, value_width)
            value_offset = _align_up(key_width, value_width)
            pair_size = _align_up(value_offset + value_width, alignment)

        entries = []
        for index in range(count):
            item = f"{field}[{index}]"
            start = self.offset
            if pair_size:
                # The whole pair must be present before any of it is read, so
                # the bound is taken from the pair's start rather than from a
                # cursor the key has already moved.
                self.need(pair_size, item)
            decoded_key = self.declared_inner(key, item + ".key")
            if pair_size:
                self._require_zero_padding(start + key_width, start + value_offset, item)
                self.offset = start + value_offset
            decoded_value = self.declared_inner(value, item + ".value")
            if decoded_key is _NOT_DECLARED or decoded_value is _NOT_DECLARED:
                missing = key if decoded_key is _NOT_DECLARED else value
                raise ActionMapCodecError(
                    f"{item}:unsupported-field-type={missing}"
                )
            if pair_size:
                self._require_zero_padding(self.offset, start + pair_size, item)
                self.offset = start + pair_size
            entries.append({"key": decoded_key, "value": decoded_value})
        return entries

    def _require_zero_padding(self, start: int, end: int, field: str) -> None:
        if end > start and any(self.data[start:end]):
            raise ActionMapCodecError(
                f"{field}:non-zero-pair-padding,offset={start}"
            )

    def declared_union(self, family: str, field: str) -> Any:
        """A member declared as a union base: null, or a tag and its members.

        The base type names the family; the tag selects which subtype's
        declaration applies. `LevelScriptTriggerVolumeData` is the reviewed
        example, where tag 1 is the Leader subtype that adds no fields.
        """

        self.need(1, field)
        if self.data[self.offset] == 0xFF:
            self.offset += 1
            return None
        tag = self.byte(field + ".tag")
        if tag == 0xFA:
            self.need(2, field + ".wideTag")
            tag = struct.unpack_from("<H", self.data, self.offset)[0]
            self.offset += 2
        elif tag >= 0xFA:
            raise ActionMapCodecError(
                f"{field}:unsupported-union-marker=0x{tag:02x}"
            )
        members = self.byte(field + ".memberCount")
        layout = self.declarations.layouts.get((family, tag))
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-declared-union={family}#0x{tag:04x},"
                f"memberCount={members}"
            )
        return {
            "unionTag": tag,
            "wrapperName": layout["wrapperName"],
            "fields": {
                member: self.declared_member(kind, f"{field}.{member}")
                for member, kind in layout["fields"]
            },
        }

    def counted_declared(
        self, element: str, field: str, *, allow_raw: bool = False
    ) -> list[Any] | None:
        count = self.i32(field + ".count")
        if count == -1:
            return None
        if not 0 <= count <= 10_000:
            raise ActionMapCodecError(f"{field}:unsupported-count={count}")
        values = []
        for index in range(count):
            item = f"{field}[{index}]"
            if _generic_argument(element, "Param") is not None:
                # A Param element carries its own envelope, so it goes through
                # the ordinary value path and picks up the reviewed decoders.
                values.append(self.value(element, item))
                continue
            decoded = self.declared_inner(element, item, allow_raw=allow_raw)
            if decoded is _NOT_DECLARED:
                raise ActionMapCodecError(
                    f"{item}:unsupported-field-type={element}"
                )
            values.append(decoded)
        return values

    def param_tail(self, value: Any, field: str) -> dict[str, Any]:
        result = params.decode_param_tail(self.data, self.offset)
        if result is None:
            raise ActionMapCodecError(f"{field}:invalid-param-tail,offset={self.offset}")
        detail, self.offset = result
        return {"value": value, **detail}

    def node(self, family: str, field: str) -> dict[str, Any]:
        start = self.offset
        tag = self.byte(field + ".tag")
        if tag == 0xFA:
            self.need(2, field + ".wideTag")
            tag = struct.unpack_from("<H", self.data, self.offset)[0]
            self.offset += 2
        elif tag >= 0xFA:
            raise ActionMapCodecError(f"{field}:unsupported-union-marker=0x{tag:02x}")
        members = self.byte(field + ".memberCount")
        layout = _layouts().get((family, tag))
        if layout is None and self.declarations is not None:
            layout = self.declarations.layouts.get((family, tag))
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-union=0x{tag:04x},memberCount={members},offset={start}"
            )
        values = {name: self.value(kind, field + "." + name) for name, kind in layout["fields"]}
        return {
            "sourceOffset": start, "endOffset": self.offset,
            "unionTag": tag, "memberCount": members,
            "wrapperName": layout["wrapperName"], "fields": values,
        }

    def condition(self, field: str) -> dict[str, Any]:
        start = self.offset
        tag = self.byte(field + ".tag")
        if tag == 0xFA:
            self.need(2, field + ".wideTag")
            tag = struct.unpack_from("<H", self.data, self.offset)[0]
            self.offset += 2
        elif tag >= 0xFA:
            raise ActionMapCodecError(
                f"{field}:unsupported-condition-union-marker=0x{tag:02x}"
            )
        members = self.byte(field + ".memberCount")
        layout = _condition_layouts().get(tag)
        if layout is None and self.declarations is not None:
            layout = self.declarations.layouts.get(("GameCondition", tag))
        if layout is None or members != layout["memberCount"]:
            raise ActionMapCodecError(
                f"{field}:unsupported-condition-union=0x{tag:04x},"
                f"memberCount={members},offset={start}"
            )
        values = {
            name: self.value(kind, field + "." + name)
            for name, kind in layout["fields"]
        }
        return {
            "sourceOffset": start,
            "endOffset": self.offset,
            "unionTag": tag,
            "memberCount": members,
            "wrapperName": layout["wrapperName"],
            "fields": values,
        }


def decode_action_serialized_map(
    data: bytes, offset: int, *, declarations: Declarations | None = None,
) -> tuple[dict[str, Any] | None, int]:
    """Consume a null map or three declared lists.

    With no `declarations` this uses only reviewed codecs and the reviewed
    layout contract, which is the `exact` tier every production consumer
    publishes at. Passing `declarations` additionally admits the derived
    union, struct and enum table; the result is then `direct`, and the caller
    owns saying so.
    """
    cursor = _Cursor(data, offset, declarations)
    marker = cursor.byte("interactiveTemplate.dataMap.memberCount")
    if marker == 0xFF:
        return None, cursor.offset
    if marker != 3:
        raise ActionMapCodecError(f"interactiveTemplate.dataMap.memberCount={marker},expected=3-or-null")
    counts = []
    lists = []
    for index, family in enumerate(("ActionBase", "GetterBase", "ActionHeader")):
        field = f"interactiveTemplate.dataMap.lists[{index}]"
        count_offset = cursor.offset
        count = cursor.i32(field + ".count")
        if not 0 <= count <= 10_000:
            raise ActionMapCodecError(
                f"{field}:unsupported-count={count},countOffset={count_offset},"
                f"payloadOffset={cursor.offset}"
            )
        counts.append(count)
        lists.append([cursor.node(family, f"{field}[{i}]") for i in range(count)])
    result: dict[str, Any] = {"memberCount": 3, "rawListCounts": counts, "empty": not any(counts)}
    if any(counts):
        result.update({"sourceOffset": offset, "endOffset": cursor.offset,
                       "actions": lists[0], "getters": lists[1], "headers": lists[2]})
    return result, cursor.offset


def decode_declared_root(
    data: bytes,
    offset: int,
    root: str,
    declarations: Declarations,
) -> tuple[dict[str, Any], int]:
    """Decode a whole serialized root from its derived declaration.

    `LevelScriptData` is a twenty-seven member MemoryPack type whose members
    are declared in the same place its unions are. Two independently recovered
    framings corroborate the order: the prefix framing proved member zero is
    `actionMap`, and the terminal framing proved the file ends with `scriptId`,
    `startShapeList`, `startType`, `taskMap`, `triggerVolumes` -- which is
    exactly the head and tail of the declared list.

    `ActionSerializedMap` is the one member that routes back to the reviewed
    reader rather than the generic one, because its three declared lists are
    what `decode_action_serialized_map` already owns.
    """

    declared = declarations.structs.get(root)
    if declared is None:
        raise ActionMapCodecError(f"declaredRoot:unknown-type={root}")
    cursor = _Cursor(data, offset, declarations)
    members = cursor.byte(f"{root}.memberCount")
    if members != declared["memberCount"]:
        raise ActionMapCodecError(
            f"{root}:unsupported-member-count={members},"
            f"expected={declared['memberCount']}"
        )
    values: dict[str, Any] = {}
    for member, kind in declared["fields"]:
        field = f"{root}.{member}"
        if kind == "ActionSerializedMap":
            values[member], cursor.offset = decode_action_serialized_map(
                data, cursor.offset, declarations=declarations
            )
            continue
        values[member] = cursor.declared_member(kind, field)
    return {"root": root, "memberCount": members, "fields": values}, cursor.offset


def decode_reviewed_node(
    data: bytes, offset: int, family: str, *, game_root: Path | None = None,
) -> tuple[dict[str, Any], int]:
    """Decode one reviewed union at a declared cursor, with a selected-build gate."""
    inputs = _contract()["nativeInputs"]
    native = check_installed_native_inputs(
        inputs["gameAssembly"]["sha256"], inputs["metadata"]["sha256"],
        gameassembly=game_root.parent / "GameAssembly.dll" if game_root else None,
        metadata=game_root / "il2cpp_data/Metadata/global-metadata.dat" if game_root else None,
    )
    if native.status != "validated":
        raise ActionMapCodecError(
            f"actionMap.installed_native_inputs: expected=validated, "
            f"actual={native.status}, detail={native.detail}"
        )
    if family not in ("ActionBase", "GetterBase", "ActionHeader"):
        raise ActionMapCodecError(f"actionMap:unsupported-family={family}")
    cursor = _Cursor(data, offset)
    result = cursor.node(family, f"actionMap.{family}")
    return result, cursor.offset
