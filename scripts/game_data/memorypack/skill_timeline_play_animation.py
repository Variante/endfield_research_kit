"""Exact current-build SkillData first-timeline PlayAnimation framing.

The decoder is intentionally narrow.  It admits only the authenticated
``ActionGroupData.timelineActions`` branch whose first ``TimelineActionData``
contains one extended-tag ``0x0115`` PlayAnimation action and whose nested
``onEndAction`` is the exact empty three-member SequenceActionData shape.
Other action tags and shapes fail at their first unsupported byte.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp_native_image import check_dependency_contracts, open_native_image, read_pinned_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR, LabelledReader


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_play_animation_native.json"
LABEL = "skillTimelinePlayAnimation"
CONTRACT_SHA256 = "3C9138B45A410A161DE9610E1C6402E49CC0E773FFC30E6EE0D8EF9DF2292B54"
PLAY_ANIMATION_TAG = 0x0115


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_pinned_contract(
        CONTRACT_PATH, sha256=CONTRACT_SHA256, schema="endfield.skill-timeline-play-animation-native-contract.v1", label=LABEL
    )
    check_dependency_contracts(value, CONTRACT_PATH.parent, label=LABEL)
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the current methods, code bytes, and generated setters."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    validated_methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(contract["instructionWindows"], label=LABEL)
    for wrapper in contract["wrappers"]:
        owner = image.metadata.types[wrapper["typeDefinition"]]
        if image.metadata.type_full_name(owner) != wrapper["typeName"]:
            raise ValueError(f"{LABEL}.native:wrapper={wrapper['typeDefinition']}")
        if image.setter_methods(owner, label=LABEL) != wrapper["setterMethods"]:
            raise ValueError(f"{LABEL}.native:setter-order={wrapper['typeName']}")
    return {
        "status": "validated",
        "inputSetSha256": contract["inputSetSha256"],
        "nativeInputs": expected,
        "methodIndices": validated_methods,
    }


class _Reader(LabelledReader):
    LABEL = "skillTimelinePlayAnimation"


def _decode_empty_sequence(reader: _Reader, name: str) -> dict[str, Any]:
    start = reader.pos
    reader.header(3, f"{name}.memberCount")
    count = reader.i32(f"{name}.actionData.count")
    if count != 0:
        raise ValueError(
            f"skillTimelinePlayAnimation.{name}.actionData:unsupported-count={count}"
        )
    only_guard = reader.boolean(f"{name}.onlyExecuteWhenSourceIsGuard")
    only_main = reader.boolean(f"{name}.onlyExecuteWhenSourceIsMainChar")
    return {
        "start": start,
        "end": reader.pos,
        "memberCount": 3,
        "actionDataCount": 0,
        "onlyExecuteWhenSourceIsGuard": only_guard,
        "onlyExecuteWhenSourceIsMainChar": only_main,
    }


def _decode_play_animation(reader: _Reader) -> dict[str, Any]:
    start = reader.pos
    if reader.raw(3, "timeline.sequence.actionData[0].unionTag") != b"\xFA\x15\x01":
        raise ValueError("skillTimelinePlayAnimation.unionTag:not-0x0115")
    reader.header(16, "timeline.sequence.actionData[0].memberCount")
    fields: dict[str, Any] = {}
    fields["isEnable"] = reader.boolean("playAnimation.isEnable")
    fields["priorityLevel"] = reader.i32("playAnimation.priorityLevel")
    fields["priorityOffset"] = reader.i32("playAnimation.priorityOffset")
    fields["serverActionIndex"] = reader.i32("playAnimation.serverActionIndex")
    fields["animName"] = reader.string("playAnimation.animName")
    fields["blendDuration"] = reader.f32("playAnimation.blendDuration")
    fields["blendOut"] = reader.f32("playAnimation.blendOut")
    fields["blendOutNextStateHash"] = reader.i32(
        "playAnimation.blendOutNextStateHash"
    )
    fields["duration"] = reader.f32("playAnimation.duration")
    fields["executeOnNormalEndOnly"] = reader.boolean(
        "playAnimation.executeOnNormalEndOnly"
    )
    fields["exitToIdle"] = reader.boolean("playAnimation.exitToIdle")
    fields["onEndAction"] = _decode_empty_sequence(reader, "playAnimation.onEndAction")
    fields["playbackSpeed"] = reader.f32("playAnimation.playbackSpeed")
    fields["startTime"] = reader.f32("playAnimation.startTime")
    fields["startTimeBlackboardKey"] = reader.string(
        "playAnimation.startTimeBlackboardKey"
    )
    fields["useStartTimeBlackboardKey"] = reader.boolean(
        "playAnimation.useStartTimeBlackboardKey"
    )
    return {
        "tag": PLAY_ANIMATION_TAG,
        "typeName": "Beyond.Gameplay.Core.PlayAnimationAction+PlayAnimationActionData",
        "start": start,
        "end": reader.pos,
        "memberCount": 16,
        "fields": fields,
        "wholeActionExact": True,
    }


def decode_first_timeline_play_animation(
    data: bytes,
    *,
    input_set_sha256: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Decode the dominant current SkillData first timeline record exactly."""
    contract = _contract()
    if input_set_sha256.upper() != contract["inputSetSha256"]:
        raise ValueError("skillTimelinePlayAnimation.input-set:mismatch")
    hard_limit = len(data) if limit is None else limit
    reader = _Reader(data, hard_limit)
    reader.header(48, "skillData.memberCount")
    reader.header(2, "skillData.actionGroupData.memberCount")
    passive_count = reader.i32("skillData.actionGroupData.passiveEventActions.count")
    timeline_count = reader.i32("skillData.actionGroupData.timelineActions.count")
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError(
            "skillTimelinePlayAnimation.actionGroupData:requires-empty-passive-positive-timeline"
        )

    timeline_start = reader.pos
    reader.header(4, "timeline.memberCount")
    end_frame = reader.i32("timeline.endFrame")
    reader.header(3, "timeline.sequenceActionData.memberCount")
    action_count = reader.i32("timeline.sequenceActionData.actionData.count")
    if action_count != 1:
        raise ValueError(
            f"skillTimelinePlayAnimation.timeline.sequenceActionData:unsupported-count={action_count}"
        )
    play_animation = _decode_play_animation(reader)
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
        "status": "exact-first-timeline-play-animation-record",
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
                "actionData": [play_animation],
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
            "The first TimelineActionData and its one PlayAnimation child close at exact "
            "physical cursors under the current byte-pinned wrapper contract. Later timeline "
            "list elements and later SkillData fields are not consumed."
        ),
    }
