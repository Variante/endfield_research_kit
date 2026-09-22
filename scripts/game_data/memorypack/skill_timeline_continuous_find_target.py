"""Exact current-build SkillData first-timeline ContinuousFindTarget framing.

The selected SkillData AbilityActionData union uses current physical tag
``0x008A`` for ``ContinuousFindTargetAction.Data``.  Its nested selector unions do not use
the older compact tag table retained by the Buff decoder, so this module
supplies the current, byte-pinned subtype routes explicitly and fails closed
for every route absent from the contract.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import check_dependency_contracts, read_pinned_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR, LabelledReader
from scripts.game_data.memorypack.buff import (
    BUFF_FIND_TARGET_BODY_MEMBERS,
    read_buff_ability_action_common_prefix_bounded,
    read_buff_selector_f32,
    read_buff_selector_member,
)
from scripts.game_data.memorypack.skill_timeline_find_target import (
    CURRENT_SELECTOR_SUBTYPE_TABLES,
    validate_current_native_contract as validate_selector_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_play_animation import (
    validate_current_native_contract as validate_timeline_native_contract,
)


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_continuous_find_target_native.json"
LABEL = "skillTimelineContinuousFindTarget"
CONTRACT_SHA256 = "7536544C31D184EDDA059E4FDA23CEAAB6A618AC3DF9A5B115D2BDD789B7478D"
CONTINUOUS_FIND_TARGET_TAG = 0x008A
CONTINUOUS_SELECTOR_SUBTYPE_TABLES = {
    **CURRENT_SELECTOR_SUBTYPE_TABLES,
    "postProcessor": {
        **CURRENT_SELECTOR_SUBTYPE_TABLES["postProcessor"],
        # The current wrapper accepts the two-member form reached by this lane.
        0x04: (
            "ExcludeTarget",
            (
                ("excludedTargetSettings", "targetsettings"),
                ("processTargetType", "i32"),
            ),
        ),
    },
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_pinned_contract(
        CONTRACT_PATH, sha256=CONTRACT_SHA256, schema="endfield.skill-timeline-continuous-find-target-native-contract.v1", label=LABEL
    )
    check_dependency_contracts(value, CONTRACT_PATH.parent, label=LABEL)
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected build and both reviewed dependency contracts."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"skillTimelineContinuousFindTarget.native:{gate.status}:{gate.detail}")
    timeline = validate_timeline_native_contract()
    selectors = validate_selector_native_contract()
    return {
        "status": "validated",
        "inputSetSha256": contract["inputSetSha256"],
        "nativeInputs": expected,
        "timelineValidation": timeline,
        "selectorValidation": selectors,
        "selectedSubtypeRoutes": contract["selectedSubtypeRoutes"],
    }


class _Reader(LabelledReader):
    LABEL = "skillTimelineContinuousFindTarget"


def _decode_continuous_find_target(data: bytes, start: int, limit: int) -> tuple[dict[str, Any], int]:
    if start + 2 > limit or data[start] != CONTINUOUS_FIND_TARGET_TAG:
        raise ValueError("skillTimelineContinuousFindTarget.unionTag:not-0x008A")
    if data[start + 1] != 19:
        actual = "eof" if start + 1 >= limit else data[start + 1]
        raise ValueError(f"skillTimelineContinuousFindTarget.action.memberCount={actual} expected=19")
    offset = start + 2
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data, offset, limit, "skillTimelineContinuousFindTarget.action.prefix"
    )
    fields: dict[str, Any] = {}
    for field_name, kind in BUFF_FIND_TARGET_BODY_MEMBERS:
        fields[field_name], offset = read_buff_selector_member(
            data,
            offset,
            limit,
            kind,
            f"skillTimelineContinuousFindTarget.action.{field_name}",
            0,
            subtype_tables=CONTINUOUS_SELECTOR_SUBTYPE_TABLES,
        )
    fields["findInterval"], offset = read_buff_selector_f32(
        data,
        offset,
        limit,
        "skillTimelineContinuousFindTarget.action.findInterval",
    )
    return {
        "tag": CONTINUOUS_FIND_TARGET_TAG,
        "typeName": "Beyond.Gameplay.Core.ContinuousFindTargetAction+Data",
        "start": start,
        "end": offset,
        "memberCount": 19,
        "prefix": prefix,
        "fields": fields,
        "wholeActionExact": True,
    }, offset


def decode_first_timeline_continuous_find_target(
    data: bytes,
    *,
    input_set_sha256: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Decode one-action first TimelineActionData records beginning with tag 8A."""
    contract = _contract()
    if input_set_sha256.upper() != contract["inputSetSha256"]:
        raise ValueError("skillTimelineContinuousFindTarget.input-set:mismatch")
    hard_limit = len(data) if limit is None else limit
    reader = _Reader(data, hard_limit)
    reader.header(48, "skillData.memberCount")
    reader.header(2, "skillData.actionGroupData.memberCount")
    passive_count = reader.i32("skillData.actionGroupData.passiveEventActions.count")
    timeline_count = reader.i32("skillData.actionGroupData.timelineActions.count")
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError(
            "skillTimelineContinuousFindTarget.actionGroupData:requires-empty-passive-positive-timeline"
        )

    timeline_start = reader.pos
    reader.header(4, "timeline.memberCount")
    end_frame = reader.i32("timeline.endFrame")
    reader.header(3, "timeline.sequenceActionData.memberCount")
    action_count = reader.i32("timeline.sequenceActionData.actionData.count")
    if action_count != 1:
        raise ValueError(
            f"skillTimelineContinuousFindTarget.timeline.sequenceActionData:unsupported-count={action_count}"
        )
    action_start = reader.pos
    continuous_find_target, reader.pos = _decode_continuous_find_target(data, action_start, hard_limit)
    reader.ranges.append({
        "name": "timeline.sequence.actionData[0].continuousFindTargetAction",
        "start": action_start,
        "end": reader.pos,
    })
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
        "status": "exact-first-timeline-continuous-find-target-record",
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
                "actionData": [continuous_find_target],
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
            "The first one-action TimelineActionData and its current tag-0x008A "
            "ContinuousFindTarget child close at exact physical cursors. Additional sequence actions, "
            "later timeline records, and selector subtypes absent from the contract fail closed."
        ),
    }



