"""Selected one-member ProjectileFinder nested SkillData route."""
from __future__ import annotations

from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.skill_selector_selected import validate_selected_selector_route


TAG = 0x0F
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_ProjectileFinder_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.Selector+ProjectileFinder+Data"


def validate_current_native_contract() -> dict[str, Any]:
    return validate_selected_selector_route(
        "SelectorFinder", TAG, wrapper_name=WRAPPER_NAME,
        wrapped_type=TYPE_NAME, member_name="shapeData",
        child_type="Beyond.Gameplay.ColliderShapeData",
    )


def decode_projectile_finder(reader: Reader) -> None:
    validate_current_native_contract()
    if reader.peek() != TAG:
        raise ValueError("skillSelectorFinderProjectile.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "nested-finder-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-nested-finder-wrapper")
    else:
        reader.header(1)
        reader.collider_shape_profile()
    reader.records.append({"start": start, "end": reader.pos,
                           "kind": "anonymous-selector-finder-profile"})
