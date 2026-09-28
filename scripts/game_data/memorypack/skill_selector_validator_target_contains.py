"""Selected one-member TargetContainsValidator nested SkillData route.

``SelectorValidator`` physical tag ``0x0C`` has its own selected switch
table, not an AbilityActionData action tag.  :mod:`skill_selector_selected`
checks the hash-pinned switch entry, resolves the reached branch's type-usage
load to the generated wrapper and confirms its one-member plan, whose
``parentTargetSettings`` child goes to the existing bounded TargetSettings
reader.  ``FF`` is the separate null-wrapper state.  Unknown children still
stop at their owning cursor; no runtime containment result is inferred.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.skill_selector_selected import validate_selected_selector_route


TAG = 0x0C
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_TargetContainsValidator_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.Selector+TargetContainsValidator+Data"


def validate_current_native_contract() -> dict[str, Any]:
    return validate_selected_selector_route(
        "SelectorValidator", TAG, wrapper_name=WRAPPER_NAME,
        wrapped_type=TYPE_NAME, member_name="parentTargetSettings",
        child_type="Beyond.Gameplay.Core.TargetSettings",
    )


def decode_target_contains_validator(reader: Reader) -> None:
    validate_current_native_contract()
    if reader.peek() != TAG:
        raise ValueError("skillSelectorValidatorTargetContains.unionTag:unsupported")
    start = reader.pos
    reader.take(1, "nested-validator-union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-nested-validator-wrapper")
    else:
        reader.header(1)
        reader.target_profile()
    reader.records.append({"start": start, "end": reader.pos,
                           "kind": "anonymous-selector-validator-profile"})
