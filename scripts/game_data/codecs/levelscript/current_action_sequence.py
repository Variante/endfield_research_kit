"""Exact codec for the current sequential action/getter members.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import math
import struct

from scripts.game_data.codecs.levelscript import action_map as levelscript_action_map
from scripts.game_data.codecs.levelscript import call_server as levelscript_call_server
from scripts.game_data.codecs.levelscript import camera_look_at as levelscript_camera_look_at
from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript import set_enable_player as levelscript_set_enable_player
from scripts.game_data.codecs.levelscript.anonymous_bodies import _read_levelscript_node_envelope
from scripts.game_data.codecs.levelscript.anonymous_bodies import _read_nullable_levelscript_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_entity_ptr_list_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_levelscript_ptr_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_string_collection_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_string_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_u64_param
from scripts.game_data.codecs.levelscript.condition_params import _decode_vector3_param
from scripts.game_data.codecs.levelscript.framing_common import LevelScriptTopLevelFramingError
from scripts.game_data.codecs.levelscript.framing_common import _record_start
from scripts.game_data.codecs.levelscript.framing_common import _round_float
from scripts.game_data.codecs.levelscript.params import decode_bool_param as _decode_bool_param
from scripts.game_data.codecs.levelscript.params import decode_i32_param as _decode_i32_param
from scripts.game_data.codecs.levelscript.params import decode_param_tail as _decode_param_tail
from scripts.game_data.codecs.levelscript.primitives import i32 as _i32
from scripts.game_data.codecs.levelscript.primitives import u32 as _u32
from scripts.game_data.codecs.levelscript.sequential_owner import _frame_levelscript_sequential_owner
from scripts.game_data.codecs.levelscript.uid_records import _decode_levelscript_uid_record
from typing import Any

_CURRENT_SEQUENTIAL_ACTION_MEMBERS = {
    0x001F: (0x11, "BlackScreenFadeIn"),
    0x0015: (0x0A, "AirWallEnable"),
    0x0021: (0x0B, "BlackScreenFadeOut"),
    0x0027: (0x18, "BlendToCameraTransformWithoutBack"),
    0x0026: (0x17, "BlendToCameraTransform"),
    0x0035: (0x0E, "CallServer"),
    0x0053: (0x09, "CheckBoolIfTrue"),
    0x0052: (0x09, "CheckBoolIfFalse"),
    0x0109: (0x0B, "IfElseAction"),
    0x011F: (0x27, "LevelCameraLookAt"),
    0x0312: (0x0A, "ManualStartLevelScript"),
    0x0331: (0x0D, "NpcProxyPatrolStart"),
    0x0358: (0x0B, "PlayAudio"),
    0x036E: (0x0D, "PlayRadio"),
    0x036F: (0x0D, "PlayRadioAndWait"),
    0x0370: (0x11, "PlayRemoteComm"),
    0x0381: (0x0C, "PreloadCutsceneAction"),
    0x038A: (0x0A, "RaiseCustomLevelEvent"),
    0x0392: (0x0E, "RemoveCameraControlState"),
    0x03FF: (0x0B, "SetEnablePlayerAction"),
    0x0496: (0x0A, "ShowSceneDecorationNew"),
    0x049F: (0x0A, "ShowUIToast_DevOnly"),
    0x04A7: (0x09, "Split"),
    0x04B0: (0x0F, "StartDialogAction"),
    0x04B1: (0x10, "StartDialogAndTeleportAction"),
    0x04B5: (0x0A, "StartLevelCustomPerformance"),
    0x04CF: (0x0C, "SwitchInt"),
    0x050F: (0x09, "WaitForNpcProxyReady"),
    0x0511: (0x09, "WaitForSeconds"),
}


def _read_current_action_envelope(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    """Read one current selected ActionBase envelope at an exact cursor."""
    if cursor + 2 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated ActionBase union at offset={cursor}"
        )
    if data[cursor] == 0xFA:
        if cursor + 4 > len(data):
            raise LevelScriptTopLevelFramingError(
                f"truncated extended ActionBase union at offset={cursor}"
            )
        tag = struct.unpack_from("<H", data, cursor + 1)[0]
        member_count = data[cursor + 3]
        uid_offset = cursor + 14
    else:
        tag = data[cursor]
        member_count = data[cursor + 1]
        uid_offset = cursor + 12
    expected = _CURRENT_SEQUENTIAL_ACTION_MEMBERS.get(tag)
    if expected is None or member_count != expected[0]:
        raise LevelScriptTopLevelFramingError(
            "unsupported current ActionBase tag/member count: "
            f"tag=0x{tag:04x} memberCount={member_count}"
        )
    if uid_offset + 8 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated ActionBase uid at offset={uid_offset}"
        )
    raw_uid = data[uid_offset:uid_offset + 8]
    try:
        uid = raw_uid.decode("ascii")
    except UnicodeDecodeError as error:
        raise LevelScriptTopLevelFramingError(
            f"invalid ActionBase uid at offset={uid_offset}"
        ) from error
    record = _decode_levelscript_uid_record(data, uid_offset, uid)
    if record is None or _record_start(record) != cursor:
        raise LevelScriptTopLevelFramingError(
            f"invalid ActionBase envelope at offset={cursor}"
        )
    return {
        **record,
        "action": expected[1],
    }, int(record["payloadStart"])


def _read_current_bool_param(
    data: bytes,
    cursor: int,
    label: str,
) -> tuple[dict[str, Any], int]:
    decoded = _decode_bool_param(data, cursor)
    if decoded is not None:
        return decoded
    if (
        cursor + 14 <= len(data)
        and data[cursor] == 0x04
        and data[cursor + 1] in (0, 1)
        and data[cursor + 10:cursor + 14] == b"\xff" * 4
    ):
        getter_id, source = struct.unpack_from("<ii", data, cursor + 2)
        if 0 <= getter_id <= 0x10000 and source == -1:
            return {
                "value": bool(data[cursor + 1]),
                "idRef": getter_id,
                "paramSource": source,
                "path": None,
            }, cursor + 14
    raise LevelScriptTopLevelFramingError(
        f"unsupported {label} encoding at offset={cursor}"
    )


def _read_current_i32_param(
    data: bytes,
    cursor: int,
    label: str,
) -> tuple[dict[str, Any], int]:
    """Read a current integer Param, including a local-getter reference."""
    decoded = _decode_i32_param(data, cursor)
    if decoded is not None:
        return decoded
    if cursor + 17 > len(data) or data[cursor] != 0x04:
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} encoding at offset={cursor}"
        )
    value, id_ref, source, path_size = struct.unpack_from("<iiii", data, cursor + 1)
    end = cursor + 17
    if not (0 <= id_ref <= 0x10000 and source == -1):
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} reference at offset={cursor}"
        )
    if path_size != -1:
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} path at offset={cursor + 13}"
        )
    return {
        "value": value,
        "idRef": id_ref,
        "paramSource": source,
        "path": None,
    }, end


def _read_current_u8_param(
    data: bytes,
    cursor: int,
    label: str,
) -> tuple[dict[str, Any], int]:
    if cursor + 2 > len(data) or data[cursor] != 0x04:
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} encoding at offset={cursor}"
        )
    tail = _decode_param_tail(data, cursor + 2)
    if tail is None:
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} tail at offset={cursor + 2}"
        )
    detail, end = tail
    return {"value": data[cursor + 1], **detail}, end


def _decode_current_common_mask_blend_param(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the exact current ``Param<CommonMaskBlendData>`` shapes."""
    start = cursor
    if cursor >= len(data):
        return None
    if data[cursor] == 0xFF:
        return {"value": None, "startOffset": start, "endOffset": cursor + 1}, cursor + 1
    if data[cursor] != 0x04 or cursor + 2 > len(data):
        return None
    cursor += 1
    if data[cursor] == 0xFF:
        value: dict[str, Any] | None = None
        cursor += 1
    else:
        if data[cursor] != 0x06 or cursor + 17 > len(data):
            return None
        cursor += 1
        audio = data[cursor:cursor + 16]
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
            return None
        cursor += 16
        if cursor >= len(data):
            return None
        if data[cursor] == 0xFF:
            curve: dict[str, Any] | None = None
            cursor += 1
        elif data[cursor] == 0x03 and cursor + 13 <= len(data):
            post_wrap, pre_wrap, key_count = struct.unpack_from("<iii", data, cursor + 1)
            if key_count != 0:
                return None
            curve = {
                "postWrapMode": post_wrap,
                "preWrapMode": pre_wrap,
                "keys": [],
            }
            cursor += 13
        else:
            return None
        if cursor + 13 > len(data):
            return None
        fade_in, fade_out, mask_type = struct.unpack_from("<ffi", data, cursor)
        use_curve = data[cursor + 12]
        if (
            not math.isfinite(fade_in)
            or not math.isfinite(fade_out)
            or mask_type not in (0, 1, 2, 3)
            or use_curve not in (0, 1)
        ):
            return None
        cursor += 13
        value = {
            "audioBlackScreenBehaviour": {
                "presetBehaviour": preset,
                "customRetainFlags": retain_flags,
                "isOverrideFadeInTime": bool(fade_in_override),
                "overrideFadeInTimeSeconds": _round_float(override_in),
                "isOverrideFadeOutTime": bool(fade_out_override),
                "overrideFadeOutTimeSeconds": _round_float(override_out),
            },
            "curve": curve,
            "fadeInDuration": _round_float(fade_in),
            "fadeOutDuration": _round_float(fade_out),
            "maskType": mask_type,
            "useCurve": bool(use_curve),
        }
    tail = _decode_param_tail(data, cursor)
    if tail is None:
        return None
    binding, cursor = tail
    return {
        "value": value,
        **binding,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor


def _read_current_camera_transform_fields(
    data: bytes,
    cursor: int,
    *,
    without_back: bool,
) -> tuple[dict[str, Any], int]:
    """Read the two current camera-transform action layouts in generated order."""
    start = cursor
    fields: dict[str, Any] = {}
    if cursor + 5 > len(data) or data[cursor] != 0x04:
        raise LevelScriptTopLevelFramingError(
            f"unsupported camera alternativeCameraPoses at offset={cursor}"
        )
    pose_count = _i32(data, cursor + 1)
    if pose_count not in (-1, 0):
        raise LevelScriptTopLevelFramingError(
            f"unsupported camera alternativeCameraPoses count={pose_count}"
        )
    tail = _decode_param_tail(data, cursor + 5)
    if tail is None:
        raise LevelScriptTopLevelFramingError(
            f"unsupported camera alternativeCameraPoses tail at offset={cursor + 5}"
        )
    binding, cursor = tail
    fields["alternativeCameraPoses"] = {
        "value": None if pose_count == -1 else [],
        **binding,
    }

    prefix = (
        (("useAngleMin", _decode_bool_param), ("advancedMode", _decode_bool_param))
        if without_back else
        (
            ("needInterruptMainHudAction", _decode_bool_param),
            ("resetType", _decode_i32_param),
            ("useAngleMin", _decode_bool_param),
        )
    )
    for label, decoder in prefix:
        decoded = decoder(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                f"unsupported camera {label} at offset={cursor}"
            )
        fields[label], cursor = decoded
    fields["blendCurveKey"], cursor = _read_nullable_levelscript_param(
        data, cursor, _decode_i32_param, "camera blendCurveKey"
    )
    suffix: tuple[tuple[str, Any], ...] = (
        ("blendStyle", _decode_i32_param),
        ("duration", levelscript_params.decode_float_param),
        ("fov", levelscript_params.decode_float_param),
    )
    if without_back:
        suffix += (("ignoreProtect", _decode_bool_param),)
    suffix += (
        (("needInterruptMainHudAction", _decode_bool_param),)
        if without_back else ()
    ) + (
        ("overrideBlend", _decode_bool_param),
        ("pos", _decode_vector3_param),
        ("rot", _decode_vector3_param),
        ("sceneViewOverrideFov", _decode_bool_param),
        ("tweenTime", levelscript_params.decode_float_param),
        ("useBlackScreen", _decode_bool_param),
        ("useYawCheck", _decode_bool_param),
    )
    for label, decoder in suffix:
        decoded = decoder(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                f"unsupported camera {label} at offset={cursor}"
            )
        fields[label], cursor = decoded
    fields["consumedBytes"] = cursor - start
    return fields, cursor


def _decode_current_air_wall_ptr_param(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the aligned 24-byte ``AirWallPtr`` constant and Param tail."""
    if cursor + 37 > len(data) or data[cursor] != 0x04:
        return None
    raw = data[cursor + 1:cursor + 25]
    if raw[0] not in (0, 1) or raw[1:8] != b"\x00" * 7 or raw[20:24] != b"\x00" * 4:
        return None
    tail = _decode_param_tail(data, cursor + 25)
    if tail is None:
        return None
    binding, end = tail
    return {
        "logicId": str(struct.unpack_from("<Q", raw, 8)[0]),
        "slotId": struct.unpack_from("<I", raw, 16)[0],
        "useSlotId": bool(raw[0]),
        **binding,
    }, end


def _decode_current_event_args_ptr_param(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode ``Param<EventArgsPtr>`` with its one-member pointer value."""
    if cursor + 6 > len(data) or data[cursor:cursor + 2] != b"\x04\x01":
        return None
    size = _i32(data, cursor + 2)
    cursor += 6
    if size == -1:
        key = None
    elif size is not None and 0 <= size <= 256 and cursor + size <= len(data):
        try:
            key = data[cursor:cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
    else:
        return None
    tail = _decode_param_tail(data, cursor)
    if tail is None:
        return None
    binding, end = tail
    return {"key": key, **binding}, end


def _read_current_action_fields(
    data: bytes,
    cursor: int,
    action: str,
) -> tuple[dict[str, Any], int]:
    """Advance the selected current generated fields for one action."""
    start = cursor
    if action == "CallServer":
        decoded = levelscript_call_server.decode_call_server_action(data[cursor:])
        consumed = decoded.get("consumedBytes") if isinstance(decoded, dict) else None
        if not isinstance(consumed, int) or consumed <= 0:
            raise LevelScriptTopLevelFramingError("CallServer fields did not decode")
        return decoded, cursor + consumed
    if action == "LevelCameraLookAt":
        try:
            return levelscript_camera_look_at.decode_fields(data, cursor)
        except levelscript_camera_look_at.CameraLookAtDecodeError as error:
            raise LevelScriptTopLevelFramingError(str(error)) from error
    if action == "BlackScreenFadeIn":
        fields: dict[str, Any] = {}
        for label, decoder in (
            ("black", _decode_bool_param),
            ("blockInput", _decode_bool_param),
            ("customAudioFlags", None),
            ("duration", levelscript_params.decode_float_param),
            ("presetAudioBehaviour", None),
            ("isOverrideFadeInTime", _decode_bool_param),
            ("isOverrideFadeOutTime", _decode_bool_param),
        ):
            decoded = (
                _read_current_u8_param(data, cursor, f"BlackScreenFadeIn.{label}")
                if decoder is None
                else decoder(data, cursor)
            )
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"unsupported BlackScreenFadeIn.{label} encoding at offset={cursor}"
                )
            fields[label], cursor = decoded
        for label in ("overrideFadeInTimeSeconds", "overrideFadeOutTimeSeconds"):
            fields[label], cursor = _read_nullable_levelscript_param(
                data, cursor, levelscript_params.decode_float_param,
                f"BlackScreenFadeIn.{label}",
            )
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "BlackScreenFadeOut":
        fields: dict[str, Any] = {}
        for label, decoder in (
            ("black", _decode_bool_param),
            ("blockInput", _decode_bool_param),
            ("duration", levelscript_params.decode_float_param),
        ):
            decoded = decoder(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"unsupported BlackScreenFadeOut.{label} encoding at offset={cursor}"
                )
            fields[label], cursor = decoded
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action in ("BlendToCameraTransform", "BlendToCameraTransformWithoutBack"):
        return _read_current_camera_transform_fields(
            data,
            cursor,
            without_back=action == "BlendToCameraTransformWithoutBack",
        )
    if action == "AirWallEnable":
        air_wall = _decode_current_air_wall_ptr_param(data, cursor)
        if air_wall is None:
            raise LevelScriptTopLevelFramingError(
                f"AirWallEnable.airWallPtr did not decode at offset={cursor}"
            )
        air_wall_detail, cursor = air_wall
        enable, cursor = _read_current_bool_param(
            data, cursor, "AirWallEnable.enable"
        )
        return {
            "airWallPtr": air_wall_detail,
            "enable": enable,
            "consumedBytes": cursor - start,
        }, cursor
    if action in ("CheckBoolIfFalse", "CheckBoolIfTrue"):
        value, cursor = _read_current_bool_param(data, cursor, f"{action}.value")
        return {"value": value, "consumedBytes": cursor - start}, cursor
    if action == "IfElseAction":
        condition, cursor = _read_current_bool_param(data, cursor, "IfElseAction.condition")
        if cursor + 8 > len(data):
            raise LevelScriptTopLevelFramingError("truncated IfElseAction branch ids")
        false_id, true_id = struct.unpack_from("<ii", data, cursor)
        if any(value < -1 or value > 0x10000 for value in (false_id, true_id)):
            raise LevelScriptTopLevelFramingError("invalid IfElseAction branch id")
        cursor += 8
        return {
            "condition": condition,
            "onFalseID": false_id,
            "onTrueID": true_id,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "ManualStartLevelScript":
        level_id = _decode_string_param(data, cursor)
        if level_id is None:
            raise LevelScriptTopLevelFramingError(
                f"ManualStartLevelScript.levelId did not decode at offset={cursor}"
            )
        level_id_detail, cursor = level_id
        script_id = _decode_levelscript_ptr_param(data, cursor)
        if script_id is None:
            raise LevelScriptTopLevelFramingError(
                f"ManualStartLevelScript.scriptId did not decode at offset={cursor}"
            )
        script_id_detail, cursor = script_id
        return {
            "levelId": level_id_detail,
            "scriptId": script_id_detail,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "Split":
        if cursor + 4 > len(data):
            raise LevelScriptTopLevelFramingError("truncated Split idList count")
        count = _i32(data, cursor)
        cursor += 4
        if count is None or count < 0 or count > 64 or cursor + count * 4 > len(data):
            raise LevelScriptTopLevelFramingError(f"invalid Split idList count={count}")
        values = list(struct.unpack_from(f"<{count}i", data, cursor)) if count else []
        if any(value < -1 or value > 0x10000 for value in values):
            raise LevelScriptTopLevelFramingError("invalid Split action id")
        cursor += count * 4
        return {"idList": values, "consumedBytes": cursor - start}, cursor
    if action == "SwitchInt":
        lists: list[list[int]] = []
        for label in ("caseIDList", "caseValueList"):
            if cursor + 4 > len(data):
                raise LevelScriptTopLevelFramingError(f"truncated SwitchInt {label}")
            count = _i32(data, cursor)
            cursor += 4
            if count is None or count < 0 or count > 64 or cursor + count * 4 > len(data):
                raise LevelScriptTopLevelFramingError(
                    f"invalid SwitchInt {label} count={count}"
                )
            values = list(struct.unpack_from(f"<{count}i", data, cursor)) if count else []
            cursor += count * 4
            lists.append(values)
        if len(lists[0]) != len(lists[1]) or cursor + 4 > len(data):
            raise LevelScriptTopLevelFramingError("SwitchInt case lists do not align")
        default_id = _i32(data, cursor)
        cursor += 4
        value_detail, cursor = _read_current_i32_param(
            data, cursor, "SwitchInt.value"
        )
        return {
            "caseIDList": lists[0],
            "caseValueList": lists[1],
            "defaultID": default_id,
            "value": value_detail,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "NpcProxyPatrolStart":
        fields: dict[str, Any] = {}
        for label, decoder in (
            ("forceIdle", _decode_bool_param),
            ("levelId", _decode_string_param),
            ("patrolId", _decode_i32_param),
            ("startFromBeginning", _decode_bool_param),
            ("targetProxy", _decode_string_param),
        ):
            decoded = decoder(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"unsupported NpcProxyPatrolStart.{label} at offset={cursor}"
                )
            fields[label], cursor = decoded
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "PlayAudio":
        output = levelscript_params.decode_param_output(data, cursor)
        if output is None:
            raise LevelScriptTopLevelFramingError(
                f"PlayAudio.audioPlayingId did not decode at offset={cursor}"
            )
        output_detail, cursor = output
        key = _decode_string_param(data, cursor)
        if key is None:
            raise LevelScriptTopLevelFramingError(
                f"PlayAudio.key did not decode at offset={cursor}"
            )
        key_detail, cursor = key
        stop_on_release, cursor = _read_current_bool_param(
            data, cursor, "PlayAudio.stopOnRelease"
        )
        return {
            "audioPlayingId": output_detail,
            "key": key_detail,
            "stopOnRelease": stop_on_release,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "PreloadCutsceneAction":
        fields: dict[str, Any] = {}
        decoded = _decode_string_param(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                f"PreloadCutsceneAction.cutsceneId did not decode at offset={cursor}"
            )
        fields["cutsceneId"], cursor = decoded
        fields["isMultiplePreload"], cursor = _read_current_bool_param(
            data, cursor, "PreloadCutsceneAction.isMultiplePreload"
        )
        fields["multiCutsceneId"], cursor = _read_nullable_levelscript_param(
            data, cursor, _decode_string_collection_param,
            "PreloadCutsceneAction.multiCutsceneId",
        )
        fields["showAfterPreloadFinish"], cursor = _read_current_bool_param(
            data, cursor, "PreloadCutsceneAction.showAfterPreloadFinish"
        )
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "RaiseCustomLevelEvent":
        event_args = _decode_current_event_args_ptr_param(data, cursor)
        if event_args is None:
            raise LevelScriptTopLevelFramingError(
                f"RaiseCustomLevelEvent.eventArgsPtr did not decode at offset={cursor}"
            )
        event_args_detail, cursor = event_args
        event_key = _decode_string_param(data, cursor)
        if event_key is None:
            raise LevelScriptTopLevelFramingError(
                f"RaiseCustomLevelEvent.eventKey did not decode at offset={cursor}"
            )
        event_key_detail, cursor = event_key
        return {
            "eventArgsPtr": event_args_detail,
            "eventKey": event_key_detail,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "RemoveCameraControlState":
        fields: dict[str, Any] = {}
        fields["blendCurveKey"], cursor = _read_nullable_levelscript_param(
            data, cursor, _decode_i32_param,
            "RemoveCameraControlState.blendCurveKey",
        )
        for label, decoder in (
            ("blendStyle", _decode_i32_param),
            ("blendTime", levelscript_params.decode_float_param),
        ):
            decoded = decoder(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"RemoveCameraControlState.{label} did not decode at offset={cursor}"
                )
            fields[label], cursor = decoded
        if cursor + 2 > len(data) or data[cursor:cursor + 2] != b"\x04\xff":
            raise LevelScriptTopLevelFramingError(
                f"unsupported RemoveCameraControlState.controlState at offset={cursor}"
            )
        tail = _decode_param_tail(data, cursor + 2)
        if tail is None and data[cursor + 2:cursor + 14] == b"\xff" * 12:
            tail = ({"idRef": -1, "paramSource": -1, "path": None}, cursor + 14)
        if tail is None:
            raise LevelScriptTopLevelFramingError(
                f"invalid RemoveCameraControlState.controlState tail at offset={cursor + 2}"
            )
        binding, cursor = tail
        fields["controlState"] = {"value": None, **binding}
        decoded = _decode_i32_param(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                f"RemoveCameraControlState.controlStateId did not decode at offset={cursor}"
            )
        fields["controlStateId"], cursor = decoded
        fields["overrideBlend"], cursor = _read_current_bool_param(
            data, cursor, "RemoveCameraControlState.overrideBlend"
        )
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action in ("PlayRadio", "PlayRadioAndWait"):
        fields: dict[str, Any] = {}
        for label, decoder in (
            ("fromBegin", _decode_bool_param),
            ("index", _decode_i32_param),
            ("noFlushAfterLoading", _decode_bool_param),
            ("onlyOnce", _decode_bool_param),
            ("radioId", _decode_string_param),
        ):
            decoded = decoder(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"unsupported PlayRadio.{label} encoding at offset={cursor}"
                )
            fields[label], cursor = decoded
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "PlayRemoteComm":
        fields: dict[str, Any] = {}
        for label, decoder in (
            ("fadeInTimeAfter", levelscript_params.decode_float_param),
            ("fadeInTimeBefore", levelscript_params.decode_float_param),
            ("fadeOutTimeAfter", levelscript_params.decode_float_param),
            ("fadeOutTimeBefore", levelscript_params.decode_float_param),
            ("remoteCommId", _decode_string_param),
            ("useBlackScreenAfter", _decode_bool_param),
            ("useBlackScreenBefore", _decode_bool_param),
            ("maskTypeAfter", _decode_i32_param),
            ("maskTypeBefore", _decode_i32_param),
        ):
            decoded = decoder(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"unsupported PlayRemoteComm.{label} encoding at offset={cursor}"
                )
            fields[label], cursor = decoded
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "ShowSceneDecorationNew":
        target = _decode_u64_param(data, cursor)
        if target is None:
            raise LevelScriptTopLevelFramingError(
                "ShowSceneDecorationNew.targetDynamicEntity did not decode"
            )
        target_detail, cursor = target
        visible, cursor = _read_current_bool_param(
            data, cursor, "ShowSceneDecorationNew.visible"
        )
        return {
            "targetDynamicEntity": target_detail,
            "visible": visible,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "ShowUIToast_DevOnly":
        duration = levelscript_params.decode_float_param(data, cursor)
        if duration is None:
            raise LevelScriptTopLevelFramingError(
                f"ShowUIToast_DevOnly.duration did not decode at offset={cursor}"
            )
        duration_detail, cursor = duration
        info = _decode_string_param(data, cursor)
        if info is None:
            raise LevelScriptTopLevelFramingError(
                f"ShowUIToast_DevOnly.info did not decode at offset={cursor}"
            )
        info_detail, cursor = info
        return {
            "duration": duration_detail,
            "info": info_detail,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "SetEnablePlayerAction":
        try:
            return levelscript_set_enable_player.decode_fields(data, cursor)
        except levelscript_set_enable_player.SetEnablePlayerActionDecodeError as error:
            raise LevelScriptTopLevelFramingError(str(error)) from error
    if action == "StartDialogAction":
        fields: dict[str, Any] = {}
        decoded = _decode_string_param(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError("StartDialogAction.dialogId did not decode")
        fields["dialogId"], cursor = decoded
        if cursor < len(data) and data[cursor] == 0xFF:
            fields["existingEnemy"] = None
            cursor += 1
        else:
            decoded = _decode_entity_ptr_list_param(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    "StartDialogAction.existingEnemy did not decode"
                )
            fields["existingEnemy"], cursor = decoded
        fields["shouldWaitForFinish"], cursor = _read_current_bool_param(
            data, cursor, "StartDialogAction.shouldWaitForFinish"
        )
        for label in ("afterMask", "beforeMask"):
            decoded = _decode_current_common_mask_blend_param(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"StartDialogAction.{label} did not decode at offset={cursor}"
                )
            fields[label], cursor = decoded
        for label in ("overrideAfterMaskConfig", "overrideBeforeMaskConfig"):
            if cursor >= len(data):
                raise LevelScriptTopLevelFramingError(
                    f"truncated StartDialogAction.{label} at offset={cursor}"
                )
            if data[cursor] == 0xFF:
                fields[label] = {
                    "value": None,
                    "startOffset": cursor,
                    "endOffset": cursor + 1,
                }
                cursor += 1
            else:
                fields[label], cursor = _read_current_bool_param(
                    data, cursor, f"StartDialogAction.{label}"
                )
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "StartDialogAndTeleportAction":
        fields: dict[str, Any] = {}
        for label in ("afterMask", "beforeMask"):
            decoded = _decode_current_common_mask_blend_param(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"StartDialogAndTeleportAction.{label} did not decode at offset={cursor}"
                )
            fields[label], cursor = decoded
        for label, decoder in (
            ("levelIdStr", _decode_string_param),
            ("position", _decode_vector3_param),
            ("rotationEuler", _decode_vector3_param),
            ("teleportId", _decode_string_param),
        ):
            decoded = decoder(data, cursor)
            if decoded is None:
                raise LevelScriptTopLevelFramingError(
                    f"StartDialogAndTeleportAction.{label} did not decode at offset={cursor}"
                )
            fields[label], cursor = decoded
        fields["teleportUIType"], cursor = _read_nullable_levelscript_param(
            data, cursor, _decode_i32_param,
            "StartDialogAndTeleportAction.teleportUIType",
        )
        decoded = _decode_string_param(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                f"StartDialogAndTeleportAction.dialogId did not decode at offset={cursor}"
            )
        fields["dialogId"], cursor = decoded
        fields["consumedBytes"] = cursor - start
        return fields, cursor
    if action == "StartLevelCustomPerformance":
        allow_unstuck, cursor = _read_nullable_levelscript_param(
            data, cursor, _decode_bool_param,
            "StartLevelCustomPerformance.allowUnstuck",
        )
        handle = levelscript_params.decode_param_output(data, cursor)
        if handle is None:
            raise LevelScriptTopLevelFramingError(
                f"StartLevelCustomPerformance.handle did not decode at offset={cursor}"
            )
        handle_detail, cursor = handle
        return {
            "allowUnstuck": allow_unstuck,
            "handle": handle_detail,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "WaitForSeconds":
        seconds = levelscript_params.decode_float_param(data, cursor)
        if seconds is None:
            raise LevelScriptTopLevelFramingError(
                f"WaitForSeconds.seconds did not decode at offset={cursor}"
            )
        seconds_detail, cursor = seconds
        return {
            "seconds": seconds_detail,
            "consumedBytes": cursor - start,
        }, cursor
    if action == "WaitForNpcProxyReady":
        decoded = _decode_string_param(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                f"WaitForNpcProxyReady.npcProxyId did not decode at offset={cursor}"
            )
        npc_proxy_id, cursor = decoded
        return {
            "npcProxyId": npc_proxy_id,
            "consumedBytes": cursor - start,
        }, cursor
    raise LevelScriptTopLevelFramingError(f"unsupported sequential action={action}")


_CURRENT_SEQUENTIAL_GETTER_MEMBERS = {
    0x0101: (0x09, "GetLevelScriptPropertyGenericBool"),
    0x0130: (0x08, "GetLevelScriptStage"),
}


def _read_current_getter(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    """Read one selected PureGetter envelope and its exact generated fields."""
    start = cursor
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError(f"truncated PureGetter at offset={cursor}")
    if data[cursor] == 0xFA:
        tag = struct.unpack_from("<H", data, cursor + 1)[0]
        member_count = data[cursor + 3]
        prefix = 4
    else:
        tag = data[cursor]
        member_count = data[cursor + 1]
        prefix = 2
    expected = _CURRENT_SEQUENTIAL_GETTER_MEMBERS.get(tag)
    if expected is None or member_count != expected[0]:
        raise LevelScriptTopLevelFramingError(
            "unsupported current PureGetter tag/member count: "
            f"tag=0x{tag:04x} memberCount={member_count}"
        )
    base = cursor + prefix
    if base + 24 > len(data):
        raise LevelScriptTopLevelFramingError("truncated PureGetter NodeBase fields")
    booleans = (data[base], data[base + 5], data[base + 22], data[base + 23])
    if any(value not in (0, 1) for value in booleans):
        raise LevelScriptTopLevelFramingError("invalid PureGetter NodeBase boolean")
    if _u32(data, base + 6) != 8:
        raise LevelScriptTopLevelFramingError("PureGetter uid length mismatch")
    raw_uid = data[base + 10:base + 18]
    if not all(
        ord("0") <= value <= ord("9") or ord("a") <= value <= ord("f")
        for value in raw_uid
    ):
        raise LevelScriptTopLevelFramingError("invalid PureGetter uid")
    cursor = base + 24
    getter = expected[1]
    if getter == "GetLevelScriptStage":
        decoded = _decode_levelscript_ptr_param(data, cursor)
        if decoded is None:
            raise LevelScriptTopLevelFramingError(
                "GetLevelScriptStage.scriptPtr did not decode"
            )
        fields, cursor = decoded
        fields = {"scriptPtr": fields}
    elif getter == "GetLevelScriptPropertyGenericBool":
        path = _decode_string_param(data, cursor)
        if path is None:
            raise LevelScriptTopLevelFramingError(
                "GetLevelScriptPropertyGenericBool.path did not decode"
            )
        path_detail, cursor = path
        target = _decode_levelscript_ptr_param(data, cursor)
        if target is None:
            raise LevelScriptTopLevelFramingError(
                "GetLevelScriptPropertyGenericBool.target did not decode"
            )
        target_detail, cursor = target
        fields = {"path": path_detail, "target": target_detail}
    else:
        raise LevelScriptTopLevelFramingError(f"unsupported sequential getter={getter}")
    return {
        "startOffset": start,
        "endOffset": cursor,
        "unionTag": tag,
        "serializedMemberCount": member_count,
        "getter": getter,
        "uid": raw_uid.decode("ascii"),
        "fields": fields,
    }, cursor


def _read_current_leader_enter_header(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    envelope, cursor = _read_levelscript_node_envelope(
        data, cursor, union_tag=0xBF, member_count=0x12
    )
    fields_start = cursor
    if cursor + 21 > len(data):
        raise LevelScriptTopLevelFramingError("truncated ActionHeader generated fields")
    filter_level = _i32(data, cursor)
    filter_mask = _i32(data, cursor + 4)
    filter_mode = data[cursor + 8]
    next_id = _i32(data, cursor + 9)
    priority = _i32(data, cursor + 13)
    trigger_active_during = _i32(data, cursor + 17)
    if filter_mode not in (0, 1):
        raise LevelScriptTopLevelFramingError("invalid ActionHeader filterMode")
    cursor += 21
    validate, cursor = _read_nullable_levelscript_param(
        data, cursor, _decode_bool_param, "ActionHeader.validate"
    )
    if cursor >= len(data) or data[cursor] != 0xFF:
        raise LevelScriptTopLevelFramingError("unsupported non-null ScriptEvent.targetScript")
    cursor += 1
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError("truncated ScriptEvent.triggerTarget")
    trigger_target = _i32(data, cursor)
    cursor += 4
    slot_filter, cursor = _read_nullable_levelscript_param(
        data, cursor, _decode_i32_param, "triggerSlotIdFilter"
    )
    slot_output, cursor = _read_nullable_levelscript_param(
        data, cursor, levelscript_params.decode_param_output, "triggerSlotIdOutput"
    )
    return {
        "envelope": envelope,
        "header": "ScriptEvent_OnLeaderEnterTriggerVolume",
        "startOffset": envelope["startOffset"],
        "endOffset": cursor,
        "fieldsStartOffset": fields_start,
        "fields": {
            "filterLevel": filter_level,
            "filterMask": filter_mask,
            "filterMode": bool(filter_mode),
            "nextID": next_id,
            "priority": priority,
            "triggerActiveDuring": trigger_active_during,
            "validate": validate,
            "targetScript": None,
            "triggerTarget": trigger_target,
            "triggerSlotIdFilter": slot_filter,
            "triggerSlotIdOutput": slot_output,
        },
    }, cursor


def _read_reviewed_map_node(
    data: bytes, cursor: int, family: str, original_error: ValueError,
) -> tuple[dict[str, Any], int]:
    try:
        return levelscript_action_map.decode_reviewed_node(data, cursor, family)
    except levelscript_action_map.ActionMapCodecError as error:
        raise LevelScriptTopLevelFramingError(
            f"{original_error}; reviewed {family} at offset={cursor}: {error}"
        ) from error


def frame_levelscript_current_action_sequence_leader_enter(
    data: bytes,
) -> dict[str, Any]:
    """Close selected current sequences, including reviewed shared union layouts."""
    if len(data) < 7 or data[:3] != b"\x1b\x02\x03":
        raise LevelScriptTopLevelFramingError("selected action map root/member mismatch")
    action_count = _i32(data, 3)
    if action_count is None or not 0 <= action_count <= 4096:
        raise LevelScriptTopLevelFramingError("invalid selected actionList count")
    cursor = 7
    actions = []
    for _index in range(action_count):
        try:
            envelope, fields_start = _read_current_action_envelope(data, cursor)
            fields, end = _read_current_action_fields(
                data, fields_start, str(envelope["action"])
            )
        except LevelScriptTopLevelFramingError as error:
            action, cursor = _read_reviewed_map_node(
                data, cursor, "ActionBase", error
            )
            actions.append(action)
            continue
        cursor = end
        actions.append({
            "envelope": envelope,
            "action": envelope["action"],
            "fields": fields,
            "startOffset": envelope["start"],
            "endOffset": cursor,
        })
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError("truncated getterList count")
    getter_count = _i32(data, cursor)
    if getter_count is None or getter_count < 0 or getter_count > 4096:
        raise LevelScriptTopLevelFramingError(
            f"invalid selected getterList count={getter_count}"
        )
    cursor += 4
    getters = []
    for _index in range(getter_count):
        try:
            getter, cursor = _read_current_getter(data, cursor)
        except LevelScriptTopLevelFramingError as error:
            getter, cursor = _read_reviewed_map_node(
                data, cursor, "GetterBase", error
            )
        getters.append(getter)
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError("truncated headerList count")
    header_count = _i32(data, cursor)
    if header_count is None or not 0 <= header_count <= 4096:
        raise LevelScriptTopLevelFramingError(
            "invalid selected headerList count: "
            f"actual={header_count}"
        )
    cursor += 4
    headers = []
    for _index in range(header_count):
        try:
            header, cursor = _read_current_leader_enter_header(data, cursor)
        except LevelScriptTopLevelFramingError as error:
            header, cursor = _read_reviewed_map_node(
                data, cursor, "ActionHeader", error
            )
        headers.append(header)
    if cursor + 5 > len(data) or data[cursor] != 1:
        raise LevelScriptTopLevelFramingError("ParamListForGraph member count mismatch")
    param_count = _i32(data, cursor + 1)
    if param_count != 0:
        raise LevelScriptTopLevelFramingError(
            f"selected action sequence requires empty ParamListForGraph: actual={param_count}"
        )
    action_map_end = cursor + 5
    action_map = {
        "startOffset": 1,
        "endOffset": action_map_end,
        "serializedMemberCount": 2,
        "completeAsset": True,
        "dataMap": {
            "startOffset": 2,
            "endOffset": cursor,
            "serializedMemberCount": 3,
            "actionListCount": action_count,
            "getterListCount": getter_count,
            "headerListCount": header_count,
            "actionList": actions,
            "getterList": getters,
            "headerList": headers,
        },
        "paramBlackboard": {
            "startOffset": cursor,
            "endOffset": action_map_end,
            "serializedMemberCount": 1,
            "valueCount": 0,
        },
    }
    return _frame_levelscript_sequential_owner(
        data,
        action_map=action_map,
        owner_offset=action_map_end,
        action_map_boundary="selected current action/getter/header sequence",
        partial_status="exact_named_current_action_sequence_owner_prefix",
    )
