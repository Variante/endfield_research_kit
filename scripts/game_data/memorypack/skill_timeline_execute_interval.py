"""Selected SkillData ExecuteIntervalAction (0x00AE) stored-byte reader.

The selected dispatcher and generated wrapper supply the seven-member plan.
The nested SequenceActionData and BlackboardDouble grammars are independently
bounded by the shared action reader; unsupported children remain refusals.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineExecuteInterval"
TAG = 0x00AE
TYPE_NAME = "Beyond.Gameplay.Core.ExecuteIntervalAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ExecuteIntervalAction_DataForMemoryPack"
MEMBERS = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
    ("actionOnExecuting", "object", None, None),
    ("executeEachFrame", "fixed", 1, "bool"),
    ("executeInterval", "object", None, None),
)
CHILD_TYPES = (
    "Beyond.Gameplay.Core.SequenceActionData",
    "Beyond.Blackboard+BlackboardDouble",
)


@lru_cache(maxsize=1)
def _selected_plan() -> dict[str, Any]:
    routes, resolver, audit = resolve_routes()
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    wrapper = resolver.wrappers.get(definition) if resolver and isinstance(definition, int) else None
    plan = resolver.plans.get(definition) if resolver and isinstance(definition, int) else None
    observed = tuple((member.name, member.kind, member.width, member.scalar) for member in plan or ())
    children = tuple(
        resolver.wrappers.get(plan[index].ref).wrapped_type
        if resolver and plan and isinstance(plan[index].ref, int)
        and resolver.wrappers.get(plan[index].ref) is not None else None
        for index in (4, 6)
    ) if plan and len(plan) == len(MEMBERS) else ()
    if (
        audit.get("status") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None
        or wrapper.wrapped_type != TYPE_NAME
        or observed != MEMBERS
        or children != CHILD_TYPES
    ):
        raise ValueError(f"{LABEL}.native:route-or-plan-drift:{route!r}:{observed!r}:{children!r}")
    return {
        "status": "validated", "nativeInputs": audit.get("nativeInputs"),
        "unionTag": TAG, "typeName": TYPE_NAME, "memberCount": len(MEMBERS),
        "childTypes": list(CHILD_TYPES),
        "source": "selected dispatcher and generated wrapper read plan",
    }


def validate_current_native_contract() -> dict[str, Any]:
    return _selected_plan()


def decode_execute_interval_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    _selected_plan()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(MEMBERS))
    reader.take(1, "ExecuteIntervalAction.isEnable.bool-byte")
    for _ in range(3):
        reader.take(4, "ExecuteIntervalAction.scalar32")
    reader.sequence(depth + 1)
    reader.take(1, "ExecuteIntervalAction.executeEachFrame.bool-byte")
    reader.scalar_payload()
