"""Selected native and source-byte receipts for EffectActionCfg blackboard children.

The selected EffectAction and EffectActionCfg readers fix each parent span.
This adapter names the three BlackboardVector3 members and reuses the
independently selected BlackboardDouble child reader for every scalar leaf.

The generated vector wrapper names ``x``, ``y`` and ``z`` in the same order
as three selected ``BlackboardDouble`` generic source reads, with direct
stores to the corresponding runtime fields. Inside each component, and in the
configuration's two direct scalar blackboard children, the scalar reader
names ``blackboardKey``, ``useBlackboardKey`` and the raw four-byte
``value``. The VFS and source-hash gate reparses every reached action and
requires each nested child to close at the enclosing field boundary. This
closes the stored blackboard interiors on the reached branch only: key
strings are not decoded, no live provider is selected, no coordinate meaning
is assigned, and positive effect arrays and the enclosing BuffData record
remain open.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_effect_action_receipt as action
from scripts.game_data.memorypack import buff_effect_config_child_receipt as config
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.buff-effect-vector-child-receipt.v1"
LABEL = "buffEffectVectorChild"
CONTRACT_PATH = CONTRACTS_DIR / "buff_effect_vector_child_native.json"
DOUBLE_TYPE = "Beyond.Blackboard+BlackboardDouble"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.buff-effect-vector-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    members = value.get("readOrder")
    if (
        value.get("sourceReaderContract") != "buff_9a_native.json"
        or value.get("parentConfigContract") != "buff_effect_config_child_native.json"
        or not isinstance(members, list) or len(members) != 3
        or [row.get("fieldName") for row in members] != ["x", "y", "z"]
        or len(value.get("vectorParentFields", [])) != 3
        or len(set(value["vectorParentFields"])) != 3
        or len(value.get("vectorReaderMethodIndices", [])) != 2
        or len(value.get("vectorReaderWindowStarts", [])) != 2
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck three selected generic reads, setters, stores and scalar child."""
    contract = _contract()
    expected = contract["nativeInputs"]
    parent = config.validate_current_native_contract()
    scalar_native = scalar.validate_current_native_contract()
    parent_contract = config._contract()
    if (
        parent.get("status") != "validated"
        or parent.get("nativeInputs") != expected
        or scalar_native.get("status") != "validated"
        or scalar_native.get("selectedReadOrder")
        != ["blackboardKey", "useBlackboardKey", "value"]
        or parent_contract.get("nativeInputs") != expected
    ):
        raise ValueError(f"{LABEL}.native:parent-or-scalar-gate")
    source, _ = read_reviewed_contract(
        CONTRACTS_DIR / contract["sourceReaderContract"],
        status=None, schema=None, label=LABEL,
    )
    if (
        source.get("schemaVersion") != 1
        or source.get("anonymousReadOrder", {}).get("vector3")
        != ["scalar-payload"] * 3
    ):
        raise ValueError(f"{LABEL}.native:source-contract-shape")
    parent_fields = [row for row in parent_contract["readOrder"]
                     if row["kind"] == "vector"]
    if (
        [row["fieldName"] for row in parent_fields] != contract["vectorParentFields"]
        or any(row["declaredType"] != contract["vectorRuntimeTypeName"]
               for row in parent_fields)
    ):
        raise ValueError(f"{LABEL}.native:parent-vector-binding")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    methods = [row for row in source["methods"]
               if row[0] in contract["vectorReaderMethodIndices"]]
    windows = [row for row in source["codeWindows"]
               if row["startRva"] in contract["vectorReaderWindowStarts"]]
    if (
        [row[0] for row in methods] != contract["vectorReaderMethodIndices"]
        or [row["startRva"] for row in windows]
        != contract["vectorReaderWindowStarts"]
    ):
        raise ValueError(f"{LABEL}.native:vector-method-or-window")
    for row in methods:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(windows, label=LABEL)
    if (
        image.type_name(contract["vectorWrapperTypeDefinition"])
        != contract["vectorWrapperName"]
        or image.type_name(contract["vectorRuntimeTypeDefinition"])
        != contract["vectorRuntimeTypeName"]
    ):
        raise ValueError(f"{LABEL}.native:vector-type")
    wrapper = image.metadata.types[contract["vectorWrapperTypeDefinition"]]
    setters = image.setter_methods(wrapper, parameter="typeName", label=LABEL)
    if setters != [[row["setterMethodIndex"],
                    f"set___{row['fieldName']}__", DOUBLE_TYPE]
                   for row in contract["readOrder"]]:
        raise ValueError(f"{LABEL}.native:vector-setters")
    derived = derive_from_image(image).get(contract["vectorWrapperTypeDefinition"])
    if (
        derived is None or len(derived.members) != 3
        or [(row.name, row.method_index, row.declared_type)
            for row in derived.members]
        != [(row["fieldName"], row["setterMethodIndex"], DOUBLE_TYPE)
            for row in contract["readOrder"]]
    ):
        raise ValueError(f"{LABEL}.native:vector-derived-order")
    offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration,
        contract["vectorRuntimeTypeDefinition"],
    )
    if offsets != {row["fieldName"]: row["runtimeFieldOffset"]
                   for row in contract["readOrder"]}:
        raise ValueError(f"{LABEL}.native:vector-runtime-offsets")
    reader_start, reader_end = windows[1]["startRva"], windows[1]["endRva"]
    contexts = source["nestedContexts"]
    for index, row in enumerate(contract["readOrder"]):
        context = contexts[row["sourceContextIndex"]]
        next_rva = (contract["readOrder"][index + 1]["sourceContextRva"]
                    if index + 1 < len(contract["readOrder"]) else reader_end)
        if (
            context["instructionRva"] != row["sourceContextRva"]
            or context["typeName"] != DOUBLE_TYPE
            or not reader_start < row["sourceContextRva"]
            < row["storeRva"] < next_rva <= reader_end
        ):
            raise ValueError(f"{LABEL}.native:source-context={index}")
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        spec_index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if spec_index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index={index}")
        spec = struct.unpack("<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + spec_index * 12, 12
        ))
        if (
            list(spec) != context["methodSpec"]
            or image.instantiations.resolve(spec[2]).arguments[0].raw_type_record_hex
            != context["argumentRawHex"]
        ):
            raise ValueError(f"{LABEL}.native:method-spec-type={index}")
        raw = bytes.fromhex(row["storeHex"])
        if (
            image.pe.bytes_at_va(image.pe.image_base + row["storeRva"], len(raw))
            != raw or raw != bytes((0x49, 0x89, 0x40, row["runtimeFieldOffset"]))
        ):
            raise ValueError(f"{LABEL}.native:direct-store={index}")
    return {
        "status": "validated", "nativeInputs": expected,
        "effectConfigNative": parent,
        "scalarNative": scalar_native,
        "vectorMemberNames": [row["fieldName"] for row in contract["readOrder"]],
        "vectorParentFields": list(contract["vectorParentFields"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_blackboard_vector3_value(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Read the exact stored vector; its caller independently owns the typed field."""
    contract = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("vectorMemberNames") != [row["fieldName"] for row in contract["readOrder"]]
            or not source or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.value:native-source-or-span")
    reader = Reader(data, source, end)
    reader.pos = start
    if reader.peek() == 0xFF:
        reader.take(1, "null-vector")
        status = "exact-null"
        members = []
    else:
        reader.header(len(contract["readOrder"]))
        status = "named-vector-members-exact-span"
        members = []
        for name in native_validation["vectorMemberNames"]:
            member_start = reader.pos
            reader.scalar_payload()
            member = scalar.decode_adding_cooldown(
                data, member_start, reader.pos,
                native_validation=native_validation["scalarNative"],
            )
            if member.get("wholeValueExact") is not True:
                raise ValueError(f"{LABEL}.value:scalar-child-incomplete")
            members.append({"fieldName": name, "start": member_start,
                            "end": reader.pos, "child": member})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.value:vector-end")
    return {"start": start, "end": end, "status": status, "namedMembers": members}


def decode_effect_vector_child_receipt(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
    action_native: dict[str, Any],
) -> dict[str, Any]:
    """Reparse one exact parent and name its five blackboard field interiors."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("vectorParentFields")
        != contract["vectorParentFields"]
        or native_validation.get("vectorMemberNames")
        != [row["fieldName"] for row in contract["readOrder"]]
        or not isinstance(source, str) or not source
        or not isinstance(logical_sha256, str)
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}.decode:validation-or-source")
    parent = action.decode_effect_action_receipt(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, native_validation=action_native,
    )
    fields = [field for field in parent["namedFields"]
              if field["fieldName"] == "effectActionCfg"
              and field["kind"] == "effect-configuration-profile"]
    if len(fields) != 1:
        raise ValueError(f"{LABEL}.decode:config-parent-field")
    parent_field = fields[0]
    child = config.decode_effect_config_child_receipt(
        data, source=source, logical_sha256=logical_sha256,
        start=parent_field["start"], end=parent_field["end"],
        native_validation=native_validation["effectConfigNative"],
    )
    if child["status"] != "named-direct-members-exact-span":
        raise ValueError(f"{LABEL}.decode:config-null")
    scalars: list[dict[str, Any]] = []
    vectors: list[dict[str, Any]] = []
    for field in child["namedFields"]:
        if field["kind"] == "scalar":
            scalar_child = scalar.decode_adding_cooldown(
                data, field["start"], field["end"],
                native_validation=native_validation["scalarNative"],
            )
            scalars.append({"fieldName": field["fieldName"],
                            "start": field["start"], "end": field["end"],
                            "child": scalar_child})
        elif field["fieldName"] in contract["vectorParentFields"]:
            if field["kind"] != "vector":
                raise ValueError(f"{LABEL}.decode:vector-kind={field['fieldName']}")
            value = decode_blackboard_vector3_value(
                data, source=source, logical_sha256=logical_sha256,
                start=field["start"], end=field["end"], native_validation=native_validation,
            )
            vectors.append({"fieldName": field["fieldName"], **value})
    if (
        [row["fieldName"] for row in scalars]
        != ["durationScaleBB", "lengthBB"]
        or [row["fieldName"] for row in vectors]
        != contract["vectorParentFields"]
    ):
        raise ValueError(f"{LABEL}.decode:config-blackboard-bindings")
    return {
        "schema": SCHEMA, "status": "named-config-blackboard-children-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "parentTag": action.TAG, "parentActionRange": [start, end],
        "effectConfigRange": [parent_field["start"], parent_field["end"]],
        "scalarChildren": scalars, "vectorChildren": vectors,
        "wholeConfigBlackboardChildrenExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": (
            "The selected EffectAction and EffectActionCfg readers fix every "
            "parent field extent. Selected vector source contexts, generated "
            "x/y/z setters and direct stores name the three vector members. "
            "The separately selected scalar reader names each stored leaf. "
            "Blackboard evaluation, effect execution, and the enclosing "
            "BuffData schema remain unresolved."
        ),
    }
