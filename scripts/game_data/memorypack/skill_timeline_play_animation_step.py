"""Exact current-build SkillData first-timeline PlayAnimationWithStep framing.

Only the authenticated extended union tag ``0x0116`` is admitted.  The
member-30 wrapper inherits the exact PlayAnimation member-16 prefix and then
reads fourteen generated properties.  Unknown nested TargetSettings selector
routes fail at their first byte rather than inheriting a guessed boundary.
"""
from __future__ import annotations

import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import Reader as ActionReader
from scripts.game_data.memorypack.buff import read_buff_target_settings_full
from scripts.game_data.memorypack.skill_timeline_play_animation import (
    _Reader,
    _decode_empty_sequence,
    validate_current_native_contract as validate_play_animation_native_contract,
)


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_play_animation_step_native.json"
LABEL = "skillTimelinePlayAnimationStep"
PLAY_ANIMATION_STEP_TAG = 0x0116


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-play-animation-step-native-contract.v1", label=LABEL
    )
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected dispatcher route and generated reader."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    parent_validation = validate_play_animation_native_contract()
    dispatcher = contract["dispatcher"]
    image.validate_dispatcher(dispatcher, label=LABEL)
    validated_methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    for context in contract["nestedContextUsage"]:
        image.nested_usage_cell(context, label=LABEL)
    owner = image.check_wrapper_inheritance(contract["wrapper"], label=LABEL)
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["wrapper"]["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "unionTag": dispatcher["unionTag"],
        "methodIndices": validated_methods,
        "parentValidation": parent_validation,
    }


def _decode_blackboard_double(reader: _Reader, name: str) -> dict[str, Any] | None:
    start = reader.pos
    marker = reader.raw(1, f"{name}.memberCount")[0]
    if marker == 0xFF:
        return None
    if marker != 3:
        raise ValueError(
            f"skillTimelinePlayAnimationStep.{name}.member-count={marker} expected=3"
        )
    return {
        "start": start,
        "end": None,
        "memberCount": 3,
        "directValue": reader.string(f"{name}.directValue"),
        "isBlackboard": reader.boolean(f"{name}.isBlackboard"),
        "value": reader.f32(f"{name}.value"),
    }


def _decode_play_animation_step(reader: _Reader) -> dict[str, Any]:
    start = reader.pos
    if reader.raw(3, "timeline.sequence.actionData[0].unionTag") != b"\xFA\x16\x01":
        raise ValueError("skillTimelinePlayAnimationStep.unionTag:not-0x0116")
    reader.header(30, "timeline.sequence.actionData[0].memberCount")
    fields: dict[str, Any] = {}
    fields["isEnable"] = reader.boolean("playAnimationWithStep.isEnable")
    fields["priorityLevel"] = reader.i32("playAnimationWithStep.priorityLevel")
    fields["priorityOffset"] = reader.i32("playAnimationWithStep.priorityOffset")
    fields["serverActionIndex"] = reader.i32("playAnimationWithStep.serverActionIndex")
    fields["animName"] = reader.string("playAnimationWithStep.animName")
    fields["blendDuration"] = reader.f32("playAnimationWithStep.blendDuration")
    fields["blendOut"] = reader.f32("playAnimationWithStep.blendOut")
    fields["blendOutNextStateHash"] = reader.i32(
        "playAnimationWithStep.blendOutNextStateHash"
    )
    fields["duration"] = reader.f32("playAnimationWithStep.duration")
    fields["executeOnNormalEndOnly"] = reader.boolean(
        "playAnimationWithStep.executeOnNormalEndOnly"
    )
    fields["exitToIdle"] = reader.boolean("playAnimationWithStep.exitToIdle")
    fields["onEndAction"] = _decode_empty_sequence(
        reader, "playAnimationWithStep.onEndAction"
    )
    fields["playbackSpeed"] = reader.f32("playAnimationWithStep.playbackSpeed")
    fields["startTime"] = reader.f32("playAnimationWithStep.startTime")
    fields["startTimeBlackboardKey"] = reader.string(
        "playAnimationWithStep.startTimeBlackboardKey"
    )
    fields["useStartTimeBlackboardKey"] = reader.boolean(
        "playAnimationWithStep.useStartTimeBlackboardKey"
    )
    fields["animBlendInAfterStep"] = reader.f32(
        "playAnimationWithStep.animBlendInAfterStep"
    )
    fields["battlePoseWhenStep"] = reader.boolean(
        "playAnimationWithStep.battlePoseWhenStep"
    )
    fields["frameToOriginAnim"] = reader.i32(
        "playAnimationWithStep.frameToOriginAnim"
    )
    fields["hideWeapon"] = reader.boolean("playAnimationWithStep.hideWeapon")
    fields["hideWeaponFrame"] = reader.i32(
        "playAnimationWithStep.hideWeaponFrame"
    )
    fields["montageName"] = reader.string("playAnimationWithStep.montageName")
    fields["snapDistance"] = reader.f32("playAnimationWithStep.snapDistance")
    fields["snapFrame"] = reader.i32("playAnimationWithStep.snapFrame")
    fields["speed"] = _decode_blackboard_double(reader, "playAnimationWithStep.speed")
    if fields["speed"] is not None:
        fields["speed"]["end"] = reader.pos
    fields["speedCurveKey"] = reader.string(
        "playAnimationWithStep.speedCurveKey"
    )
    fields["stepBlendIn"] = reader.f32("playAnimationWithStep.stepBlendIn")
    fields["stepDistance"] = reader.f32("playAnimationWithStep.stepDistance")
    target_start = reader.pos
    try:
        target, target_end = read_buff_target_settings_full(
            reader.data,
            target_start,
            reader.limit,
            "playAnimationWithStep.stepTarget",
            0,
        )
    except (IndexError, UnicodeDecodeError, ValueError, struct.error) as exc:
        raise ValueError(
            f"skillTimelinePlayAnimationStep.stepTarget:unsupported:{exc}"
        ) from exc
    if target_end <= target_start:
        raise ValueError("skillTimelinePlayAnimationStep.stepTarget:no-progress")
    reader.pos = target_end
    reader.ranges.append({
        "name": "playAnimationWithStep.stepTarget",
        "start": target_start,
        "end": target_end,
    })
    fields["stepTarget"] = target
    fields["useFixSpeed"] = reader.boolean("playAnimationWithStep.useFixSpeed")
    return {
        "tag": PLAY_ANIMATION_STEP_TAG,
        "typeName": _contract()["wrapper"]["typeName"],
        "start": start,
        "end": reader.pos,
        "memberCount": 30,
        "fields": fields,
        "wholeActionExact": True,
    }


