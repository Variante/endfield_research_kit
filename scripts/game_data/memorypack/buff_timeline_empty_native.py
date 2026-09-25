"""Selected BuffData timeline-list ownership and null/empty suffix receipt.

The positive list still needs independent element boundaries.  This reader
only joins an empty or null list count to the following exact trigger tail.
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
from scripts.game_data.memorypack.buff import read_buff_trigger_interval_bool_tail_exact
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffTimelineEmpty"
SCHEMA = "endfield.buff-timeline-empty-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_timeline_empty_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"


def _contract() -> dict[str, Any]:
    return read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )[0]


def _call_target(image: Any, rva: int) -> int:
    code = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if code[0] != 0xE8:
        raise ValueError(f"{LABEL}.native:not-direct-call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", code, 1)[0]


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
    method = image.metadata.methods[spec[0]]
    owner = image.metadata.types[method.declaring_type]
    if (image.metadata.type_full_name(owner) != context["methodType"]
            or image.metadata.string(method.name_index) != context["methodName"]):
        raise ValueError(f"{LABEL}.native:method-identity")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:method-argument-count")
    argument = instance.arguments[0]
    if (argument.raw_type_record_hex != context["argumentRawHex"]
            or runtime_type_name(
                image.pe, image.metadata, argument.type_pointer_va
            ) != context["argumentType"]):
        raise ValueError(f"{LABEL}.native:method-argument-type")


def validate_current_native_contract() -> dict[str, Any]:
    """Validate root source contexts, calls, stores, and field types."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        return {"status": gate.status, "nativeStatus": gate.status,
                "detail": gate.detail,
                "evidenceBoundary": "No named timeline list on missing or changed native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "nativeStatus": "missing",
                "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "nativeStatus": "mismatched",
                "detail": "UnityPlayer.dll hash differs"}

    image = open_native_image(gate.gameassembly, gate.metadata)
    if contract["reviewedDependencies"] != [ROOT_CONTRACT_PATH.name]:
        raise ValueError(f"{LABEL}.native:dependencies")
    root = json.loads(ROOT_CONTRACT_PATH.read_text(encoding="utf-8"))
    if root.get("schemaVersion") != 1 or root["methods"][1] != contract["methods"][0]:
        raise ValueError(f"{LABEL}.native:root-dependency")
    image.check_windows(root["codeWindows"][:1], label=LABEL)
    for method in contract["methods"]:
        image.validate_method_row(method, label=LABEL)
    setter = image.metadata.methods[contract["methods"][1][0]]
    parameters = image.metadata.parameters_for(setter)
    if len(parameters) != 1:
        raise ValueError(f"{LABEL}.native:timeline-setter-parameter-count")
    setter_type_pointer = image.pe.u64_at_va(
        int(image.registration["types"], 16) + parameters[0].type_index * 8
    )
    if runtime_type_name(image.pe, image.metadata, setter_type_pointer) != contract["timelineFieldType"]:
        raise ValueError(f"{LABEL}.native:timeline-setter-parameter-type")
    image.check_instruction_windows(
        [[row["instructionRva"], row["instructionHex"]] for row in (
            contract["listSourceContext"], contract["followingSourceContext"]
        )], label=LABEL,
    )
    image.check_instruction_windows(contract["rootInstructions"], label=LABEL)
    _check_context(image, contract["listSourceContext"])
    _check_context(image, contract["followingSourceContext"])
    if (_call_target(image, contract["rootInstructions"][0][0]) != contract["listReadTargetRva"]
            or _call_target(image, contract["rootInstructions"][2][0]) != contract["followingReadTargetRva"]):
        raise ValueError(f"{LABEL}.native:read-target")

    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == contract["ownerType"]]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:owner-type-count={len(owners)}")
    owner = owners[0]
    offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, owner.index
    )
    fields = {image.metadata.string(field.name_index): field
              for field in image.metadata.fields_for(owner)}
    type_table = int(image.registration["types"], 16)
    for field_name, type_name, instruction, source_context in (
        (contract["timelineField"], contract["timelineFieldType"],
         contract["rootInstructions"][1], contract["listSourceContext"]),
        (contract["followingField"], contract["followingFieldType"],
         contract["rootInstructions"][3], contract["followingSourceContext"]),
    ):
        field = fields[field_name]
        pointer = image.pe.u64_at_va(type_table + field.type_index * 8)
        if (runtime_type_name(image.pe, image.metadata, pointer) != type_name
                or source_context["argumentType"] != type_name):
            raise ValueError(f"{LABEL}.native:field-type={field_name}")
        expected_store = b"\x48\x89\x81" + struct.pack("<I", offsets[field_name])
        if bytes.fromhex(instruction[1]) != expected_store:
            raise ValueError(f"{LABEL}.native:field-store={field_name}")

    return {"status": "validated", "nativeStatus": "validated",
            "nativeInputs": expected, "field": contract["timelineField"],
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_empty_timeline_suffix(
    data: bytes, count_start: int, *, native_validation: dict[str, Any]
) -> dict[str, Any]:
    """Require a null/zero list and immediate exact named trigger tail."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(count_start) is not int or not 0 <= count_start <= len(data) - 4:
        raise ValueError(f"{LABEL}.boundary:invalid-count-start={count_start!r}")
    count = struct.unpack_from("<i", data, count_start)[0]
    if count not in (-1, 0):
        raise ValueError(f"{LABEL}.count:positive-or-invalid={count}")
    trigger_start = count_start + 4
    trigger, use_time_dilation, wait_first, end = (
        read_buff_trigger_interval_bool_tail_exact(data, trigger_start)
    )
    return {
        "status": "exact-null-or-empty-list-to-eof",
        "startOffset": count_start, "consumedEnd": trigger_start,
        "count": count, "representation": "null" if count == -1 else "empty",
        "followingField": "triggerInterval",
        "followingStart": trigger_start,
        "followingEnd": end,
        "triggerInterval": trigger,
        "useTimeDilationDt": use_time_dilation,
        "waitFirstTriggerInterval": wait_first,
        "wholeTimelineListExact": True,
        "positiveTimelineInteriorExact": False,
    }
