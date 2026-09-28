"""Selected BuffData EnableMoveColliderAction (0x00A6) stored-byte route.

The selected dispatcher and generated wrapper determine a five-member plan.
The mount-point field remains an enum32 bit pattern; no runtime effect or enum
label is inferred from the stored value.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.derived_schema import resolve_routes


TAG = 0x00A6
TYPE_NAME = "Beyond.Gameplay.Core.EnableMoveColliderAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_EnableMoveColliderAction_DataForMemoryPack"
MEMBERS = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
    ("mountPoint", "fixed", 4, "scalar32"),
)


@lru_cache(maxsize=1)
def validate_current_native_contract() -> dict[str, Any]:
    routes, resolver, audit = resolve_routes()
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    wrapper = resolver.wrappers.get(definition) if resolver and isinstance(definition, int) else None
    plan = resolver.plans.get(definition) if resolver and isinstance(definition, int) else None
    observed = tuple((member.name, member.kind, member.width, member.scalar) for member in plan or ())
    if (
        audit.get("status") != "validated"
        or audit.get("routeAudit") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None
        or wrapper.wrapped_type != TYPE_NAME
        or observed != MEMBERS
    ):
        raise ValueError(f"buffEnableMoveCollider.native:route-or-plan-drift:{route!r}:{observed!r}")
    return {
        "status": "validated", "nativeInputs": audit.get("nativeInputs"),
        "unionTag": TAG, "typeName": TYPE_NAME, "memberCount": len(MEMBERS),
        "source": "selected dispatcher and generated wrapper read plan",
    }


def decode_enable_move_collider_action(reader: Reader, tag: int, width: int) -> None:
    validate_current_native_contract()
    if tag != TAG or width != 1:
        raise ValueError("buffEnableMoveCollider.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(MEMBERS))
    reader.take(1, "EnableMoveColliderAction.isEnable.bool-byte")
    for _ in range(3):
        reader.take(4, "EnableMoveColliderAction.inherited-scalar32")
    reader.take(4, "EnableMoveColliderAction.mountPoint.enum32")