def decode_play_animation_step_action(
    reader: ActionReader, depth: int, tag: int, width: int,
) -> None:
    """Consume the selected action at any reached shared-sequence position."""
    del depth
    contract = _contract()
    if (
        tag != PLAY_ANIMATION_STEP_TAG
        or width != 3
        or contract.get("dispatcher", {}).get("unionTag") != tag
        or contract.get("wrapper", {}).get("serializedMemberCount") != 30
    ):
        raise ValueError(f"{LABEL}.shared-action:route-drift")
    start = reader.pos
    nested = _Reader(reader.data, reader.limit, start=start)
    _decode_play_animation_step(nested)
    if nested.pos <= start:
        raise ValueError(f"{LABEL}.shared-action:no-progress")
    reader.take(nested.pos - start, "play-animation-step-action")


def decode_first_timeline_play_animation_step(
    data: bytes,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Decode the first TimelineActionData when its sole action is tag 0x0116."""
    hard_limit = len(data) if limit is None else limit
    reader = _Reader(data, hard_limit)
    reader.header(48, "skillData.memberCount")
    reader.header(2, "skillData.actionGroupData.memberCount")
    passive_count = reader.i32("skillData.actionGroupData.passiveEventActions.count")
    timeline_count = reader.i32("skillData.actionGroupData.timelineActions.count")
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError(
            "skillTimelinePlayAnimationStep.actionGroupData:requires-empty-passive-positive-timeline"
        )
    timeline_start = reader.pos
    reader.header(4, "timeline.memberCount")
    end_frame = reader.i32("timeline.endFrame")
    reader.header(3, "timeline.sequenceActionData.memberCount")
    action_count = reader.i32("timeline.sequenceActionData.actionData.count")
    if action_count != 1:
        raise ValueError(
            f"skillTimelinePlayAnimationStep.timeline.sequenceActionData:unsupported-count={action_count}"
        )
    action = _decode_play_animation_step(reader)
    sequence_guard = reader.boolean(
        "timeline.sequenceActionData.onlyExecuteWhenSourceIsGuard"
    )
    sequence_main = reader.boolean(
        "timeline.sequenceActionData.onlyExecuteWhenSourceIsMainChar"
    )
    start_frame = reader.i32("timeline.startFrame")
    force_sync_start = reader.pos
    reader.header(4, "timeline.forceSyncAnimData.memberCount")
    force_sync = reader.boolean("timeline.forceSyncAnimData.forceSync")
    montage_name = reader.string("timeline.forceSyncAnimData.montageName")
    playback_speed = reader.f32("timeline.forceSyncAnimData.playbackSpeed")
    target_frame = reader.i32("timeline.forceSyncAnimData.targetFrame")
    return {
        "status": "exact-first-timeline-play-animation-step-record",
        "parserCursor": reader.pos,
        "hardLimit": hard_limit,
        "timelineActionsCount": timeline_count,
        "firstTimelineAction": {
            "start": timeline_start,
            "end": reader.pos,
            "memberCount": 4,
            "endFrame": end_frame,
            "sequenceActionData": {
                "actionDataCount": 1,
                "actionData": [action],
                "onlyExecuteWhenSourceIsGuard": sequence_guard,
                "onlyExecuteWhenSourceIsMainChar": sequence_main,
            },
            "startFrame": start_frame,
            "forceSyncAnimData": {
                "start": force_sync_start,
                "end": reader.pos,
                "memberCount": 4,
                "forceSync": force_sync,
                "montageName": montage_name,
                "playbackSpeed": playback_speed,
                "targetFrame": target_frame,
            },
            "wholeRecordExact": True,
        },
        "namedRanges": reader.ranges,
        "wholeTimelineListExact": timeline_count == 1,
        "wholeActionGroupDataExact": timeline_count == 1,
        "wholeSkillDataExact": False,
        "evidenceBoundary": (
            "The current dispatcher, generated member-30 wrapper, inherited member-16 "
            "reader and nested typed readers close the first TimelineActionData at its "
            "physical cursor. Later list elements and later SkillData fields remain open."
        ),
    }
