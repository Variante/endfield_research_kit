"""Selected-build ownership and byte replay for BuffData.stackingSettings.

This child receipt names the compact stacking key branch without changing the
legacy Buff suffix parser. The following tag/timeline fields remain separate
proof obligations even when a standalone corpus replay reaches EOF.
"""
from __future__ import annotations

import hashlib
import json
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.buff import (
    read_buff_bool_field,
    read_buff_u32_field,
    skip_buff_stack_effects_effect_actions_body,
)
from scripts.game_data.memorypack.core import CONTRACTS_DIR, read_memorypack_utf8_string


LABEL = "buffStackingCompact"
SCHEMA = "endfield.buff-stacking-compact-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_stacking_compact_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"


def _contract() -> dict[str, Any]:
    return read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )[0]


def _selected_type(image: Any, name: str) -> Any:
    matches = [row for row in image.metadata.types
               if image.metadata.type_full_name(row) == name]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(matches)}")
    return matches[0]


def _check_context(image: Any, context: dict[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(image.gameassembly), offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index={index}")
    spec = struct.unpack(
        "<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12
        )
    )
    if list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:method-spec={spec!r}")
    instantiation = image.instantiations.resolve(spec[2])
    if len(instantiation.arguments) != 1:
        raise ValueError(f"{LABEL}.native:argument-count")
    argument = bytes.fromhex(instantiation.arguments[0].raw_type_record_hex)
    if argument.hex().upper() != context["argumentRawHex"]:
        raise ValueError(f"{LABEL}.native:argument-raw")
    definition = struct.unpack_from("<Q", argument)[0]
    if (definition != context["typeDefinition"]
            or image.type_name(definition) != context["typeName"]
            or argument[10] != context["typeKind"]):
        raise ValueError(f"{LABEL}.native:argument-type")


def _call_target(image: Any, rva: int) -> int:
    instruction = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if instruction[0] != 0xE8:
        raise ValueError(f"{LABEL}.native:not-direct-call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", instruction, 1)[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Check the root field join, child width/order, and following tag count."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        return {"status": gate.status, "nativeStatus": gate.status, "detail": gate.detail,
                "evidenceBoundary": "No named compact branch on missing or mismatched native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "nativeStatus": "missing", "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "nativeStatus": "mismatched", "detail": "UnityPlayer.dll hash differs"}

    image = open_native_image(gate.gameassembly, gate.metadata)
    if image.code_registration != contract["codeRegistrationVa"]:
        raise ValueError(f"{LABEL}.native:code-registration")
    if contract["reviewedDependencies"] != [ROOT_CONTRACT_PATH.name]:
        raise ValueError(f"{LABEL}.native:dependencies")
    root = json.loads(ROOT_CONTRACT_PATH.read_text(encoding="utf-8"))
    if root.get("schemaVersion") != 1 or root["methods"][1] != contract["methods"][0]:
        raise ValueError(f"{LABEL}.native:root-dependency")
    image.check_windows(root["codeWindows"][:1], label=LABEL)
    for method in contract["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)
    for group in ("rootInstructions", "childInstructions", "stringHelperInstructions", "tagArrayInstructions"):
        image.check_instruction_windows(contract[group], label=LABEL)
    _check_context(image, contract["rootSourceContext"])
    _check_context(image, contract["tagSourceContext"])

    wrapper = image.metadata.types[contract["wrapper"]["typeDefinition"]]
    if image.metadata.type_full_name(wrapper) != contract["wrapper"]["typeName"]:
        raise ValueError(f"{LABEL}.native:wrapper-name")
    if image.setter_methods(wrapper, parameter="typeIndex", label=LABEL) != contract["wrapper"]["setterMethods"]:
        raise ValueError(f"{LABEL}.native:wrapper-setter-order")
    owner_name, _, owner_field = contract["ownerField"].partition("::")
    owner = _selected_type(image, owner_name)
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
    store = bytes.fromhex(contract["rootInstructions"][1][1])
    if store != b"\x48\x89\x81" + struct.pack("<I", offsets[owner_field]):
        raise ValueError(f"{LABEL}.native:owner-store-offset")
    declared = next(field for field in image.metadata.fields_for(owner)
                    if image.metadata.string(field.name_index) == owner_field)
    type_table = int(image.registration["types"], 16)
    pointer = image.pe.u64_at_va(type_table + declared.type_index * 8)
    if runtime_type_name(image.pe, image.metadata, pointer) != contract["rootSourceContext"]["typeName"]:
        raise ValueError(f"{LABEL}.native:owner-field-type")
    if _call_target(image, contract["childInstructions"][0][0]) != contract["codeWindows"][1]["startRva"]:
        raise ValueError(f"{LABEL}.native:string-helper-call")
    if _call_target(image, contract["rootInstructions"][2][0]) != contract["codeWindows"][2]["startRva"]:
        raise ValueError(f"{LABEL}.native:following-tag-call")
    if _call_target(image, contract["rootInstructions"][0][0]) != contract["rootChildReaderRva"]:
        raise ValueError(f"{LABEL}.native:root-child-call")
    tags_offset = offsets["tagsAfterTriggerExtendBuffAction"]
    if bytes.fromhex(contract["rootInstructions"][3][1]) != b"\x48\x89\x41" + bytes([tags_offset]):
        raise ValueError(f"{LABEL}.native:following-tag-store-offset")
    return {"status": "validated", "nativeStatus": "validated",
            "field": contract["ownerField"], "nativeInputs": expected,
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_stacking_settings_compact(
    data: bytes, start: int, *, native_validation: dict[str, Any]
) -> dict[str, Any]:
    """Replay one child, preserving null/empty/nonempty key distinctions."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or not 0 <= start < len(data):
        raise ValueError(f"{LABEL}.boundary:invalid-start={start!r}")
    offset = start
    if data[offset] != 12:
        raise ValueError(f"{LABEL}.member-count={data[offset]}")
    offset += 1
    identifier_type_raw = data[offset]
    offset += 1
    need_effect, offset = read_buff_bool_field(data, offset, "stackingSettings.isNeedStackEffect")
    if offset + 4 > len(data):
        raise ValueError(f"{LABEL}.maxStackCnt:truncated")
    max_count = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    max_key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{LABEL}.maxStackCntKey:{error}")
    negate, offset = read_buff_bool_field(data, offset, "stackingSettings.negatePriority")
    if offset + 4 > len(data):
        raise ValueError(f"{LABEL}.priority:truncated")
    priority_bits = data[offset:offset + 4].hex().upper()
    offset += 4
    priority_key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{LABEL}.priorityKey:{error}")
    count, offset = read_buff_u32_field(data, offset, "stackingSettings.stackEffectsCount")
    if count > 256:
        raise ValueError(f"{LABEL}.stackEffectsCount:large={count}")
    body_start = offset
    body_status = "empty"
    key_offset: int
    key: str | None
    if count:
        zero_end = offset + count * 5
        zero_items = zero_end <= len(data)
        probe = offset
        for _ in range(count):
            if not zero_items or data[probe] != 1 or struct.unpack_from("<I", data, probe + 1)[0] != 0:
                zero_items = False
                break
            probe += 5
        if zero_items:
            offset = zero_end
            body_status = "zero-action-items"
        else:
            details, offset = skip_buff_stack_effects_effect_actions_body(data, offset, count)
            body_status = "opaque-effectActions"
            if details["stackingKeyPrefixHandling"] == "consumed-empty-string-prefix":
                key_offset = int(details["stackingKeyPrefixOffset"], 0)
                if offset != key_offset + 4 or data[key_offset:offset] != b"\x00" * 4:
                    raise ValueError(f"{LABEL}.stackingKey:consumed-prefix-mismatch")
                key = ""
                body_end = key_offset
            else:
                key_offset = offset
                key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
                if error:
                    raise ValueError(f"{LABEL}.stackingKey:{error}")
                body_end = key_offset
    if not count or body_status == "zero-action-items":
        key_offset = offset
        body_end = offset
        key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
        if error:
            raise ValueError(f"{LABEL}.stackingKey:{error}")
    if offset + 2 > len(data):
        raise ValueError(f"{LABEL}.stackingType:truncated-word")
    type_offset = offset
    stacking_type_raw = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    max_key_enabled, offset = read_buff_bool_field(data, offset, "stackingSettings.useMaxStackCntKey")
    priority_key_enabled, offset = read_buff_bool_field(data, offset, "stackingSettings.usePriorityKey")
    key_length = struct.unpack_from("<i", data, key_offset)[0]
    if key_length < -1 or key_length > 256:
        raise ValueError(f"{LABEL}.stackingKey:length={key_length}")
    branch = "null" if key_length == -1 else "empty" if key_length == 0 else "nonempty"
    return {
        "status": "exact-child-cursor", "startOffset": start, "consumedEnd": offset,
        "memberCount": 12, "identifierTypeRaw": identifier_type_raw,
        "isNeedStackEffect": need_effect, "maxStackCnt": max_count,
        "maxStackCntKey": max_key, "negatePriority": negate,
        "priorityRawBitsHex": priority_bits, "priorityKey": priority_key,
        "stackEffectsCount": count, "stackEffectsBodyStatus": body_status,
        "stackEffectsBodyRange": [body_start, body_end],
        "stackingKeyBranch": branch, "stackingKey": key,
        "stackingKeyLengthRaw": key_length,
        "stackingKeyRange": [key_offset, type_offset],
        "stackingTypeRaw": stacking_type_raw,
        "stackingTypeRange": [type_offset, type_offset + 2],
        "useMaxStackCntKey": max_key_enabled,
        "usePriorityKey": priority_key_enabled,
        "evidenceBoundary": "Selected native source order and exact stored child cursor; nested stack effects and runtime stacking remain unresolved.",
    }
