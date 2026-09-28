"""Selected two-member SnapPointFinder nested SkillData route.

The stored radius and target-settings children are structural data. This
reader does not assign live snap-point or target-selection behavior.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.skill_selector_selected import (
    validate_selected_selector_route_plan,
)


TAG = 0x14
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_SnapPointFinder_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.Selector+SnapPointFinder+Data"
MEMBERS = (
    ("radius", "Beyond.Blackboard+BlackboardDouble"),
    ("snapTargetSettings", "Beyond.Gameplay.Core.TargetSettings"),
)


def validate_current_native_contract() -> dict[str, Any]:
    return validate_selected_selector_route_plan(
        "SelectorFinder", TAG, wrapper_name=WRAPPER_NAME,
        wrapped_type=TYPE_NAME, members=MEMBERS,
    )


def decode_snap_point_finder(reader: Reader) -> None:
    """Consume only the selected tag-20 union and its two ordered children."""
    validate_current_native_contract()
    if reader.peek() != TAG:
        raise ValueError("skillSelectorFinderSnapPoint.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "nested-finder-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-nested-finder-wrapper")
    else:
        reader.header(len(MEMBERS))
        reader.scalar_payload()
        reader.target_profile()
    reader.records.append({
        "start": start, "end": reader.pos,
        "kind": "anonymous-selector-finder-profile",
    })
