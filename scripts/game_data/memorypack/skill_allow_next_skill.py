"""Re-derived finite SkillData AllowNextSkillAction 0x000E reader.

The installed dispatcher and generated wrapper derive this five-member plan:
the common fixed prefix followed by a nullable List<string>.  The route is
re-evaluated for the selected build instead of pinning build addresses in code.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillAllowNextSkill"
TAG = 0x000E
TYPE_NAME = "Beyond.Gameplay.Core.AllowNextSkillAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_AllowNextSkillAction_DataForMemoryPack"
MEMBERS = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
    ("allowedSkillIdList", "list", None, None),
)


@lru_cache(maxsize=1)
def _selected_plan() -> dict[str, Any]:
    routes, resolver, audit = resolve_routes()
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    wrapper = resolver.wrappers.get(definition) if resolver and definition is not None else None
    plan = resolver.plans.get(definition) if resolver and definition is not None else None
    observed = tuple(
        (member.name, member.kind, member.width, member.scalar)
        for member in plan or ()
    )
    final = plan[-1] if plan else None
    if (
        audit.get("status") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None
        or wrapper.wrapped_type != TYPE_NAME
        or observed != MEMBERS
        or final is None
        or final.element is None
        or final.element.kind != "string"
    ):
        raise ValueError(f"{LABEL}.native:route-or-plan-drift:{route!r}:{observed!r}")
    return {
        "status": "validated",
        "nativeInputs": audit.get("nativeInputs"),
        "wrapperName": WRAPPER_NAME,
        "typeName": TYPE_NAME,
        "unionTag": TAG,
        "memberCount": len(MEMBERS),
        "source": "selected dispatcher and generated wrapper read plan",
    }


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove physical route, type identity and ordered member kinds."""
    return _selected_plan()


def decode_allow_next_skill_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one bounded five-member action under the selected plan."""
    del depth
    _selected_plan()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(MEMBERS))
    reader.take(1, "AllowNextSkillAction.isEnable.bool-byte")
    for _ in range(3):
        reader.take(4, "AllowNextSkillAction.scalar32")
    count = reader.count(4, nullable=True)
    for _ in range(max(0, count)):
        reader.byte_payload()
