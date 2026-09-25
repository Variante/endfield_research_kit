"""Finite SkillData readers for two selected four-member action routes.

The installed wrapper derivation supplies their read plans and dispatcher
identities. The reviewed Buff frontier independently authenticates 0x009E's
complete native reader. Values stay anonymous; this module only frames bytes.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data import buff_frontiers_native
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineFixedFour"
ROUTE_NAMES = {
    0x009E: "Beyond.MemoryPack.Beyond_Gameplay_Core_DisableRootMotionAction_DataForMemoryPack",
    0x00E8: "Beyond.MemoryPack.Beyond_Gameplay_Core_MarkCanInterrupt_DataForMemoryPack",
}
ROUTE_TYPES = {
    0x009E: "Beyond.Gameplay.Core.DisableRootMotionAction+Data",
    0x00E8: "Beyond.Gameplay.Core.MarkCanInterrupt+Data",
}
PLAN = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
)


def validate_current_native_contract() -> dict[str, Any]:
    """Fail closed unless both selected routes still have the exact plan."""
    frontier, frontier_audit = buff_frontiers_native.load_rows("frontier6")
    if frontier_audit.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:frontier6:{frontier_audit.get('status')}")
    root_motion = frontier.get(0x009E)
    if (
        not isinstance(root_motion, dict)
        or root_motion.get("wrapperName") != ROUTE_NAMES[0x009E]
        or root_motion.get("serializedMemberCount") != 4
        or root_motion.get("readOrder") != ["byte", "scalar32", "scalar32", "scalar32"]
    ):
        raise ValueError(f"{LABEL}.native:frontier6:0x009E-shape")

    routes, resolver, audit = resolve_routes()
    if audit.get("status") != "validated" or resolver is None:
        raise ValueError(f"{LABEL}.native:derived-routes:{audit.get('status')}")
    for tag, name in ROUTE_NAMES.items():
        route = routes.get(tag, {})
        definition = route.get("wrapperTypeDefinition")
        plan = resolver.plans.get(definition) if isinstance(definition, int) else None
        wrapper = resolver.wrappers.get(definition) if isinstance(definition, int) else None
        if (
            route.get("status") != "determined"
            or route.get("wrapperName") != name
            or route.get("evidenceTier") != "direct"
            or wrapper is None
            or wrapper.wrapped_type != ROUTE_TYPES[tag]
            or not isinstance(plan, tuple)
            or tuple((m.name, m.kind, m.width, m.scalar) for m in plan) != PLAN
        ):
            raise ValueError(f"{LABEL}.native:route-0x{tag:04X}-plan-drift")
    return {
        "status": "validated",
        "routeTags": [f"0x{tag:04X}" for tag in ROUTE_NAMES],
        "frontier6Status": frontier_audit["status"],
        "derivedRouteStatus": audit["status"],
    }


def decode_fixed_four_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume one reached route after the outer gate validates both plans."""
    del depth
    if tag not in ROUTE_NAMES or width != 1 or reader.peek() != tag:
        raise ValueError(f"{LABEL}.union-tag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(PLAN))
    reader.take(1, "anonymous-bool-byte")
    for _ in range(3):
        reader.take(4, "anonymous-scalar32")
