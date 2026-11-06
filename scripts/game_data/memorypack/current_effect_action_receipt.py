"""Current EffectAction receipt composed from an active native source operation.

The literal wrapper selects the physical current route. Every named parent read
and positive child uses the same authenticated program/capabilities as the
current Skill reader. Historical EffectAction tags and anonymous windows provide
no authority here. A closed action never certifies its enclosing Buff root.
"""
from __future__ import annotations

from scripts.game_data.memorypack.skill_timeline_current_sequence import (
    validate_program,
)
from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence


WRAPPER = "Beyond.MemoryPack.Beyond_Gameplay_Core_EffectAction_EffectActionDataForMemoryPack"
TYPE = "Beyond.Gameplay.Core.EffectAction+EffectActionData"
SCHEMA = "endfield.current-effect-action-receipt.v1"


def current_program(operation):
    selected = prepared_current_sequence(operation)
    rows = [row for row in selected.proof["programs"]
            if row.get("family") == "AbilityActionData" and row.get("wrapperName") == WRAPPER]
    if len(rows) != 1:
        raise ValueError("currentEffectAction: unique source-owned wrapper route required")
    row = selected.route("AbilityActionData", rows[0]["tag"])
    validate_program(row)
    if row["wrappedType"] != TYPE or row["memberCount"] != 20:
        raise ValueError("currentEffectAction: current twenty-member source program required")
    return selected, row


def decode_current_effect_action(data, *, operation, source, logical_sha256, start, end):
    from scripts.game_data.memorypack.current_action_receipts import _decode_program
    selected, row = current_program(operation)
    result = _decode_program(data, selected=selected, row=row, source=source,
        logical_sha256=logical_sha256, start=start, end=end)
    return dict(result, schema=SCHEMA, nativeInputs=selected.proof['nativeInputs'])
