"""Exact codec for the LevelScript audio action payloads.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import math
import struct

from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript.condition_params import _decode_audio_param_tail
from scripts.game_data.codecs.levelscript.condition_params import _decode_quaternion_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_string_collection_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_vector3_param
from scripts.game_data.codecs.levelscript.framing_common import _drop_empty
from scripts.game_data.codecs.levelscript.framing_common import _round_float
from scripts.game_data.codecs.levelscript.record_hints import LEVELSCRIPT_NATIVE_AUDIO_ACTION_MAPPING_ID
from scripts.game_data.codecs.levelscript.record_hints import LEVELSCRIPT_NATIVE_LIST_GET_VALUE_STRING_MAPPING_ID
from typing import Any

def _decode_list_add_value_entity_ptr(payload: bytes) -> dict[str, Any]:
    """Decode one exact ListAddValueEntityPtr property/output chain."""
    if len(payload) < 50 or payload[0] != 0x04 or payload[1:9] != b"\xff" * 8:
        return {}
    list_source = struct.unpack_from("<i", payload, 9)[0]
    list_path_size = struct.unpack_from("<i", payload, 13)[0]
    list_path_start = 17
    list_path_end = list_path_start + list_path_size
    if list_path_size <= 0 or list_path_size > 256 or list_path_end + 29 > len(payload):
        return {}
    try:
        list_path = payload[list_path_start:list_path_end].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    cursor = list_path_end
    if payload[cursor : cursor + 2] != b"\x04\x03":
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    value_id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    value_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    value_path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    value_path_start = cursor + 27
    value_path_end = value_path_start + value_path_size
    if (
        use_slot_id not in (0, 1)
        or value_path_size <= 0
        or value_path_size > 256
        or value_path_end != len(payload)
    ):
        return {}
    try:
        value_path = payload[value_path_start:value_path_end].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    output_match = levelscript_params.PROPERTY_OUTPUT_PATH_RE.match(value_path)
    if not output_match or output_match.group("name") != "entityOutput":
        return {}
    return {
        "action": "ListAddValueEntityPtr",
        "destinationList": {
            "paramSource": list_source,
            "path": list_path,
        },
        "valueEntity": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
            "idRef": value_id_ref,
            "paramSource": value_source,
            "path": value_path,
            "sourceHeaderLocalId": int(output_match.group("local")),
        },
        "payloadShape": "dynamic-list-and-event-entity-output-exact-eof",
    }


def _decode_audio_scalar_param(
    payload: bytes,
    cursor: int,
    value_kind: str,
) -> tuple[dict[str, Any], int] | None:
    """Decode a string/bool/i32/float audio Param with its exact binding."""
    if cursor >= len(payload) or payload[cursor] != 0x04:
        return None
    if value_kind == "string":
        if cursor + 5 > len(payload):
            return None
        size = struct.unpack_from("<i", payload, cursor + 1)[0]
        value_cursor = cursor + 5
        if size == -1:
            value = None
        elif 0 <= size <= 1024 and value_cursor + size <= len(payload):
            try:
                value = payload[value_cursor : value_cursor + size].decode("utf-8")
            except UnicodeDecodeError:
                return None
            value_cursor += size
        else:
            return None
    elif value_kind == "bool":
        if cursor + 2 > len(payload) or payload[cursor + 1] not in (0, 1):
            return None
        value = bool(payload[cursor + 1])
        value_cursor = cursor + 2
    elif value_kind == "i32":
        if cursor + 5 > len(payload):
            return None
        value = struct.unpack_from("<i", payload, cursor + 1)[0]
        value_cursor = cursor + 5
    elif value_kind == "float":
        if cursor + 5 > len(payload):
            return None
        raw_value = struct.unpack_from("<f", payload, cursor + 1)[0]
        if not math.isfinite(raw_value):
            return None
        value = _round_float(raw_value)
        value_cursor = cursor + 5
    else:
        return None
    tail = _decode_audio_param_tail(payload, value_cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def _decode_audio_string_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    return _decode_audio_scalar_param(payload, cursor, "string")


def _decode_audio_bool_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    return _decode_audio_scalar_param(payload, cursor, "bool")


def _decode_audio_i32_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    return _decode_audio_scalar_param(payload, cursor, "i32")


def _decode_audio_float_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    return _decode_audio_scalar_param(payload, cursor, "float")


def _decode_audio_entity_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    decoded = levelscript_params.decode_constant_entity_ptr_param(payload, cursor)
    if decoded is None:
        return None
    detail, end = decoded
    if detail.get("idRef", -2) < -1:
        return None
    if not -1 <= detail.get("paramSource", -2) <= 0x10000:
        return None
    return detail, end


def _decode_list_get_value_string(payload: bytes) -> dict[str, Any]:
    """Decode the installed ``ListGetValueString`` getter fields.

    The generated formatter writes the inherited getter fields first, then
    ``_index`` and ``_list``.  Current direct native setter mapping proves the
    final two fields and the complete active overlay contains two instances of
    this union.  Their index getter starts with the same zero marker followed
    by the shared idRef/source/path tail; the list is the ordinary
    ``Param<List<string>>`` wire shape.
    """
    if not payload or payload[0] != 0:
        return {}
    index_tail = _decode_audio_param_tail(payload, 1)
    if index_tail is None:
        return {}
    index_binding, cursor = index_tail
    list_decoded = _decode_string_collection_param(payload, cursor)
    if list_decoded is None:
        return {}
    list_binding, end = list_decoded
    if end != len(payload):
        return {}

    if (
        isinstance(index_binding.get("idRef"), int)
        and index_binding["idRef"] >= 0
        and index_binding.get("paramSource") == -1
        and index_binding.get("path") is None
    ):
        index_binding = {
            **index_binding,
            "bindingKind": "localGetterRef",
            "getterLocalId": index_binding["idRef"],
        }
    else:
        index_binding = {**index_binding, "bindingKind": "dynamic"}

    list_binding = {
        **list_binding,
        "bindingKind": (
            "constant"
            if list_binding.get("idRef") == -1
            and list_binding.get("paramSource") == 0
            and list_binding.get("path") is None
            else "dynamic"
        ),
    }
    return {
        "index": index_binding,
        "list": list_binding,
        "consumedBytes": end,
        "payloadShape": "list-get-value-string-exact-current-build-memorypack-fields",
        "nativeMappingId": LEVELSCRIPT_NATIVE_LIST_GET_VALUE_STRING_MAPPING_ID,
    }


def _decode_announce_audio_target_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the installed ``AnnounceAudioOnTarget._target`` null shape.

    ``AnnounceAudioOnTarget`` uses the same managed ``Param<EntityPtr>``
    generic as the other target actions, but the current formatter writes its
    unset target as a compact ten-byte reference prefix rather than the
    27-byte ``0x04 0x03`` constant pointer used by ``PlayAudioOnTarget``.
    Every current authored row has this exact shape.  Keep the bytes opaque:
    the prefix proves an unset/indirect target representation, not a concrete
    entity owner or runtime target selection.
    """
    compact_null = b"\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    if payload[cursor : cursor + len(compact_null)] != compact_null:
        return None
    return {
        "serializedShape": "announce-target-compact-null-reference",
        "serializedHex": compact_null.hex(" "),
        "bindingKind": "opaque",
        "targetResolutionStatus": "targetRuntimeResolutionUnresolved",
    }, cursor + len(compact_null)


