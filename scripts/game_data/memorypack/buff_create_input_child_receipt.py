"""Selected native and exact-byte receipts for CreateBuffAction input children.

This names only the direct CreateBuffActionInput and AssignPair fields inside a
previously certified CreateBuffAction.buffs range. It does not infer assignment
execution or promote the enclosing BuffData record.

The registered ``CreateBuffActionInput`` reader consumes a five-member
wrapper: inherited ``assignBlackboard``, ``assignItems`` and ``buffId``,
then ``buffIdKey`` and ``readIdFromBlackboard``. The ``assignItems`` generic
source context resolves to ``List<AssignPair>``, and the registered
``AssignPair`` reader consumes ``directValueType``, ``inputValueKey``,
``numericValue``, ``stringValue``, ``targetKey`` and ``useDirectValue`` in
generated setter order. The gate checks source calls, destination stores,
runtime field offsets and complete reader windows against the selected
build, rechecks every current logical source hash, reparses each certified
CreateBuffAction parent, and requires the nested list to end exactly at the
parent's ``buffs`` field boundary. Reached input and assignment wrappers,
including positive assignment lists, close with named direct fields. String
members stay signed-length byte spans and ``numericValue`` raw float bits;
decoded strings and live assignment behavior are not claimed.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffCreateInputChild"
SCHEMA = "endfield.buff-create-input-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_create_input_child_native.json"
_INPUT_KINDS = (
    "byte", "counted-assignment-profiles", "byte-payload", "byte-payload", "byte",
)
_PAIR_KINDS = (
    "scalar32", "byte-payload", "raw-float32", "byte-payload", "byte-payload", "byte",
)


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-create-input-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    if (contract.get("readerContract") != "buff_92_native.json"
            or contract.get("parentActionContract") != "skill_timeline_create_buff_native.json"
            or len(contract.get("readerMethodIndices", ())) != 4
            or len(contract.get("readerWindowStarts", ())) != 6
            or set(contract.get("readerWindows", {})) != {"input", "assignPair"}
            or set(contract.get("assignmentListContext", {}))
            != {"instructionRva", "methodSpecIndex", "elementInstantiationIndex"}
            or len(contract.get("inputWrapper", {}).get("readOrder", ())) != 5
            or len(contract.get("assignPairWrapper", {}).get("readOrder", ())) != 6
            or [row[2] for row in contract.get("sourceReadCalls", {}).get("input", ())]
            != list(_INPUT_KINDS)
            or [row[2] for row in contract.get("sourceReadCalls", {}).get("assignPair", ())]
            != list(_PAIR_KINDS)):
        raise ValueError(f"{LABEL}.contract:shape")
    for wrapper, parts in ((contract["inputWrapper"], ("inheritedSetterMethods", "directSetterMethods")),
                           (contract["assignPairWrapper"], ("setterMethods",))):
        names = [row[1].removeprefix("set___").removesuffix("__")
                 for part in parts for row in wrapper[part]]
        if names != wrapper["readOrder"] or len(set(names)) != len(names):
            raise ValueError(f"{LABEL}.contract:setter-order")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck selected method windows, inherited setters and source calls."""
    contract = _contract()
    expected = contract["nativeInputs"]
    parent = json.loads((CONTRACTS_DIR / contract["parentActionContract"]).read_bytes())
    reader = json.loads((CONTRACTS_DIR / contract["readerContract"]).read_bytes())
    if (parent.get("schema") != "endfield.skill-timeline-create-buff-native-contract.v1"
            or parent.get("nativeInputs") != expected
            or parent.get("dispatcher", {}).get("unionTag") != contract["parentUnionTag"]
            or reader.get("schemaVersion") != 1
            or reader.get("anonymousReadOrder", {}).get("member5")
            != list(_INPUT_KINDS)
            or reader.get("anonymousReadOrder", {}).get("member6")
            != ["scalar32", "byte-payload", "scalar32", "byte-payload", "byte-payload", "byte"]):
        raise ValueError(f"{LABEL}.native:dependency-shape")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if (not unityplayer.is_file()
            or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    selected = tuple(contract["readerMethodIndices"])
    method_rows = [row for row in reader["methods"] if row[0] in selected]
    if tuple(row[0] for row in method_rows) != selected:
        raise ValueError(f"{LABEL}.native:reader-methods")
    for row in method_rows:
        image.validate_method_row(row, label=LABEL)
    selected_starts = set(contract["readerWindowStarts"])
    windows = [row for row in reader["codeWindows"] if row["startRva"] in selected_starts]
    if {row["startRva"] for row in windows} != selected_starts:
        raise ValueError(f"{LABEL}.native:reader-windows")
    image.check_windows(windows, label=LABEL)
    # The generic List<AssignPair> source context and registered list candidate
    # are authenticated by the shared reviewed reader audit, not by its name.
    audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["readerContract"],
    )
    context_contract = contract["assignmentListContext"]
    contexts = [row for row in audit["nestedContexts"]
                if row["instructionRva"] == context_contract["instructionRva"]]
    if (len(contexts) != 1
            or contexts[0]["methodSpecIndex"] != context_contract["methodSpecIndex"]
            or contexts[0]["generic"]["elementInstantiationIndex"]
            != context_contract["elementInstantiationIndex"]):
        raise ValueError(f"{LABEL}.native:assignment-list-context")
    input_wrapper = contract["inputWrapper"]
    owner = image.check_wrapper_inheritance(input_wrapper, label=LABEL)
    inherited = image.metadata.types[input_wrapper["parentTypeDefinition"]]
    if (image.setter_methods(inherited, parameter="typeName", label=LABEL)
            != input_wrapper["inheritedSetterMethods"]
            or image.setter_methods(owner, parameter="typeName", label=LABEL)
            != input_wrapper["directSetterMethods"]):
        raise ValueError(f"{LABEL}.native:input-setters")
    pair_wrapper = contract["assignPairWrapper"]
    pair_owner = image.check_wrapper_inheritance(pair_wrapper, label=LABEL)
    if (image.setter_methods(pair_owner, parameter="typeName", label=LABEL)
            != pair_wrapper["setterMethods"]):
        raise ValueError(f"{LABEL}.native:assign-pair-setters")
    for group, (start, end) in contract["readerWindows"].items():
        if not any(row["startRva"] == start and row["endRva"] == end for row in windows):
            raise ValueError(f"{LABEL}.native:{group}-reader-window")
        sites = contract["sourceReadCalls"][group]
        if not all(start <= row[0] < end for row in sites):
            raise ValueError(f"{LABEL}.native:{group}-site-bounds")
        if [row[0] for row in sites] != sorted({row[0] for row in sites}):
            raise ValueError(f"{LABEL}.native:{group}-site-order")
        for rva, target, _kind in sites:
            raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
            if (raw[:1] != b"\xe8"
                    or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target):
                raise ValueError(f"{LABEL}.native:{group}-source-call={rva:#x}")
    runtime_fields = contract.get("runtimeFields", ())
    if len(runtime_fields) != 3:
        raise ValueError(f"{LABEL}.native:runtime-field-types")
    offsets_by_name: dict[str, int] = {}
    for row in runtime_fields:
        definition = row["typeDefinition"]
        if image.type_name(definition) != row["typeName"]:
            raise ValueError(f"{LABEL}.native:runtime-field-type={definition}")
        current = runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, definition,
        )
        if current != row["offsets"] or set(current) & set(offsets_by_name):
            raise ValueError(f"{LABEL}.native:runtime-field-offsets={definition}")
        offsets_by_name.update(current)
    if set(offsets_by_name) != set(input_wrapper["readOrder"] + pair_wrapper["readOrder"]):
        raise ValueError(f"{LABEL}.native:runtime-field-set")
    direct = contract.get("directStores", ())
    setter_stores = contract.get("setterStores", ())
    if (len(direct) != 9 or len(setter_stores) != 2
            or {row[0] for row in direct} | {row[0] for row in setter_stores}
            != set(offsets_by_name)):
        raise ValueError(f"{LABEL}.native:destination-plan")
    image.check_instruction_windows([row[1:3] for row in direct], label=LABEL)
    for name, rva, raw_hex in direct:
        raw = bytes.fromhex(raw_hex)
        if len(raw) < 3 or raw[-1] != offsets_by_name[name]:
            raise ValueError(f"{LABEL}.native:destination-store={name}")
        group = "input" if name in input_wrapper["readOrder"] else "assignPair"
        index = (input_wrapper["readOrder"] if group == "input"
                 else pair_wrapper["readOrder"]).index(name)
        calls = contract["sourceReadCalls"][group]
        next_rva = calls[index + 1][0] if index + 1 < len(calls) else contract["readerWindows"][group][1]
        if not calls[index][0] < rva < next_rva:
            raise ValueError(f"{LABEL}.native:destination-order={name}")
    target_key_store = contract.get("targetKeyIndirectStore")
    if (not isinstance(target_key_store, list) or len(target_key_store) != 2
            or target_key_store[0] <= next(row[1] for row in direct if row[0] == "targetKey")
            or target_key_store[0] >= contract["sourceReadCalls"]["assignPair"][5][0]
            or target_key_store[1] != "488901"):
        raise ValueError(f"{LABEL}.native:target-key-indirect-store")
    image.check_instruction_windows([target_key_store], label=LABEL)
    for name, method_index, call_rva, setter_rva, store_rva, store_hex in setter_stores:
        if name not in input_wrapper["readOrder"]:
            raise ValueError(f"{LABEL}.native:setter-field={name}")
        method = image.metadata.methods[method_index]
        if (image.method_pointer_va(method) != image.pe.image_base + setter_rva
                or image.metadata.string(method.name_index)
                != f"set___{name}__"):
            raise ValueError(f"{LABEL}.native:setter-method={name}")
        raw_call = image.pe.bytes_at_va(image.pe.image_base + call_rva, 5)
        if (raw_call[:1] != b"\xe8"
                or call_rva + 5 + struct.unpack_from("<i", raw_call, 1)[0]
                != setter_rva):
            raise ValueError(f"{LABEL}.native:setter-call={name}")
        index = input_wrapper["readOrder"].index(name)
        source_calls = contract["sourceReadCalls"]["input"]
        next_rva = (source_calls[index + 1][0] if index + 1 < len(source_calls)
                    else contract["readerWindows"]["input"][1])
        if (not source_calls[index][0] < call_rva < next_rva
                or not setter_rva <= store_rva < setter_rva + 0x100
                or bytes.fromhex(store_hex)[-1] != offsets_by_name[name]):
            raise ValueError(f"{LABEL}.native:setter-store={name}")
        image.check_instruction_windows([[store_rva, store_hex]], label=LABEL)
    return {
        "status": "validated", "nativeInputs": expected,
        "inputReadOrder": input_wrapper["readOrder"],
        "assignPairReadOrder": pair_wrapper["readOrder"],
        "assignmentListMethodSpecIndex": context_contract["methodSpecIndex"],
        "runtimeFieldOffsets": offsets_by_name,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _raw_byte(reader: Reader, name: str) -> dict[str, Any]:
    start = reader.pos
    value = reader.take(1, name)[0]
    return {"fieldName": name, "start": start, "end": reader.pos,
            "rawHex": f"{value:02X}"}


def _raw_scalar(reader: Reader, name: str, *, floating: bool = False) -> dict[str, Any]:
    start = reader.pos
    raw = reader.take(4, name)
    row = {"fieldName": name, "start": start, "end": reader.pos,
           "rawHex": raw.hex().upper()}
    if not floating:
        row["storedInt32"] = struct.unpack("<i", raw)[0]
    return row


def _byte_payload(reader: Reader, name: str) -> dict[str, Any]:
    start = reader.pos
    length = reader.count(1, nullable=True)
    if length > 0:
        reader.take(length, f"{name}.source-bytes")
    return {"fieldName": name, "start": start, "end": reader.pos,
            "storedByteLength": length, "sourceBytesSha256": (
                hashlib.sha256(reader.data[start + 4:reader.pos]).hexdigest().upper()
                if length >= 0 else None),
            "stringDecodeClaimed": False}


def _assign_pair(reader: Reader, names: list[str]) -> dict[str, Any]:
    start = reader.pos
    if reader.peek() == 0xFF:
        reader.take(1, "null-assign-pair")
        return {"start": start, "end": reader.pos, "status": "exact-null-wrapper",
                "namedFields": []}
    reader.header(6)
    fields = [
        _raw_scalar(reader, names[0]), _byte_payload(reader, names[1]),
        _raw_scalar(reader, names[2], floating=True),
        _byte_payload(reader, names[3]), _byte_payload(reader, names[4]),
        _raw_byte(reader, names[5]),
    ]
    if [field["fieldName"] for field in fields] != names:
        raise ValueError(f"{LABEL}:assign-pair-field-order")
    return {"start": start, "end": reader.pos,
            "status": "named-six-member-exact-span", "namedFields": fields}


def decode_assignment_list(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Compose AssignPair elements after an independently typed parent join."""
    contract = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("assignPairReadOrder") != contract["assignPairWrapper"]["readOrder"]):
        raise ValueError(f"{LABEL}:assignment-native-not-validated")
    if (not isinstance(data, bytes) or not source or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}:assignment-source-range-or-hash")
    reader = Reader(data, source, end); reader.pos = start
    count = reader.count(1, nullable=True)
    elements = [_assign_pair(reader, contract["assignPairWrapper"]["readOrder"])
                for _ in range(max(0, count))]
    if reader.pos != end:
        raise ValueError(f"{LABEL}:assignment-list-end={reader.pos}; expected={end}")
    return {"source": source, "logicalSha256": logical_sha256.upper(),
            "start": start, "end": end, "count": count, "elements": elements,
            "recursiveStoredSchemaExact": True, "runtimeAssignmentKnown": False}


def decode_create_buff_input_list(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse one certified CreateBuffAction.buffs field to its exact end."""
    contract = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("inputReadOrder")
            != contract["inputWrapper"]["readOrder"]
            or native_validation.get("assignPairReadOrder")
            != contract["assignPairWrapper"]["readOrder"]):
        raise ValueError(f"{LABEL}:native-not-validated")
    if (not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()):
        raise ValueError(f"{LABEL}:logical-source-hash")
    if (not source or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}:source-range")
    reader = Reader(data, source, end)
    reader.pos = start
    count = reader.count(1, nullable=True)
    input_names = contract["inputWrapper"]["readOrder"]
    pair_names = contract["assignPairWrapper"]["readOrder"]
    items: list[dict[str, Any]] = []
    for _ in range(max(0, count)):
        item_start = reader.pos
        if reader.peek() == 0xFF:
            reader.take(1, "null-create-buff-input")
            items.append({"start": item_start, "end": reader.pos,
                          "status": "exact-null-wrapper", "namedFields": []})
            continue
        reader.header(5)
        first = _raw_byte(reader, input_names[0])
        list_start = reader.pos
        assign_count = reader.count(1, reserve=9, nullable=True)
        assignments = [_assign_pair(reader, pair_names)
                       for _ in range(max(0, assign_count))]
        assign_field = {"fieldName": input_names[1], "start": list_start,
                        "end": reader.pos, "count": assign_count,
                        "elements": assignments}
        fields = [first, assign_field,
                  _byte_payload(reader, input_names[2]),
                  _byte_payload(reader, input_names[3]),
                  _raw_byte(reader, input_names[4])]
        if [field["fieldName"] for field in fields] != input_names:
            raise ValueError(f"{LABEL}:input-field-order")
        items.append({"start": item_start, "end": reader.pos,
                      "status": "named-five-member-exact-span", "namedFields": fields})
    if reader.pos != end:
        raise ValueError(f"{LABEL}:input-list-end={reader.pos}; expected={end}")
    return {"schema": SCHEMA, "status": "named-input-list-exact-span",
            "source": source, "logicalSha256": logical_sha256.upper(),
            "start": start, "end": end, "count": count, "inputs": items,
            "wholeStoredSpanExact": True, "namedDirectMembersExact": True,
            "liveProviderSelectionKnown": False,
            "runtimeAssignmentKnown": False, "wholeBuffDataExact": False}
