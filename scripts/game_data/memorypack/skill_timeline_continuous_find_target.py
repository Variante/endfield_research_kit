"""Exact current-build SkillData first-timeline ContinuousFindTarget framing.

The selected SkillData AbilityActionData union routes
``ContinuousFindTargetAction.Data`` through a tag resolved by type name per
build (``continuous_find_target_plain_tag``, through
``levelscript_union_tags``); an unvalidated build or a changed member count
resolves no tag and nothing decodes.  Its nested selector unions are
read through the Buff decoder's name-keyed subtype tables, restricted to the
routes the FindTarget contract reviewed
(``skill_timeline_find_target.CURRENT_SELECTOR_SUBTYPE_TABLES``), and fail
closed for every route absent from the contract.

The 19-member order is the shared four-member action prefix, fourteen
target-selection members and a terminal ``findInterval`` float.  Current
Skill selector routes include the two-member ``ExcludeTarget`` postprocessor
(``excludedTargetSettings``, ``processTargetType``), whose tag is resolved by
type name per build like every other selector route.  Reached first records
close exactly; whole-file closure still needs every later timeline record.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data import levelscript_union_tags as union_tags
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
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
# The AbilityActionData type this lane reads and the member count it reads.
CONTINUOUS_FIND_TARGET_TYPE = "Core_ContinuousFindTargetAction_Data"
CONTINUOUS_FIND_TARGET_MEMBER_COUNT = 19
# The FindTarget contract's reviewed routes, each keyed by its subtype's tag
# resolved by type name per build (``buff._selector_subtypes`` through
# ``levelscript_union_tags``). They already carry the two-member
# ``ExcludeTarget`` postprocessor this lane reaches, so no route is added
# here: a literal tag would outlive a renumbering and a build drift.
CONTINUOUS_SELECTOR_SUBTYPE_TABLES = CURRENT_SELECTOR_SUBTYPE_TABLES


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-continuous-find-target-native-contract.v1", label=LABEL
    )
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
        "nativeInputs": expected,
        "timelineValidation": timeline,
        "selectorValidation": selectors,
        "selectedSubtypeRoutes": contract["selectedSubtypeRoutes"],
    }


def continuous_find_target_plain_tag() -> int | None:
    """The build's one-byte tag of ``ContinuousFindTargetAction.Data``, by name.

    ``None`` when the union-tag contract does not validate the build, the
    member count is no longer the one read here, or the tag needs the wide
    ``FA`` encoding this lane does not read.
    """
    route = union_tags.plain_route(
        "AbilityActionData", CONTINUOUS_FIND_TARGET_TYPE, CONTINUOUS_FIND_TARGET_MEMBER_COUNT
    )
    return route[0] if route else None


class _Reader(LabelledReader):
    LABEL = "skillTimelineContinuousFindTarget"


def _decode_continuous_find_target(data: bytes, start: int, limit: int) -> tuple[dict[str, Any], int]:
    tag = continuous_find_target_plain_tag()
    if tag is None:
        raise ValueError(
            f"skillTimelineContinuousFindTarget.unionTag:unresolved{union_tags.unavailable_note()}"
        )
    if start + 2 > limit or data[start] != tag:
        raise ValueError(f"skillTimelineContinuousFindTarget.unionTag:not-0x{tag:04X}")
    if data[start + 1] != CONTINUOUS_FIND_TARGET_MEMBER_COUNT:
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
        "tag": tag,
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
    limit: int | None = None,
) -> dict[str, Any]:
    """Decode one-action first TimelineActionData records beginning with ContinuousFindTarget."""
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
            "The first one-action TimelineActionData and its current "
            f"tag-0x{continuous_find_target['tag']:04X} "
            "ContinuousFindTarget child close at exact physical cursors. Additional sequence actions, "
            "later timeline records, and selector subtypes absent from the contract fail closed."
        ),
    }



