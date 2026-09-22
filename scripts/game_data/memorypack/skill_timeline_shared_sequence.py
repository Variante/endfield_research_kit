"""Authenticated exact SkillData timeline records using current action readers.

This is deliberately narrower than the general BuffData action reader.  It
admits the named first-action routes in its byte-pinned composite contract,
including the recursively bounded IfElse route, plus the reached multi-action
CreateBuff rows.  Every absent child route still fails closed at its first
byte.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import (
    IF_ELSE_ACTION_MEMBER_COUNT,
    IF_ELSE_ACTION_READ_KINDS,
    IF_ELSE_ACTION_TAG,
    SEQUENCE_RECURSION_LIMIT,
    Reader,
)


CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_shared_sequence_native.json"
LABEL = "skillTimelineSharedSequence"
CONTRACT_SHA256 = "A082749F89876CA9010F0C3ADECF95FCB9FA75F049A76BF10F253ED3408F0124"
JUMP_TO_ACTION_TAG = 0x00D9
JUMP_TO_ACTION_MEMBER_COUNT = 6
JUMP_TO_ACTION_READ_KINDS = (
    "anonymous-nonzero-byte",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "SequenceActionData",
    "int32",
)
SET_ABILITY_ENTITY_TARGET_TAG = 0x0147
SET_ABILITY_ENTITY_TARGET_MEMBER_COUNT = 5
SET_ABILITY_ENTITY_TARGET_READ_KINDS = (
    "anonymous-nonzero-byte",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "anonymous-scalar32",
    "TargetSettings",
)
PLAY_PERFECT_DODGE_ANIM_TAG = 0x0118
PLAY_PERFECT_DODGE_ANIM_MEMBER_COUNT = 6
PLAY_PERFECT_DODGE_ANIM_READ_KINDS = (
    "bool-byte",
    "enum-int32",
    "int32",
    "int32",
    "bool-byte",
    "float32-bits",
)
FIRST_DAMAGE_UNIT_COST_LIST_MEMBER_INDEX = 5
FIRST_DAMAGE_UNIT_COST_LIST_METHOD_SPEC = 610882
COST_DATA_MEMBER_COUNT = 3
COST_DATA_READ_KINDS = (
    "anonymous-raw4",
    "anonymous-scalar32",
    "anonymous-raw4",
)


class SharedSequenceReader(Reader):
    """Skill-only extensions to the shared finite action grammar."""

    def damage_unit_profile(self) -> None:
        """Select the Skill-authenticated CostData list at member five.

        The shared Buff reader deliberately leaves every positive first/third
        DamageUnit list closed.  SkillData has an additional composite
        contract for member five only, so keep the selection local to this
        subclass and retain the shared fail-closed behavior for member ten and
        the EffectActionCfg array.
        """
        stack = getattr(self, "_skill_damage_unit_list_indices", None)
        if stack is None:
            stack = []
            self._skill_damage_unit_list_indices = stack
        stack.append(0)
        try:
            super().damage_unit_profile()
        finally:
            stack.pop()

    def empty_damage_collection(self, kind: str) -> int | None:
        stack = getattr(self, "_skill_damage_unit_list_indices", None)
        if kind == "damage unit list" and stack:
            list_index = stack[-1]
            stack[-1] += 1
            if list_index == 0:
                start = self.pos
                count = self.count(1, nullable=True)
                for _ in range(max(0, count)):
                    self.cost_profile()
                self.records.append({
                    "start": start,
                    "end": self.pos,
                    "kind": "skill-damage-unit-cost-data-list",
                    "count": count,
                    "damageUnitMemberIndex": FIRST_DAMAGE_UNIT_COST_LIST_MEMBER_INDEX,
                })
                return count
        return super().empty_damage_collection(kind)

    def _action(self, depth: int, tag: int, width: int) -> None:
        if tag == JUMP_TO_ACTION_TAG:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(JUMP_TO_ACTION_MEMBER_COUNT)
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            self.sequence(depth)
            self.take(4, "anonymous-scalar32")
            return
        if tag == SET_ABILITY_ENTITY_TARGET_TAG:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(SET_ABILITY_ENTITY_TARGET_MEMBER_COUNT)
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            self.target_profile()
            return
        if tag == PLAY_PERFECT_DODGE_ANIM_TAG:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(PLAY_PERFECT_DODGE_ANIM_MEMBER_COUNT)
            self.take(1, PLAY_PERFECT_DODGE_ANIM_READ_KINDS[0])
            for kind in PLAY_PERFECT_DODGE_ANIM_READ_KINDS[1:4]:
                self.take(4, kind)
            self.take(1, PLAY_PERFECT_DODGE_ANIM_READ_KINDS[4])
            self.take(4, PLAY_PERFECT_DODGE_ANIM_READ_KINDS[5])
            return
        super()._action(depth, tag, width)


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    raw = CONTRACT_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != CONTRACT_SHA256:
        raise ValueError("skillTimelineSharedSequence.contract:sha256-mismatch")
    value = json.loads(raw)
    if value.get("schema") != "endfield.skill-timeline-shared-sequence-native-contract.v1":
        raise ValueError("skillTimelineSharedSequence.contract:unsupported-schema")
    dependency_values: dict[str, dict[str, Any]] = {}
    for dependency in value.get("dependencies", []):
        path = CONTRACT_PATH.parent / dependency["path"]
        dependency_raw = path.read_bytes()
        if hashlib.sha256(dependency_raw).hexdigest().upper() != dependency["sha256"]:
            raise ValueError(
                f"skillTimelineSharedSequence.dependency:sha256-mismatch:{dependency['path']}"
            )
        if path.suffix == ".json":
            dependency_values[dependency["path"]] = json.loads(dependency_raw)
    routes = value.get("allowedReachedRoutes")
    if not isinstance(routes, list):
        raise ValueError("skillTimelineSharedSequence.contract:routes")
    for route in routes:
        provider_ref = route.get("providerRef")
        if provider_ref is None:
            continue
        provider = value.get(provider_ref)
        if not isinstance(provider, dict):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-missing:{provider_ref}"
            )
        if (
            provider.get("physicalTag") != route.get("tag")
            or provider.get("serializedMemberCount") != route.get("memberCount")
            or provider.get("status")
            != "authenticated-static-provider-chain-with-exact-corpus-cursor"
        ):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-route-drift:{provider_ref}"
            )
        reads = provider.get("orderedSourceReads")
        read_kinds = tuple(row.get("kind") for row in reads) if isinstance(reads, list) else ()
        provider_kind = provider.get("providerKind")
        expected = {
            None: (IF_ELSE_ACTION_TAG, IF_ELSE_ACTION_MEMBER_COUNT, IF_ELSE_ACTION_READ_KINDS),
            "nested-sequence-action": (
                JUMP_TO_ACTION_TAG,
                JUMP_TO_ACTION_MEMBER_COUNT,
                JUMP_TO_ACTION_READ_KINDS,
            ),
            "target-settings-action": (
                SET_ABILITY_ENTITY_TARGET_TAG,
                SET_ABILITY_ENTITY_TARGET_MEMBER_COUNT,
                SET_ABILITY_ENTITY_TARGET_READ_KINDS,
            ),
            "simple-action": (
                PLAY_PERFECT_DODGE_ANIM_TAG,
                PLAY_PERFECT_DODGE_ANIM_MEMBER_COUNT,
                PLAY_PERFECT_DODGE_ANIM_READ_KINDS,
            ),
        }.get(provider_kind)
        if (
            expected is None
            or int(route["tag"], 16) != expected[0]
            or route["memberCount"] != expected[1]
            or [row.get("memberIndex") for row in reads or []]
            != list(range(route["memberCount"]))
            or read_kinds != expected[2]
            or (provider_kind is None and provider.get("recursionLimit") != SEQUENCE_RECURSION_LIMIT)
        ):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-read-order:{provider_ref}"
            )
        method_spec = provider.get("nestedMethodSpec")
        expected_type = {
            None: "Beyond.Gameplay.Core.SequenceActionData",
            "nested-sequence-action": "Beyond.Gameplay.Core.SequenceActionData",
            "target-settings-action": "Beyond.Gameplay.Core.TargetSettings",
            "simple-action": None,
        }[provider_kind]
        if expected_type is not None and (
            not isinstance(method_spec, dict)
            or method_spec.get("typeName") != expected_type
        ):
            raise ValueError(
                f"skillTimelineSharedSequence.contract:provider-type:{provider_ref}"
            )
        if expected_type is None and method_spec is not None:
            raise ValueError(
                f"skillTimelineSharedSequence.contract:unexpected-provider-type:{provider_ref}"
            )
    cost_provider = value.get("positiveFirstDamageUnitCostListProvider")
    if not isinstance(cost_provider, dict):
        raise ValueError("skillTimelineSharedSequence.contract:cost-list-provider")
    element_reads = cost_provider.get("orderedElementReads")
    if (
        cost_provider.get("status")
        != "authenticated-static-provider-chain-with-exact-corpus-cursor"
        or cost_provider.get("damageUnitMemberIndex")
        != FIRST_DAMAGE_UNIT_COST_LIST_MEMBER_INDEX
        or cost_provider.get("listMethodSpecIndex")
        != FIRST_DAMAGE_UNIT_COST_LIST_METHOD_SPEC
        or cost_provider.get("elementTypeName")
        != "Beyond.Gameplay.Core.CastData+CostData"
        or cost_provider.get("elementTypeDefinition") != 9061
        or cost_provider.get("elementMemberCount") != COST_DATA_MEMBER_COUNT
        or [row.get("memberIndex") for row in element_reads or []]
        != list(range(COST_DATA_MEMBER_COUNT))
        or tuple(row.get("kind") for row in element_reads or [])
        != COST_DATA_READ_KINDS
    ):
        raise ValueError("skillTimelineSharedSequence.contract:cost-list-provider-drift")
    damage_contract = dependency_values.get("buff_9a_native.json", {})
    damage_context = next(
        (
            row
            for row in damage_contract.get("nestedContexts", [])
            if row.get("instructionRva") == cost_provider.get("listCallsiteRva")
        ),
        None,
    )
    cost_contract = dependency_values.get("buff_c0_native.json", {})
    cost_methods = cost_contract.get("methods", [])
    source_contracts = {
        row.get("path"): row.get("sha256")
        for row in cost_provider.get("sourceContracts", [])
        if isinstance(row, dict)
    }
    dependency_hashes = {
        row.get("path"): row.get("sha256")
        for row in value.get("dependencies", [])
        if isinstance(row, dict)
    }
    if (
        not isinstance(damage_context, dict)
        or damage_context.get("methodSpecIndex") != FIRST_DAMAGE_UNIT_COST_LIST_METHOD_SPEC
        or damage_context.get("typeName") != "System.Collections.Generic.List`1"
        or damage_context.get("generic", {}).get("elementInstantiationIndex") != 17015
        or damage_context.get("generic", {}).get("elementArguments")
        != [cost_provider.get("elementArgumentRawHex")]
        or cost_contract.get("anonymousReadOrder", {}).get("costMember3")
        != ["raw4", "scalar32", "raw4"]
        or not any(
            row[1]
            == "Beyond.MemoryPack.Beyond_Gameplay_Core_CastData_CostDataForMemoryPack"
            and row[2] == "Deserialize"
            for row in cost_methods
        )
        or source_contracts.get("buff_9a_native.json")
        != dependency_hashes.get("buff_9a_native.json")
        or source_contracts.get("buff_c0_native.json")
        != dependency_hashes.get("buff_c0_native.json")
    ):
        raise ValueError("skillTimelineSharedSequence.contract:cost-list-source-drift")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameassemblySha256"], expected["globalMetadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(
            f"skillTimelineSharedSequence.native:{gate.status}:{gate.detail}"
        )
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unityplayer.is_file():
        raise ValueError("skillTimelineSharedSequence.native:UnityPlayer.dll:missing")
    if hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["unityplayerSha256"]:
        raise ValueError("skillTimelineSharedSequence.native:UnityPlayer.dll:sha256-mismatch")
    return {
        "status": "validated",
        "inputSetSha256": contract["inputSetSha256"],
        "nativeInputs": expected,
        "contractSha256": CONTRACT_SHA256,
        "dependencyCount": len(contract["dependencies"]),
    }


def _tag_at(data: bytes, offset: int, limit: int) -> tuple[int, int]:
    if offset >= limit:
        raise ValueError("skillTimelineSharedSequence.unionTag:truncated")
    lead = data[offset]
    if lead == 0xFA:
        if offset + 3 > limit:
            raise ValueError("skillTimelineSharedSequence.unionTag:truncated-extended")
        return struct.unpack_from("<H", data, offset + 1)[0], 3
    return lead, 1


def _route_table() -> dict[int, dict[str, Any]]:
    return {
        int(row["tag"], 16): row for row in _contract()["allowedReachedRoutes"]
    }


def _named_ranges(reader: Reader) -> list[dict[str, Any]]:
    ranges = [
        {"name": "skillData.memberCount", "start": 0, "end": 1, "kind": "SkillData.member-count"},
        {"name": "skillData.actionGroupData.memberCount", "start": 1, "end": 2, "kind": "ActionGroupData.member-count"},
        {"name": "skillData.actionGroupData.passiveEventActions.count", "start": 2, "end": 6, "kind": "nullable-list-count-i32"},
        {"name": "skillData.actionGroupData.timelineActions.count", "start": 6, "end": 10, "kind": "nullable-list-count-i32"},
    ]
    for index, span in enumerate(reader.ranges):
        ranges.append({
            "name": f"timeline.sharedSequence.range[{index}]",
            "start": span["start"],
            "end": span["end"],
            "kind": span["kind"],
        })
    cursor = 0
    for span in ranges:
        if span["start"] != cursor or span["end"] <= span["start"]:
            raise ValueError(
                f"skillTimelineSharedSequence.ranges:not-contiguous:{cursor}:{span}"
            )
        cursor = span["end"]
    if cursor != reader.pos:
        raise ValueError(
            f"skillTimelineSharedSequence.ranges:end={cursor}:cursor={reader.pos}"
        )
    return ranges


def decode_first_timeline_shared_sequence(
    data: bytes,
    *,
    input_set_sha256: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Close one first TimelineActionData using only contracted action routes."""
    contract = _contract()
    if input_set_sha256.upper() != contract["inputSetSha256"]:
        raise ValueError("skillTimelineSharedSequence.input-set:mismatch")
    hard_limit = len(data) if limit is None else limit
    if hard_limit > len(data) or hard_limit < 22:
        raise ValueError("skillTimelineSharedSequence.limit")
    if data[0] != 48 or data[1] != 2:
        raise ValueError("skillTimelineSharedSequence.envelope")
    passive_count = struct.unpack_from("<i", data, 2)[0]
    timeline_count = struct.unpack_from("<i", data, 6)[0]
    if passive_count != 0 or timeline_count <= 0:
        raise ValueError("skillTimelineSharedSequence.actionGroup")
    if data[10] != 4 or data[15] != 3:
        raise ValueError("skillTimelineSharedSequence.timelineHeader")
    action_count = struct.unpack_from("<i", data, 16)[0]
    if action_count <= 0:
        raise ValueError("skillTimelineSharedSequence.actionCount")
    first_tag, _ = _tag_at(data, 20, hard_limit)
    roots = {int(tag, 16) for tag in contract["rootTags"]}
    create_buff_root = int(contract["createBuffMultiActionRoot"], 16)
    if first_tag == create_buff_root:
        if action_count <= 1:
            raise ValueError("skillTimelineSharedSequence.createBuff:requires-multiple-actions")
    elif first_tag not in roots:
        raise ValueError(f"skillTimelineSharedSequence.firstTag=0x{first_tag:04X}")

    reader = SharedSequenceReader(data, "SkillData.SharedTimelineSequence", hard_limit)
    reader.pos = 10
    timeline_start = reader.pos
    reader.header(4)
    reader.take(4, "TimelineActionData.endFrame.int32")
    reader.sequence()
    sequence_end = reader.pos
    reader.take(4, "TimelineActionData.startFrame.int32")
    reader.header(4)
    reader.take(1, "ForceSyncAnimData.forceSync.bool-byte")
    reader.byte_payload()
    reader.take(4, "ForceSyncAnimData.playbackSpeed.float32-bits")
    reader.take(4, "ForceSyncAnimData.targetFrame.int32")

    route_table = _route_table()
    actions = []
    for record in reader.records:
        if record.get("kind") != "union":
            continue
        tag = record["tag"]
        if tag == 0xFF:
            actions.append({
                "tag": tag,
                "tagHex": "0x00FF",
                "typeName": "null",
                "memberCount": None,
                "start": record["start"],
                "end": record["end"],
                "structurallyExact": True,
            })
            continue
        route = route_table.get(tag)
        if route is None:
            raise ValueError(f"skillTimelineSharedSequence.route=0x{tag:04X}:not-contracted")
        _tag, width = _tag_at(data, record["start"], record["end"])
        if _tag != tag:
            raise ValueError("skillTimelineSharedSequence.route:tag-drift")
        member_offset = record["start"] + width
        if member_offset >= record["end"] or data[member_offset] != route["memberCount"]:
            raise ValueError(
                f"skillTimelineSharedSequence.route=0x{tag:04X}:member-count"
            )
        actions.append({
            "tag": tag,
            "tagHex": f"0x{tag:04X}",
            "typeName": route["typeName"],
            "memberCount": route["memberCount"],
            "start": record["start"],
            "end": record["end"],
            "structurallyExact": True,
        })
    top_level_actions = [row for row in actions if row["start"] < sequence_end]
    if len(top_level_actions) < action_count:
        raise ValueError(
            f"skillTimelineSharedSequence.topLevelActions={len(top_level_actions)} expected>={action_count}"
        )
    # Nested sequences can contribute union records. The root sequence's first
    # action count is independently retained, while all reached unions must be
    # contracted and exact.
    return {
        "status": "exact-first-timeline-shared-sequence-record",
        "parserCursor": reader.pos,
        "hardLimit": hard_limit,
        "timelineActionsCount": timeline_count,
        "firstSequenceActionDataCount": action_count,
        "firstActionTag": first_tag,
        "firstTimelineAction": {
            "start": timeline_start,
            "end": reader.pos,
            "sequenceEnd": sequence_end,
            "actionData": actions,
            "wholeRecordExact": True,
        },
        "namedRanges": _named_ranges(reader),
        "wholeFirstTimelineActionExact": True,
        "wholeTimelineListExact": timeline_count == 1,
        "wholeActionGroupDataExact": timeline_count == 1,
        "wholeSkillDataExact": False,
        "evidenceBoundary": contract["evidenceBoundary"],
    }