def _decode_nullable_audio_field(
    payload: bytes,
    cursor: int,
    decoder: Any,
) -> tuple[dict[str, Any], int] | None:
    """Decode a nullable MemoryPack audio-action field.

    ``Param<T>`` and ``ParamOutput<T>`` are reference members. The installed
    blobs serialize an absent member as one ``0xff`` byte and a present member
    with its ordinary typed formatter.
    """
    # AnnounceAudioOnTarget's target formatter has an exact ten-byte null
    # representation beginning with 0xff; let its dedicated decoder consume
    # that shape instead of truncating it to the generic one-byte null marker.
    if (
        decoder is not _decode_announce_audio_target_param
        and cursor < len(payload)
        and payload[cursor] == 0xFF
    ):
        return {"present": False, "bindingKind": "null"}, cursor + 1
    decoded = decoder(payload, cursor)
    if decoded is None:
        return None
    detail, end = decoded
    detail = {"present": True, **detail}
    if "idRef" in detail:
        detail["bindingKind"] = (
            "constant"
            if detail.get("idRef") == -1
            and detail.get("paramSource") == 0
            and detail.get("path") is None
            else "dynamic"
        )
    elif "bindingKind" not in detail:
        detail["bindingKind"] = "output"
    return detail, end


def _finish_audio_action_fields(
    payload: bytes,
    end: int,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Accept exact audio fields plus proven outer ActionMap list framing.

    The final physical action in a serialized list can be followed, before
    the next UID record, by one list count or by an empty-list count and the
    following list count. Those u32 values are container framing, not action
    fields. Current installed records use only these three bounded forms.
    """
    trailer = payload[end:]
    framing: list[int] = []
    if not trailer:
        pass
    elif len(trailer) == 4:
        framing = [struct.unpack_from("<I", trailer, 0)[0]]
    elif len(trailer) == 8 and trailer[:4] == b"\x00\x00\x00\x00":
        framing = list(struct.unpack_from("<II", trailer, 0))
    else:
        return {}
    if any(value > 0x10000 for value in framing):
        return {}
    out = {
        **detail,
        "consumedBytes": end,
        "payloadShape": "audio-action-exact-current-build-memorypack-fields",
        "nativeMappingId": LEVELSCRIPT_NATIVE_AUDIO_ACTION_MAPPING_ID,
    }
    if framing:
        out["trailingActionMapFramingU32s"] = framing
    return out


def _decode_audio_action(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode the installed high-yield ActionBase audio field layouts.

    The union tag/member-count pair selects one exact generated MemoryPack
    formatter. Every declared derived member is decoded in generated-setter
    order. Literal Event/cue bindings are emitted only for constant string
    parameters; dynamic parameters retain idRef/source/path evidence without
    being promoted to an authored name.
    """
    layouts: dict[
        tuple[int, int],
        tuple[str, tuple[tuple[str, Any], ...]],
    ] = {
        # These actions have no derived serialized fields in the current
        # MemoryPack payload.  The record can still carry the bounded
        # ActionMap list framing accepted by _finish_audio_action_fields.
        (0x00B7, 0x08): ("ExitCustomMusicMode", ()),
        (0x0016, 0x09): (
            "AnnounceAudioOnTarget",
            (
                ("target", _decode_announce_audio_target_param),
                ("audioKey", _decode_audio_string_param),
            ),
        ),
        (0x0028, 0x09): (
            "BlockAutoMusicChange",
            (("blockHandle", levelscript_params.decode_param_output),),
        ),
        (0x0029, 0x09): (
            "BlockAutoMusicChangeCancel",
            (("blockHandle", _decode_audio_i32_param),),
        ),
        (0x002A, 0x09): (
            "BlockBattleMusic",
            (("block", _decode_audio_bool_param),),
        ),
        (0x0089, 0x0B): (
            "EnterCustomMusicMode",
            (
                ("allowCombatMusic", _decode_audio_bool_param),
                ("audioEvent", _decode_audio_string_param),
                ("autoExitOnRelease", _decode_audio_bool_param),
            ),
        ),
        (0x0306, 0x09): (
            "ManualRestoreMusicState",
            (
                ("delay", _decode_audio_float_param),
            ),
        ),
        (0x0307, 0x0B): (
            "ManualSetMusicState",
            (
                ("baseState", _decode_audio_i32_param),
                ("battleIntensityState", _decode_audio_i32_param),
                ("battleState", _decode_audio_i32_param),
            ),
        ),
        (0x034C, 0x0C): (
            "PlayAudiAtPosition",
            (
                ("audioPlayingId", levelscript_params.decode_param_output),
                ("key", _decode_audio_string_param),
                ("position", _decode_vector3_param),
                ("stopOnRelease", _decode_audio_bool_param),
            ),
        ),
        (0x034E, 0x0B): (
            "PlayAudio",
            (
                ("audioPlayingId", levelscript_params.decode_param_output),
                ("key", _decode_audio_string_param),
                ("stopOnRelease", _decode_audio_bool_param),
            ),
        ),
        (0x034F, 0x10): (
            "PlayAudioAndWait",
            (
                ("eventName", _decode_audio_string_param),
                ("playCompleteThreshold", _decode_audio_float_param),
                ("playingId", levelscript_params.decode_param_output),
                ("playType", _decode_audio_i32_param),
                ("position", _decode_vector3_param),
                ("stopAudioOnRelease", _decode_audio_bool_param),
                ("targetEntity", _decode_audio_entity_param),
                ("targetProxy", _decode_audio_string_param),
            ),
        ),
        (0x034A, 0x14): (
            "Play3DRadio",
            (
                ("attenuationType", _decode_audio_i32_param),
                ("enableAdvancedOptions", _decode_audio_bool_param),
                ("entityPtr", _decode_audio_entity_param),
                ("fromBegin", _decode_audio_bool_param),
                ("index", _decode_audio_i32_param),
                ("noFlushAfterLoading", _decode_audio_bool_param),
                ("npcProxyId", _decode_audio_string_param),
                ("onlyOnce", _decode_audio_bool_param),
                ("radioId", _decode_audio_string_param),
                ("reverbOffset", _decode_audio_float_param),
                ("useNpcProxy", _decode_audio_bool_param),
                ("voOffset", _decode_audio_float_param),
            ),
        ),
        (0x034B, 0x14): (
            "Play3DRadioAndWait",
            (
                ("attenuationType", _decode_audio_i32_param),
                ("enableAdvancedOptions", _decode_audio_bool_param),
                ("entityPtr", _decode_audio_entity_param),
                ("fromBegin", _decode_audio_bool_param),
                ("index", _decode_audio_i32_param),
                ("noFlushAfterLoading", _decode_audio_bool_param),
                ("npcProxyId", _decode_audio_string_param),
                ("onlyOnce", _decode_audio_bool_param),
                ("radioId", _decode_audio_string_param),
                ("reverbOffset", _decode_audio_float_param),
                ("useNpcProxy", _decode_audio_bool_param),
                ("voOffset", _decode_audio_float_param),
            ),
        ),
        (0x0352, 0x0C): (
            "PlayAudioOnTarget",
            (
                ("audioKey", _decode_audio_string_param),
                ("audioPlayingId", levelscript_params.decode_param_output),
                ("stopOnRelease", _decode_audio_bool_param),
                ("target", _decode_audio_entity_param),
            ),
        ),
        (0x0367, 0x11): (
            "PlayStandaloneMusic",
            (
                ("handleId", levelscript_params.decode_param_output),
                ("playKey", _decode_audio_i32_param),
                ("playType", _decode_audio_i32_param),
                ("position", _decode_vector3_param),
                ("rotation", _decode_quaternion_param),
                ("size", _decode_vector3_param),
                ("startEvent", _decode_audio_string_param),
                ("stopEvent", _decode_audio_string_param),
                ("stopOnRelease", _decode_audio_bool_param),
            ),
        ),
        (0x0368, 0x0B): (
            "PlayVoice",
            (
                ("target", _decode_audio_entity_param),
                ("voiceHandle", levelscript_params.decode_param_output),
                ("voId", _decode_audio_string_param),
            ),
        ),
        (0x0369, 0x0A): (
            "PlayVoiceNarrative",
            (
                ("voiceHandle", levelscript_params.decode_param_output),
                ("voId", _decode_audio_string_param),
            ),
        ),
        (0x0363, 0x0D): (
            "PlayRadio",
            (
                ("fromBegin", _decode_audio_bool_param),
                ("index", _decode_audio_i32_param),
                ("noFlushAfterLoading", _decode_audio_bool_param),
                ("onlyOnce", _decode_audio_bool_param),
                ("radioId", _decode_audio_string_param),
            ),
        ),
        (0x0364, 0x0D): (
            "PlayRadioAndWait",
            (
                ("fromBegin", _decode_audio_bool_param),
                ("index", _decode_audio_i32_param),
                ("noFlushAfterLoading", _decode_audio_bool_param),
                ("onlyOnce", _decode_audio_bool_param),
                ("radioId", _decode_audio_string_param),
            ),
        ),
        (0x036B, 0x13): (
            "PostAudioCue",
            (
                ("behaviourType", _decode_audio_i32_param),
                ("boolParam", _decode_audio_bool_param),
                ("boolParam1", _decode_audio_bool_param),
                ("boolParam2", _decode_audio_bool_param),
                ("cueHandlerId", levelscript_params.decode_param_output),
                ("floatParam", _decode_audio_float_param),
                ("intParam", _decode_audio_i32_param),
                ("name", _decode_audio_string_param),
                ("placeholderMusicFadeInType", _decode_audio_i32_param),
                ("stringParam", _decode_audio_string_param),
                ("volume0To10", _decode_audio_float_param),
            ),
        ),
        (0x036E, 0x14): (
            "PostAudioCueOnRelease",
            (
                ("behaviourType", _decode_audio_i32_param),
                ("boolParam", _decode_audio_bool_param),
                ("boolParam1", _decode_audio_bool_param),
                ("boolParam2", _decode_audio_bool_param),
                ("cueHandlerId", levelscript_params.decode_param_output),
                ("floatParam", _decode_audio_float_param),
                ("intParam", _decode_audio_i32_param),
                ("name", _decode_audio_string_param),
                ("placeholderMusicFadeInType", _decode_audio_i32_param),
                ("stringParam", _decode_audio_string_param),
                ("volume0To10", _decode_audio_float_param),
                ("onlyIfExecuted", _decode_audio_bool_param),
            ),
        ),
        (0x0371, 0x0B): (
            "PostAudioStatusEvent",
            (
                ("onlyTriggerExitAfterNodeTriggered", _decode_audio_bool_param),
                ("statusEnterEvent", _decode_audio_string_param),
                ("statusExitEvent", _decode_audio_string_param),
            ),
        ),
        (0x0373, 0x0C): (
            "PostMusicEvent",
            (
                ("musicEvent", _decode_audio_string_param),
                ("musicEventOnRelease", _decode_audio_string_param),
                ("musicEventType", _decode_audio_i32_param),
                ("playingId", levelscript_params.decode_param_output),
            ),
        ),
        (0x03D5, 0x0F): (
            "SetAudioCueVar",
            (
                ("boolValue", _decode_audio_bool_param),
                ("floatValue", _decode_audio_float_param),
                ("intValue", _decode_audio_i32_param),
                ("scope", _decode_audio_i32_param),
                ("stringValue", _decode_audio_string_param),
                ("varName", _decode_audio_string_param),
                ("varType", _decode_audio_i32_param),
            ),
        ),
        (0x0372, 0x08): ("PostAudioStopAllEnemyVoice", ()),
        (0x04A7, 0x0E): (
            "StartPlaceholderMusic_DevOnly",
            (
                ("musicId", _decode_audio_i32_param),
                ("placeholderMusicFadeInType", _decode_audio_i32_param),
                ("seekPositionSeconds", _decode_audio_float_param),
                ("stopOnDialogEnd", _decode_audio_bool_param),
                ("stopOnLoading", _decode_audio_bool_param),
                ("volume", _decode_audio_float_param),
            ),
        ),
        (0x04AC, 0x0A): (
            "StopAudio",
            (
                ("audioId", _decode_audio_i32_param),
                ("fadeTimeMs", _decode_audio_i32_param),
            ),
        ),
        (0x04B4, 0x0B): (
            "StopPlaceholderMusic_DevOnly",
            (
                ("fadeOutTimeSeconds", _decode_audio_float_param),
                ("musicId", _decode_audio_i32_param),
                ("stopSpecificMusic", _decode_audio_bool_param),
            ),
        ),
        (0x04B5, 0x09): (
            "StopRadio",
            (
                ("radioId", _decode_audio_string_param),
            ),
        ),
        (0x04B7, 0x0A): (
            "StopVoice",
            (
                ("fadeOutTime", _decode_audio_i32_param),
                ("voiceHandle", _decode_audio_i32_param),
            ),
        ),
        (0x04BA, 0x09): (
            "SwitchAIBarkEnable",
            (
                ("enable", _decode_audio_bool_param),
            ),
        ),
        (0x04BC, 0x0B): (
            "SwitchAudioState",
            (
                ("modelLevel", _decode_audio_i32_param),
                ("target", _decode_audio_entity_param),
                ("value", _decode_audio_i32_param),
            ),
        ),
        (0x04CA, 0x09): (
            "ToggleClearScreenButRadio",
            (
                ("isShow", _decode_audio_bool_param),
            ),
        ),
        (0x00E9, 0x08): ("FlushRadio", ()),
    }
    layout = layouts.get(semantic_key)
    if layout is None:
        return {}
    action_name, serialized_fields = layout
    cursor = 0
    fields: dict[str, dict[str, Any]] = {}
    for field_name, decoder in serialized_fields:
        decoded = _decode_nullable_audio_field(payload, cursor, decoder)
        if decoded is None:
            return {}
        field_detail, cursor = decoded
        fields[field_name] = {
            "sourceField": f"_{field_name}",
            **field_detail,
        }

    event_roles = {
        "AnnounceAudioOnTarget": (("audioKey", "announceTarget"),),
        "EnterCustomMusicMode": (("audioEvent", "customMusic"),),
        "PlayAudiAtPosition": (("key", "play"),),
        "PlayAudio": (("key", "play"),),
        "PlayAudioAndWait": (("eventName", "play"),),
        "PlayAudioOnTarget": (("audioKey", "play"),),
        "PlayStandaloneMusic": (
            ("startEvent", "standaloneStart"),
            ("stopEvent", "standaloneStop"),
        ),
        "PostAudioStatusEvent": (
            ("statusEnterEvent", "statusEnter"),
            ("statusExitEvent", "statusExit"),
        ),
        "PostMusicEvent": (
            ("musicEvent", "post"),
            ("musicEventOnRelease", "release"),
        ),
    }
    event_bindings = []
    for field_name, role in event_roles.get(action_name, ()):
        field = fields[field_name]
        value = field.get("value")
        if (
            field.get("bindingKind") == "constant"
            and isinstance(value, str)
            and value
        ):
            event_bindings.append({
                "eventName": value,
                "role": role,
                "sourceField": field["sourceField"],
            })
    voice_bindings = []
    for field_name, role in {
        "PlayVoice": (("voId", "voice"),),
        "PlayVoiceNarrative": (("voId", "voiceNarrative"),),
    }.get(action_name, ()):
        field = fields[field_name]
        value = field.get("value")
        if (
            field.get("bindingKind") == "constant"
            and isinstance(value, str)
            and value
        ):
            voice_bindings.append({
                "voiceId": value,
                "role": role,
                "sourceField": field["sourceField"],
                "identityKind": "AudioDialogPathStem",
                "wwiseEventStatus": "notApplicable",
            })
    cue_bindings = []
    if action_name.startswith("PostAudioCue"):
        field = fields["name"]
        value = field.get("value")
        if field.get("bindingKind") == "constant" and isinstance(value, str) and value:
            cue_bindings.append({
                "cueName": value,
                "role": "invoke",
                "sourceField": field["sourceField"],
            })
    radio_bindings = []
    radio_roles = {
        "Play3DRadio": "play3D",
        "Play3DRadioAndWait": "play3DAndWait",
        "PlayRadio": "play",
        "PlayRadioAndWait": "playAndWait",
        "StopRadio": "stop",
    }
    radio_role = radio_roles.get(action_name)
    if radio_role:
        field = fields["radioId"]
        value = field.get("value")
        if field.get("bindingKind") == "constant" and isinstance(value, str) and value:
            radio_bindings.append({
                "radioId": value,
                "role": radio_role,
                "sourceField": field["sourceField"],
            })

    return _finish_audio_action_fields(payload, cursor, _drop_empty({
        "action": action_name,
        "fields": fields,
        "eventBindings": event_bindings,
        "voiceBindings": voice_bindings,
        "cueBindings": cue_bindings,
        "radioBindings": radio_bindings,
    }))
