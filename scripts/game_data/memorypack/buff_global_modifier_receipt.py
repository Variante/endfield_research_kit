"""Selected-build ownership receipt for BuffData.globalModifier lists.

The selected native root owns the list read and the field store. This
formatter contract authenticates the four-member item header and all four
setter calls in order: ``applyToReturnAtbGain`` (a leading boolean),
``formulaItem``, ``param`` (a bounded ``BlackboardDouble``) and ``type``.
The authenticated BuffData corpus rejoins every reached positive list to
this exact child cursor and its source identity.

Recorded negative: an earlier three-setter inspection missed this generated
wrapper; it is not evidence that the first member is anonymous.

Evidence tier: ``exact`` child layout for the selected build; missing or
mismatched native inputs yield no child labels. This child proof does not
close the parent -- the complete root reader must consume the same bytes
through physical EOF -- and it does not prove modifier arithmetic.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff import (
    format_offset,
    read_buff_blackboard_float_raw_field_bounded,
    read_buff_bool_field_bounded,
    validate_buff_read_limit,
)


CONTRACT_PATH = CONTRACTS_DIR / "buff_global_modifier_child_native.json"
SCHEMA = "endfield.buff-global-modifier-child-native-contract.v1"
LABEL = "buffGlobalModifierChild"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
                                      status="exact-current-build", label=LABEL)
    return value


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail,
                "evidenceBoundary": "No child labels on missing or mismatched native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_method_row(contract["formatterMethod"], label=LABEL)
    image.check_windows([contract["formatterWindow"]], label=LABEL)
    owner_name = contract["wrapper"]
    owners = [row for row in image.metadata.types if image.metadata.type_full_name(row) == owner_name]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:wrapper matches={len(owners)}")
    owner = owners[0]
    setters = image.setter_methods(owner, parameter="typeName", label=LABEL)
    if setters != [row[:3] for row in contract["setters"]]:
        raise ValueError(f"{LABEL}.native:setter-order")
    for row in contract["setters"]:
        image.validate_method_row([row[0], owner_name, row[1], row[3]], label=LABEL)
    image.check_instruction_windows(contract["instructionWindows"], label=LABEL)
    image.check_instruction_windows([contract["memberHeader"]], label=LABEL)
    for row, setter in zip(contract["instructionWindows"], contract["setters"]):
        raw = bytes.fromhex(row[1])
        target = row[0] + 5 + struct.unpack_from("<i", raw, 1)[0]
        expected_target = setter[3]
        if target != expected_target:
            raise ValueError(f"{LABEL}.native:setter-call={row[2]}")
    return {"status": "validated", "selectedReadOrder": contract["selectedReadOrder"],
            "formatterMethod": contract["formatterMethod"],
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_global_modifier_collection(
    data: bytes, start: int, end: int, *, source: str,
    native_validation: dict[str, Any],
    blackboard_native_validation: dict[str, Any] | None = None,
    require_end: bool = True,
) -> dict[str, Any]:
    """Decode one bounded globalModifier list with authenticated child ownership."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (blackboard_native_validation or {}).get("status") != "validated":
        raise ValueError(f"{LABEL}.blackboard-native:unvalidated")
    validate_buff_read_limit(data, start, end, LABEL)
    if start + 4 > end:
        raise ValueError(f"{LABEL}.count:truncated")
    count = struct.unpack_from("<i", data, start)[0]
    offset = start + 4
    if count == -1:
        if offset != end:
            raise ValueError(f"{LABEL}.cursor:expected={end} actual={offset}")
        return {"status": "exact-null", "source": source, "startOffset": start,
                "consumedEnd": offset, "count": -1, "elements": [],
                "wholeValueExact": True}
    if count < 0 or count > 256:
        raise ValueError(f"{LABEL}.count:invalid={count}")
    elements = []
    for index in range(count):
        item_start = offset
        validate_buff_read_limit(data, offset, end, f"{LABEL}[{index}]")
        if offset >= end or data[offset] != 4:
            actual = "EOF" if offset >= end else data[offset]
            raise ValueError(f"{LABEL}[{index}].member-count:expected=4 actual={actual}")
        offset += 1
        apply_to_return_atb_gain, offset = read_buff_bool_field_bounded(
            data, offset, end, f"{LABEL}[{index}].applyToReturnAtbGain")
        if offset + 4 > end:
            raise ValueError(f"{LABEL}[{index}].formulaItem:truncated-u32")
        formula_item = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        param, offset = read_buff_blackboard_float_raw_field_bounded(
            data, offset, end, f"{LABEL}[{index}].param")
        if offset + 4 > end:
            raise ValueError(f"{LABEL}[{index}].type:truncated-u32")
        modifier_type = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        elements.append({"index": index, "start": item_start, "end": offset,
                         "offset": format_offset(item_start),
                         "bytes": offset - item_start,
                         "applyToReturnAtbGain": apply_to_return_atb_gain,
                         "formulaItemRaw": formula_item, "param": param,
                         "typeRaw": modifier_type})
    if require_end and offset != end:
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={offset}")
    return {"status": "exact", "source": source, "startOffset": start,
            "consumedEnd": offset, "count": count, "elements": elements,
            "wholeValueExact": True,
            "selectedReadOrder": ["applyToReturnAtbGain", "formulaItem", "param", "type"]}
