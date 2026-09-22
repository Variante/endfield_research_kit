"""Exact current-build SkillData first-timeline FindTarget framing.

The selected SkillData AbilityActionData union uses current physical tag
``0x00B2`` for ``FindTargetActionData``.  Its nested selector unions do not use
the older compact tag table retained by the Buff decoder, so this module
supplies the current, byte-pinned subtype routes explicitly and fails closed
for every route absent from the contract.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp_native_image import check_dependency_contracts, read_pinned_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR, LabelledReader
from scripts.game_data.memorypack.buff import (
    BUFF_FIND_TARGET_BODY_MEMBERS,
    BUFF_SELECTOR_FINDER_SUBTYPES,
    BUFF_SELECTOR_POSTPROCESSOR_SUBTYPES,
    BUFF_SELECTOR_VALIDATOR_SUBTYPES,
    read_buff_ability_action_common_prefix_bounded,
    read_buff_selector_member,
)
from scripts.game_data.memorypack.skill_timeline_play_animation import (
    validate_current_native_contract as validate_timeline_native_contract,
)


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_find_target_native.json"
LABEL = "skillTimelineFindTarget"
CONTRACT_SHA256 = "3B8E6D59E86A420D0A242F8B0D5BC9032A32FBBD9B97AC94D80551868CE167DF"
FIND_TARGET_TAG = 0x00B2


CURRENT_SELECTOR_SUBTYPE_TABLES = {
    "finder": {
        0x07: BUFF_SELECTOR_FINDER_SUBTYPES[0x06],  # HitBoxFinder
        0x08: BUFF_SELECTOR_FINDER_SUBTYPES[0x07],  # InFightEnemyFinder
        0x0C: BUFF_SELECTOR_FINDER_SUBTYPES[0x0A],  # OwnerPartsFinder
        0x0D: BUFF_SELECTOR_FINDER_SUBTYPES[0x0B],  # OwnerSpawnedEntityFinder
        0x13: BUFF_SELECTOR_FINDER_SUBTYPES[0x10],  # SmartTargetFinder
    },
    "validator": {
        0x04: BUFF_SELECTOR_VALIDATOR_SUBTYPES[0x03],  # DistanceValidator
        0x05: BUFF_SELECTOR_VALIDATOR_SUBTYPES[0x04],  # ExcludeOwnerValidator
        0x09: BUFF_SELECTOR_VALIDATOR_SUBTYPES[0x07],  # MainCharacterValidator
        0x0A: BUFF_SELECTOR_VALIDATOR_SUBTYPES[0x08],  # SkillCastIdValidator
        0x0B: BUFF_SELECTOR_VALIDATOR_SUBTYPES[0x09],  # TagValidator
    },
    "postProcessor": {
        0x04: BUFF_SELECTOR_POSTPROCESSOR_SUBTYPES[0x03],  # ExcludeTarget
    },
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    value, _digest = read_pinned_contract(
        CONTRACT_PATH, sha256=CONTRACT_SHA256, schema="endfield.skill-timeline-find-target-native-contract.v1", label=LABEL
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
        raise ValueError(f"skillTimelineFindTarget.native:{gate.status}:{gate.detail}")
    timeline = validate_timeline_native_contract()
    return {
        "status": "validated",
        "inputSetSha256": contract["inputSetSha256"],
        "nativeInputs": expected,
        "timelineValidation": timeline,
        "selectedSubtypeRoutes": contract["selectedSubtypeRoutes"],
    }


class _Reader(LabelledReader):
    LABEL = "skillTimelineFindTarget"


def _decode_find_target(data: bytes, start: int, limit: int) -> tuple[dict[str, Any], int]:
    if start + 2 > limit or data[start] != FIND_TARGET_TAG:
        raise ValueError("skillTimelineFindTarget.unionTag:not-0x00B2")
    if data[start + 1] != 18:
        actual = "eof" if start + 1 >= limit else data[start + 1]
        raise ValueError(f"skillTimelineFindTarget.action.memberCount={actual} expected=18")
    offset = start + 2
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data, offset, limit, "skillTimelineFindTarget.action.prefix"
    )
    fields: dict[str, Any] = {}
    for field_name, kind in BUFF_FIND_TARGET_BODY_MEMBERS:
        fields[field_name], offset = read_buff_selector_member(
            data,
            offset,
            limit,
            kind,
            f"skillTimelineFindTarget.action.{field_name}",
            0,
            subtype_tables=CURRENT_SELECTOR_SUBTYPE_TABLES,
        )
    return {
        "tag": FIND_TARGET_TAG,
        "typeName": "Beyond.Gameplay.Core.FindTargetAction+FindTargetActionData",
        "start": start,
        "end": offset,
        "memberCount": 18,
        "prefix": prefix,
        "fields": fields,
        "wholeActionExact": True,
    }, offset


def decode_first_timeline_find_target(
    data: bytes,
    *,
    input_set_sha256: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Decode one-action first TimelineActionData records beginning with tag B2."""
    contract = _contract()
    if input_set_sha256.upper() != contract["inputSetSha256"]:
        raise ValueError("skillTimelineFindTarget.input-set:mismatch")
    hard_limit = len(data) if limit is None else limit
    reader = _Reader(data, hard_limit)
    reader.header(48, "skillData.memberCount")
    reader.header(2, "skillData.actionGroupData.memberCount")
    passive_count = reader.i32("skillData.actionGroupData.passiveEventActions.count")
    timeline_count = reader.i32("skillData.actionGroupData.timelineActions.count")
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError(
            "skillTimelineFindTarget.actionGroupData:requires-empty-passive-positive-timeline"
        )

    timeline_start = reader.pos
    reader.header(4, "timeline.memberCount")
    end_frame = reader.i32("timeline.endFrame")
    reader.header(3, "timeline.sequenceActionData.memberCount")
    action_count = reader.i32("timeline.sequenceActionData.actionData.count")
    if action_count != 1:
        raise ValueError(
            f"skillTimelineFindTarget.timeline.sequenceActionData:unsupported-count={action_count}"
        )
    action_start = reader.pos
    find_target, reader.pos = _decode_find_target(data, action_start, hard_limit)
    reader.ranges.append({
        "name": "timeline.sequence.actionData[0].findTargetAction",
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
        "status": "exact-first-timeline-find-target-record",
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
                "actionData": [find_target],
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
            "The first one-action TimelineActionData and its current tag-0x00B2 "
            "FindTarget child close at exact physical cursors. Additional sequence actions, "
            "later timeline records, and selector subtypes absent from the contract fail closed."
        ),
    }
