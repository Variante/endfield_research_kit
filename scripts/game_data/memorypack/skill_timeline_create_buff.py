"""Exact current-build SkillData first-timeline CreateBuffAction framing.

Physical union tag ``0x0092`` selects the current member-19 CreateBuffAction
wrapper.  The decoder always closes and names the first action.  It closes the
containing first TimelineActionData only when that SequenceActionData contains
one action; later actions are never searched for or skipped heuristically.
"""
from __future__ import annotations

import json
import struct
from functools import lru_cache
from typing import Any, Callable

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import Reader


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_create_buff_native.json"
LABEL = "skillTimelineCreateBuff"
CREATE_BUFF_TAG = 0x0092


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-create-buff-native-contract.v1", label=LABEL
    )
    return value


@lru_cache(maxsize=1)
def _dependency_contract() -> dict[str, Any]:
    dependency = _contract()["dependencies"][0]
    return json.loads((CONTRACT_PATH.parent / dependency["path"]).read_bytes())


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the dispatcher, generated setters, and all nested readers."""
    contract = _contract()
    dependency = _dependency_contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    dispatcher = contract["dispatcher"]
    image.validate_dispatcher(dispatcher, label=LABEL)
    validated_methods = [image.validate_method_row(row, label=LABEL) for row in dependency["methods"]]
    image.check_windows([*dependency["codeWindows"], *dependency["dataWindows"]], gate="window", label=LABEL)
    for context in dependency["nestedContexts"]:
        image.nested_usage_cell(context, label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    expected_setters = [row[:3] for row in contract["wrapper"]["setterMethods"]]
    if image.setter_methods(owner, parameter="typeIndex", label=LABEL) != expected_setters:
        raise ValueError(f"{LABEL}.native:setter-order")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "unionTag": dispatcher["unionTag"],
        "methodIndices": validated_methods,
    }


def _mark(
    reader: Reader,
    ranges: list[dict[str, Any]],
    name: str,
    kind: str,
    callback: Callable[[], Any],
) -> Any:
    start = reader.pos
    value = callback()
    if reader.pos <= start:
        raise ValueError(f"skillTimelineCreateBuff.{name}:no-progress")
    ranges.append({"name": name, "start": start, "end": reader.pos, "kind": kind})
    return value


def _take_i32(reader: Reader, kind: str = "int32") -> int:
    return struct.unpack("<i", reader.take(4, kind))[0]


def _take_header(reader: Reader, expected: int) -> int:
    reader.header(expected)
    return expected


def _decode_create_buff_action(
    reader: Reader, ranges: list[dict[str, Any]]
) -> dict[str, Any]:
    start = reader.pos
    tag = _mark(
        reader,
        ranges,
        "timeline.sequence.actionData[0].unionTag",
        "AbilityActionData.union-tag",
        lambda: reader.take(1, "union-tag")[0],
    )
    if tag != CREATE_BUFF_TAG:
        raise ValueError(
            f"skillTimelineCreateBuff.unionTag={tag:#04x} expected=0x92"
        )
    _mark(
        reader,
        ranges,
        "timeline.sequence.actionData[0].memberCount",
        "CreateBuffAction.member-count",
        lambda: _take_header(reader, 19),
    )
    fields: list[dict[str, Any]] = []

    def field(name: str, kind: str, callback: Callable[[], Any]) -> Any:
        before = len(ranges)
        value = _mark(
            reader,
            ranges,
            f"timeline.sequence.actionData[0].createBuff.{name}",
            kind,
            callback,
        )
        span = ranges[-1]
        if len(ranges) != before + 1:
            raise ValueError(f"skillTimelineCreateBuff.{name}:range-accounting")
        fields.append({
            "fieldName": name,
            "start": span["start"],
            "end": span["end"],
            "kind": kind,
        })
        return value

    field("isEnable", "bool-byte", lambda: reader.take(1, "bool-byte"))
    field("priorityLevel", "enum-int32", lambda: reader.take(4, "enum-int32"))
    field("priorityOffset", "int32", lambda: reader.take(4, "int32"))
    field("serverActionIndex", "int32", lambda: reader.take(4, "int32"))
    field("asChildBuff", "bool-byte", lambda: reader.take(1, "bool-byte"))
    field("autoFinishByAction", "bool-byte", lambda: reader.take(1, "bool-byte"))
    field(
        "buffIconDurationSource",
        "BuffIconDurationSourceSetting",
        reader.scalar_bytes_profile,
    )

    def buffs() -> int:
        count = reader.count(1, reserve=20, nullable=True)
        for _ in range(max(0, count)):
            reader.input_profile()
        return count

    field("buffs", "List<CreateBuffActionInput>", buffs)
    field("buffSource", "ActionTargetType-int32", lambda: reader.take(4, "int32"))
    field("contextKey", "signed-length-string-bytes", reader.byte_payload)
    field("count", "BlackboardDouble", reader.scalar_payload)
    field(
        "finishWithNextSkillIfNotInherited",
        "bool-byte",
        lambda: reader.take(1, "bool-byte"),
    )

    def inherited_skill_ids() -> int:
        count = reader.count(4, reserve=6, nullable=True)
        for _ in range(max(0, count)):
            reader.byte_payload()
        return count

    field("inheritSkillIdList", "List<signed-length-string-bytes>", inherited_skill_ids)
    for name in (
        "inheritSourceSkillCastId",
        "inheritSourceSkillCastInfo",
        "isExtra",
        "overrideBuffIconDuration",
        "passTargetGroupsToBuff",
    ):
        field(name, "bool-byte", lambda: reader.take(1, "bool-byte"))
    field("targetSettings", "TargetSettings", reader.target_profile)
    return {
        "tag": CREATE_BUFF_TAG,
        "typeName": _contract()["wrapper"]["typeName"],
        "start": start,
        "end": reader.pos,
        "memberCount": 19,
        "fields": fields,
        "wholeActionExact": True,
    }


def decode_first_timeline_create_buff(
    data: bytes,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Decode the first CreateBuff action and, when sole, its timeline record."""
    hard_limit = len(data) if limit is None else limit
    reader = Reader(data, "SkillData.CreateBuff", hard_limit)
    ranges: list[dict[str, Any]] = []
    _mark(reader, ranges, "skillData.memberCount", "SkillData.member-count", lambda: _take_header(reader, 48))
    _mark(reader, ranges, "skillData.actionGroupData.memberCount", "ActionGroupData.member-count", lambda: _take_header(reader, 2))
    passive_count = _mark(reader, ranges, "skillData.actionGroupData.passiveEventActions.count", "nullable-list-count-i32", lambda: _take_i32(reader))
    timeline_count = _mark(reader, ranges, "skillData.actionGroupData.timelineActions.count", "nullable-list-count-i32", lambda: _take_i32(reader))
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError("skillTimelineCreateBuff.actionGroupData:requires-empty-passive-positive-timeline")
    timeline_start = reader.pos
    _mark(reader, ranges, "timeline.memberCount", "TimelineActionData.member-count", lambda: _take_header(reader, 4))
    end_frame = _mark(reader, ranges, "timeline.endFrame", "int32", lambda: _take_i32(reader))
    _mark(reader, ranges, "timeline.sequenceActionData.memberCount", "SequenceActionData.member-count", lambda: _take_header(reader, 3))
    action_count = _mark(reader, ranges, "timeline.sequenceActionData.actionData.count", "nullable-list-count-i32", lambda: _take_i32(reader))
    if action_count <= 0:
        raise ValueError(f"skillTimelineCreateBuff.timeline.sequenceActionData:count={action_count}")
    action = _decode_create_buff_action(reader, ranges)
    action_end = reader.pos
    first_timeline: dict[str, Any] = {
        "start": timeline_start,
        "end": None,
        "memberCount": 4,
        "endFrame": end_frame,
        "sequenceActionData": {
            "actionDataCount": action_count,
            "actionData": [action],
            "wholeListExact": action_count == 1,
        },
        "wholeRecordExact": False,
    }
    status = "exact-first-timeline-create-buff-action"
    if action_count == 1:
        sequence_guard = _mark(reader, ranges, "timeline.sequenceActionData.onlyExecuteWhenSourceIsGuard", "bool-byte", lambda: reader.take(1, "bool-byte")[0])
        sequence_main = _mark(reader, ranges, "timeline.sequenceActionData.onlyExecuteWhenSourceIsMainChar", "bool-byte", lambda: reader.take(1, "bool-byte")[0])
        start_frame = _mark(reader, ranges, "timeline.startFrame", "int32", lambda: _take_i32(reader))
        force_start = reader.pos
        _mark(reader, ranges, "timeline.forceSyncAnimData.memberCount", "ForceSyncAnimData.member-count", lambda: _take_header(reader, 4))
        force_sync = _mark(reader, ranges, "timeline.forceSyncAnimData.forceSync", "bool-byte", lambda: reader.take(1, "bool-byte")[0])
        montage_start = reader.pos
        _mark(reader, ranges, "timeline.forceSyncAnimData.montageName", "signed-length-string-bytes", reader.byte_payload)
        playback_speed = _mark(reader, ranges, "timeline.forceSyncAnimData.playbackSpeed", "float32-bits", lambda: reader.take(4, "float32-bits").hex().upper())
        target_frame = _mark(reader, ranges, "timeline.forceSyncAnimData.targetFrame", "int32", lambda: _take_i32(reader))
        first_timeline.update({
            "end": reader.pos,
            "startFrame": start_frame,
            "forceSyncAnimData": {
                "start": force_start,
                "end": reader.pos,
                "forceSync": force_sync,
                "montageNameRange": [montage_start, ranges[-3]["end"]],
                "playbackSpeedBits": playback_speed,
                "targetFrame": target_frame,
            },
            "wholeRecordExact": True,
        })
        first_timeline["sequenceActionData"].update({
            "onlyExecuteWhenSourceIsGuard": sequence_guard,
            "onlyExecuteWhenSourceIsMainChar": sequence_main,
        })
        status = "exact-first-timeline-create-buff-record"
    return {
        "status": status,
        "parserCursor": reader.pos,
        "hardLimit": hard_limit,
        "timelineActionsCount": timeline_count,
        "firstTimelineAction": first_timeline,
        "firstActionEnd": action_end,
        "namedRanges": ranges,
        "wholeFirstTimelineActionExact": action_count == 1,
        "wholeTimelineListExact": action_count == 1 and timeline_count == 1,
        "wholeActionGroupDataExact": action_count == 1 and timeline_count == 1,
        "wholeSkillDataExact": False,
        "evidenceBoundary": (
            "The current dispatcher, member-19 wrapper and reviewed nested readers "
            "close the first CreateBuff action exactly. The containing TimelineActionData "
            "is exact only for a one-action sequence; later actions and timeline records "
            "remain at their first unconsumed byte."
        ),
    }
