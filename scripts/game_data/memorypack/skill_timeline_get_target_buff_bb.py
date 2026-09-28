"""Bounded selected SkillData GetTargetBuffBBAction (0x00C3) profile.

The generated wrapper names the stored fields; the nested TargetSettings
selector keeps its separate structural-only evidence tier and fails closed on
unreviewed children. No runtime blackboard lookup is inferred.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineGetTargetBuffBB"
TAG = 0x00C3
TYPE_NAME = "Beyond.Gameplay.Core.GetTargetBuffBBAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_GetTargetBuffBBAction_DataForMemoryPack"
MEMBERS = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
    ("blackboardKey", "string", None, None),
    ("buffId", "string", None, None),
    ("desiredKey", "string", None, None),
    ("targetSettings", "object", None, None),
)
CHILD_TYPE = "Beyond.Gameplay.Core.TargetSettings"


@lru_cache(maxsize=1)
def _selected_plan() -> dict[str, Any]:
    routes, resolver, audit = resolve_routes()
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    wrapper = resolver.wrappers.get(definition) if resolver and isinstance(definition, int) else None
    plan = resolver.plans.get(definition) if resolver and isinstance(definition, int) else None
    observed = tuple((member.name, member.kind, member.width, member.scalar) for member in plan or ())
    child = (
        resolver.wrappers.get(plan[-1].ref)
        if resolver and plan and len(plan) == len(MEMBERS)
        and isinstance(plan[-1].ref, int) else None
    )
    if (
        audit.get("status") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "structuralOnly"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None
        or wrapper.wrapped_type != TYPE_NAME
        or observed != MEMBERS
        or child is None
        or child.wrapped_type != CHILD_TYPE
    ):
        raise ValueError(f"{LABEL}.native:route-or-plan-drift:{route!r}:{observed!r}")
    return {
        "status": "validated", "evidenceBoundary": "structuralOnly",
        "nativeInputs": audit.get("nativeInputs"), "unionTag": TAG,
        "typeName": TYPE_NAME, "memberCount": len(MEMBERS),
        "childType": CHILD_TYPE,
        "source": "selected dispatcher and generated wrapper read plan",
    }


def validate_current_native_contract() -> dict[str, Any]:
    return _selected_plan()


def decode_get_target_buff_bb_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    _selected_plan()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(MEMBERS))
    reader.take(1, "GetTargetBuffBBAction.isEnable.bool-byte")
    for _ in range(3):
        reader.take(4, "GetTargetBuffBBAction.scalar32")
    for _ in range(3):
        reader.byte_payload()
    reader.target_profile()
