"""Project IFix table, frame, return, branch, and exception operands through native bodies.

The selected ``PatchManager.LoadInternal`` body preserves file-table order in
the VM's method tables. ``VirtualMachine.Execute`` indexes those tables with
the low 16 call-operand bits, uses signed branch offsets relative to the
current instruction, selects the VM's string/field tables, and uses a
``StackSpace`` header for frame slots. Actual execution remains open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.ifix_patch import (
    EXCEPTION_RECORD_SIZE,
    ordered_signature_parameters,
    parse_ifix_patch,
)
from scripts.game_data.ifix_vm_instruction_native import (
    decode_patch_opcodes,
    selected_opcode_layout,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import (
    enum_members,
    field_defaults,
    runtime_type_name,
    runtime_type_field_offsets,
)


DEFAULT_CONTRACT = CONTRACTS_DIR / "ifix_vm_operands_native.json"
SCHEMA = "endfield.ifix-vm-operands-native-contract.v11"


class VMOperandEvidenceError(ValueError):
    """A selected native, contract, or patch-file gate did not validate."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _int_hex(value: Any, label: str) -> int:
    try:
        return int(str(value), 16)
    except ValueError as error:
        raise VMOperandEvidenceError(f"{label}: invalid hex value {value!r}") from error


def _validate_body_bytes(
    consumer: dict[str, Any], body: bytes, rva: int, *, label: str = "consumer"
) -> str:
    actual_hash = hashlib.sha256(body).hexdigest().upper()
    if len(body) != consumer["bodyBytes"] or actual_hash != str(consumer["bodySha256"]).upper():
        raise VMOperandEvidenceError(
            f"{label} body:mismatched:0x{rva:x} "
            f"expectedBytes={consumer['bodyBytes']} actualBytes={len(body)} "
            f"expectedSha256={consumer['bodySha256']} actualSha256={actual_hash}"
        )
    return actual_hash


def _require_direct_call(
    body: bytes, body_rva: int, call_rva: int, target_rva: int, *, label: str
) -> None:
    """Verify one x64 near-call witness inside an authenticated method body."""
    offset = call_rva - body_rva
    if offset < 0 or offset + 5 > len(body) or body[offset] != 0xE8:
        raise VMOperandEvidenceError(f"{label}: missing near call at 0x{call_rva:x}")
    relative = int.from_bytes(body[offset + 1:offset + 5], "little", signed=True)
    actual_target = call_rva + 5 + relative
    if actual_target != target_rva:
        raise VMOperandEvidenceError(
            f"{label}: expected target 0x{target_rva:x}, actual 0x{actual_target:x}"
        )


def _require_near_jcc(
    body: bytes, body_rva: int, branch_rva: int, target_rva: int, *, label: str
) -> None:
    """Verify an x64 near conditional branch inside an authenticated body."""
    offset = branch_rva - body_rva
    if (
        offset < 0 or offset + 6 > len(body)
        or body[offset:offset + 2] != b"\x0f\x84"
    ):
        raise VMOperandEvidenceError(f"{label}: missing near je at 0x{branch_rva:x}")
    relative = int.from_bytes(body[offset + 2:offset + 6], "little", signed=True)
    actual_target = branch_rva + 6 + relative
    if actual_target != target_rva:
        raise VMOperandEvidenceError(
            f"{label}: expected target 0x{target_rva:x}, actual 0x{actual_target:x}"
        )


def _validate_code_window_bytes(
    window: dict[str, Any], actual: bytes, *, label: str, rva: int
) -> None:
    expected_count = window["byteCount"]
    if not isinstance(expected_count, int) or not 1 <= expected_count <= 64:
        raise VMOperandEvidenceError(f"{label}: invalid code-window byte count")
    actual_hash = hashlib.sha256(actual).hexdigest().upper()
    if len(actual) != expected_count or actual_hash != str(window["sha256"]).upper():
        raise VMOperandEvidenceError(
            f"{label}:mismatched:0x{rva:x} "
            f"expectedBytes={expected_count} actualBytes={len(actual)} "
            f"expectedSha256={window['sha256']} actualSha256={actual_hash}"
        )


def _selected_method_identity(
    image: Any, owner: Any, spec: dict[str, Any], *, label: str
) -> tuple[Any, int]:
    metadata = image.metadata
    methods = [
        row for row in metadata.methods_for(owner)
        if metadata.string(row.name_index) == spec["method"]
        and row.parameter_count == spec["parameterCount"]
    ]
    if len(methods) != 1:
        raise VMOperandEvidenceError(
            f"{spec['type']}.{spec['method']}: expected one overload, found {len(methods)}"
        )
    method = methods[0]
    if "parameterNames" in spec:
        actual_names = [
            metadata.string(row.name_index) for row in metadata.parameters_for(method)
        ]
        if actual_names != spec["parameterNames"]:
            raise VMOperandEvidenceError(
                f"{label} parameters: expected {spec['parameterNames']}, actual {actual_names}"
            )
    token = f"0x{method.token:08x}"
    if token.lower() != str(spec["token"]).lower():
        raise VMOperandEvidenceError(f"{label} token: expected {spec['token']}, actual {token}")
    pointer = image.method_pointer_va(method)
    rva = pointer - image.pe.image_base
    if rva != _int_hex(spec["rva"], f"{label} rva"):
        raise VMOperandEvidenceError(
            f"{label} rva: expected {spec['rva']}, actual 0x{rva:x}"
        )
    return method, rva


def _selected_method_body(
    image: Any, owner: Any, spec: dict[str, Any], *, label: str,
    extents: dict[int, int] | None = None,
) -> tuple[bytes, int, str]:
    method, rva = _selected_method_identity(image, owner, spec, label=label)
    pointer = image.pe.image_base + rva
    if extents is None:
        extents = image.mapper.pdata_function_extents(image.pe)
    end = extents.get(pointer)
    if end is None or end <= pointer:
        raise VMOperandEvidenceError(f"{label} extent:missing:0x{rva:x}")
    body = image.pe.bytes_at_va(pointer, end - pointer)
    return body, rva, _validate_body_bytes(spec, body, rva, label=label)


def _validate_exception_handler_reader(
    image: Any, spec: dict[str, Any], loader_body: bytes, loader_rva: int
) -> dict[str, Any]:
    """Authenticate six ReadInt32 calls and their ordered handler-field stores."""
    metadata = image.metadata
    if spec.get("recordBytes") != EXCEPTION_RECORD_SIZE or spec.get("evidenceBoundary") != "direct":
        raise VMOperandEvidenceError("exception handler: unsupported record boundary")
    owner_rows = [
        row for row in metadata.types
        if metadata.type_full_name(row) == spec["type"]
    ]
    if len(owner_rows) != 1:
        raise VMOperandEvidenceError(f"exception handler type: expected one, found {len(owner_rows)}")
    offsets = runtime_type_field_offsets(
        metadata, image.pe, image.registration, owner_rows[0].index
    )
    if offsets != spec["fieldOffsets"]:
        raise VMOperandEvidenceError(
            f"exception handler fields: expected {spec['fieldOffsets']}, actual {offsets}"
        )
    members = [
        {"id": int(row["id"]), "name": row["name"]}
        for row in enum_members(metadata, field_defaults(metadata), spec["enumType"])
    ]
    if members != spec["enumMembers"] or len({row["id"] for row in members}) != len(members):
        raise VMOperandEvidenceError(
            f"exception handler enum: expected {spec['enumMembers']}, actual {members}"
        )
    reader = spec["readMethod"]
    reader_owners = [
        row for row in metadata.types
        if metadata.type_full_name(row) == reader["type"]
    ]
    if len(reader_owners) != 1:
        raise VMOperandEvidenceError(
            f"exception reader type: expected one, found {len(reader_owners)}"
        )
    _method, reader_rva = _selected_method_identity(
        image, reader_owners[0], reader, label="exception reader"
    )
    rows = spec["loaderReadOrder"]
    expected_fields = (
        "HandlerType", "CatchTypeId", "TryStart", "TryEnd", "HandlerStart", "HandlerEnd"
    )
    if len(rows) != 6 or tuple(row["field"] for row in rows) != expected_fields:
        raise VMOperandEvidenceError("exception handler: unsupported six-field read order")
    previous_store = loader_rva
    for index, row in enumerate(rows):
        call_rva = _int_hex(row["readCallRva"], f"exception[{index}].readCallRva")
        store_rva = _int_hex(row["fieldStoreRva"], f"exception[{index}].fieldStoreRva")
        if not previous_store < call_rva < store_rva < loader_rva + len(loader_body):
            raise VMOperandEvidenceError(f"exception[{index}]: read/store order outside loader body")
        _require_direct_call(
            loader_body, loader_rva, call_rva, reader_rva,
            label=f"exception[{index}].ReadInt32",
        )
        offset = store_rva - loader_rva
        expected_store = b"\x89\x47" + bytes([offsets[row["field"]]])
        if loader_body[offset:offset + 3] != expected_store:
            raise VMOperandEvidenceError(
                f"exception[{index}].{row['field']}: expected store {expected_store.hex()}, "
                f"actual {loader_body[offset:offset + 3].hex()}"
            )
        previous_store = store_rva
    return {
        "status": "validated_six_signed_int32_fields",
        "recordBytes": EXCEPTION_RECORD_SIZE,
        "readMethod": f"{reader['type']}.{reader['method']}",
        "fieldOrder": list(expected_fields),
        "enumMembers": members,
        "evidenceBoundary": "direct",
    }


def _validate_exception_control(
    spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], arithmetic: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Check the selected Leave target store and Endfinally resume path."""
    leave, endfinally = spec["leave"], spec["endfinally"]
    if (
        spec.get("evidenceBoundary") != "direct"
        or opcode_ids.get(leave["opcode"]) != leave["opcodeId"]
        or opcode_ids.get(endfinally["opcode"]) != endfinally["opcodeId"]
        or leave.get("targetMeaning") != "absoluteInstructionIndex"
        or endfinally.get("minusOneMeaning") != "pendingLeaveTargetWhenNonzero"
    ):
        raise VMOperandEvidenceError("exception control: unsupported opcode or target claim")
    expected_witnesses = {
        "leaveOperandRead": leave["operandReadRva"],
        "leavePendingStore": leave["pendingTargetStoreRva"],
        "endfinallyPendingCheck": endfinally["pendingTargetCheckRva"],
        "endfinallyMinusOneCheck": endfinally["minusOneCheckRva"],
        "endfinallyResumeRead": endfinally["resumeIndexReadRva"],
        "endfinallyScale": endfinally["scaleImmediateRva"],
        "endfinallyCodeBase": endfinally["codeBaseReadRva"],
        "endfinallyPendingClear": endfinally["pendingTargetClearRva"],
    }
    rows = spec["byteWitnesses"]
    witnesses = {row["name"]: row for row in rows}
    if len(witnesses) != len(rows) or set(witnesses) != set(expected_witnesses):
        raise VMOperandEvidenceError("exception control: missing or duplicate byte witness")
    for name, expected_rva in expected_witnesses.items():
        row = witnesses[name]
        if _int_hex(row["rva"], f"{name}.rva") != _int_hex(expected_rva, f"{name}.claimRva"):
            raise VMOperandEvidenceError(f"{name}: witness RVA disagrees with claim")
        rva = _int_hex(row["rva"], f"{name}.rva")
        expected = bytes.fromhex(row["hex"])
        offset = rva - body_rva
        if not expected or not 0 <= offset <= len(body) - len(expected):
            raise VMOperandEvidenceError(f"{name}: outside authenticated Execute body")
        actual = body[offset:offset + len(expected)]
        if actual != expected:
            raise VMOperandEvidenceError(
                f"{name}: expectedBytes={expected.hex()} actualBytes={actual.hex()}"
            )
    for label, branch_rva, target_rva in (
        ("Leave.dispatch", leave["dispatchBranchRva"], leave["dispatchEntryRva"]),
        ("Endfinally.minusOne", endfinally["minusOneBranchRva"], endfinally["resumeIndexReadRva"]),
        ("Endfinally.pendingZero", endfinally["pendingZeroBranchRva"], endfinally["pendingZeroPathRva"]),
    ):
        _require_near_jcc(
            body, body_rva, _int_hex(branch_rva, f"{label}.branchRva"),
            _int_hex(target_rva, f"{label}.targetRva"), label=label,
        )
    for call_key, window_name in (
        ("slotMultiplyCallRva", "signedSlotMultiply"),
        ("pointerAddCallRva", "pointerAdd"),
    ):
        _require_direct_call(
            body, body_rva, _int_hex(endfinally[call_key], f"Endfinally.{call_key}"),
            _int_hex(arithmetic[window_name]["rva"], f"{window_name}.rva"),
            label=f"Endfinally.{call_key}",
        )
    return {
        "status": "validated_conditional_pending_leave_resume",
        "leaveTargetMeaning": leave["targetMeaning"],
        "endfinallyMinusOneMeaning": endfinally["minusOneMeaning"],
        "evidenceBoundary": "direct",
        "executionBoundary": "unobserved",
    }


def _validate_newobj_selector(
    image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], arithmetic: dict[str, dict[str, Any]],
    call_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prove the delegate-constructor split before reading Newobj's upper half."""
    if (
        spec.get("evidenceBoundary") != "conditional"
        or spec.get("opcode") != "Newobj"
        or opcode_ids.get("Newobj") != spec.get("opcodeId")
    ):
        raise VMOperandEvidenceError("Newobj selector: unsupported opcode claim")
    newobj = [row for row in call_claims if row["opcode"] == "Newobj"]
    extern = [row for row in call_claims if row["opcode"] == "CallExtern"]
    if (
        len(newobj) != 1 or len(extern) != 1
        or newobj[0].get("upper16Meaning") != "conditionalExternStackRewind"
        or newobj[0]["low16TargetTable"] != "externMethods"
        or extern[0].get("upper16Meaning") != "externStackRewind"
    ):
        raise VMOperandEvidenceError("Newobj selector: incompatible call-table claim")
    metadata = image.metadata
    helper = spec["virtualInvokeHelper"]
    helper_rva = _int_hex(helper["rva"], "Newobj virtual helper rva")
    window_rva = _int_hex(helper["windowRva"], "Newobj virtual helper window")
    _validate_code_window_bytes(
        helper, image.pe.bytes_at_va(image.pe.image_base + window_rva, helper["byteCount"]),
        label="Newobj virtual slot helper", rva=window_rva,
    )
    for label in ("declaringTypeGetter", "baseTypeGetter"):
        row = spec[label]
        owners = [
            owner for owner in metadata.types
            if metadata.type_full_name(owner) == row["type"]
        ]
        if len(owners) != 1:
            raise VMOperandEvidenceError(f"Newobj {label}: expected one owner, found {len(owners)}")
        methods = [
            method for method in metadata.methods_for(owners[0])
            if metadata.string(method.name_index) == row["method"]
            and method.parameter_count == row["parameterCount"]
        ]
        if (
            len(methods) != 1
            or f"0x{methods[0].token:08x}".lower() != str(row["token"]).lower()
            or methods[0].slot != row["virtualSlot"]
        ):
            raise VMOperandEvidenceError(f"Newobj {label}: virtual token or slot differs")
        literal_rva = _int_hex(row["slotLiteralRva"], f"Newobj {label} slot literal")
        offset = literal_rva - body_rva
        expected = b"\xb9" + int(row["virtualSlot"]).to_bytes(4, "little")
        if not 0 <= offset <= len(body) - 5 or body[offset:offset + 5] != expected:
            raise VMOperandEvidenceError(f"Newobj {label}: virtual slot literal differs")
        _require_direct_call(
            body, body_rva, _int_hex(row["invokeCallRva"], f"Newobj {label} call"),
            helper_rva, label=f"Newobj {label} virtual invoke",
        )
    static_type = spec["delegateBaseType"]
    load_rva = _int_hex(static_type["loadRva"], "Newobj delegate type load")
    offset = load_rva - body_rva
    if not 0 <= offset <= len(body) - 7 or body[offset:offset + 3] != b"\x48\x8b\x1d":
        raise VMOperandEvidenceError("Newobj delegate type: missing mov rbx,[rip+disp]")
    cell_rva = load_rva + 7 + int.from_bytes(body[offset + 3:offset + 7], "little", signed=True)
    if cell_rva != _int_hex(static_type["cellRva"], "Newobj delegate type cell"):
        raise VMOperandEvidenceError(
            f"Newobj delegate type cell: expected {static_type['cellRva']}, actual 0x{cell_rva:x}"
        )
    raw = image.pe.bytes_at_va(image.pe.image_base + cell_rva, 8)
    word = int.from_bytes(raw, "little")
    if word != _int_hex(static_type["encodedWord"], "Newobj delegate type word"):
        raise VMOperandEvidenceError("Newobj delegate type: encoded usage word differs")
    type_index = unresolved_usage_index(
        raw, image.registration["typesCount"], tag=static_type["usageTag"],
        source="Newobj delegate type", offset=cell_rva,
    )
    if type_index != static_type["registeredTypeIndex"]:
        raise VMOperandEvidenceError("Newobj delegate type: registered index differs")
    type_pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + type_index * 8)
    actual_type_name = runtime_type_name(image.pe, metadata, type_pointer)
    if actual_type_name != static_type["typeName"]:
        raise VMOperandEvidenceError(
            f"Newobj delegate type: expected {static_type['typeName']}, actual {actual_type_name}"
        )
    from_handle = spec["typeFromHandle"]
    owners = [
        owner for owner in metadata.types
        if metadata.type_full_name(owner) == from_handle["type"]
    ]
    if len(owners) != 1:
        raise VMOperandEvidenceError("Newobj GetTypeFromHandle: expected one owner")
    _method, from_handle_rva = _selected_method_identity(
        image, owners[0], from_handle, label="Newobj GetTypeFromHandle"
    )
    _require_direct_call(
        body, body_rva, _int_hex(from_handle["callRva"], "Newobj GetTypeFromHandle call"),
        from_handle_rva, label="Newobj GetTypeFromHandle",
    )
    equality = spec["pointerEquality"]
    equality_rva = _int_hex(equality["rva"], "Newobj pointer equality rva")
    _validate_code_window_bytes(
        equality, image.pe.bytes_at_va(image.pe.image_base + equality_rva, equality["byteCount"]),
        label="Newobj pointer equality", rva=equality_rva,
    )
    _require_direct_call(
        body, body_rva, _int_hex(equality["callRva"], "Newobj pointer equality call"),
        equality_rva, label="Newobj pointer equality",
    )
    for label, row in (
        ("Newobj zero register", spec["zeroRegister"]),
        ("Newobj equality zero compare", {"rva": equality["zeroCompareRva"], "hex": equality["zeroCompareHex"]}),
        ("Newobj instruction restore", {"rva": spec["rewindPath"]["instructionRestoreRva"], "hex": spec["rewindPath"]["instructionRestoreHex"]}),
        ("Newobj upper read", {"rva": spec["rewindPath"]["signedUpper16ReadRva"], "hex": spec["rewindPath"]["signedUpper16ReadHex"]}),
        ("Newobj upper shift", {"rva": spec["rewindPath"]["signedShiftRva"], "hex": spec["rewindPath"]["signedShiftHex"]}),
    ):
        rva = _int_hex(row["rva"], f"{label} rva")
        expected = bytes.fromhex(row["hex"])
        offset = rva - body_rva
        if not expected or not 0 <= offset <= len(body) - len(expected) or body[offset:offset + len(expected)] != expected:
            raise VMOperandEvidenceError(f"{label}: expected instruction bytes {expected.hex()}")
    _require_near_jcc(
        body, body_rva,
        _int_hex(equality["nonDelegateBranchRva"], "Newobj nondelegate branch"),
        _int_hex(equality["nonDelegateTargetRva"], "Newobj nondelegate target"),
        label="Newobj nondelegate path",
    )
    rewind = spec["rewindPath"]
    if (
        rewind["signedShiftRva"] != extern[0]["upper16SignedReadRva"]
        or rewind["slotMultiplyCallRva"] != extern[0]["slotMultiplyCallRva"]
        or rewind["pointerSubtractCallRva"] != extern[0]["pointerSubtractCallRva"]
        or rewind["argumentBaseWriteRva"] != extern[0]["argumentBaseWriteRva"]
    ):
        raise VMOperandEvidenceError("Newobj rewind: does not share reviewed CallExtern path")
    for key, name in (
        ("slotMultiplyCallRva", "signedSlotMultiply"),
        ("pointerSubtractCallRva", "stackPointerSubtract"),
    ):
        _require_direct_call(
            body, body_rva, _int_hex(rewind[key], f"Newobj {key}"),
            _int_hex(arithmetic[name]["rva"], f"{name} rva"), label=f"Newobj {key}",
        )
    return {
        "status": "validated_conditional_non_delegate_constructor_rewind",
        "delegateBaseType": actual_type_name,
        "nonDelegatePath": "signed-upper16-evaluation-stack-rewind",
        "delegatePath": "separate-construction-path",
        "evidenceBoundary": "conditional",
        "executionBoundary": "unobserved",
    }


def _rip_relative_qword_cell_rva(body: bytes, body_rva: int, load_rva: int) -> int:
    offset = load_rva - body_rva
    if offset < 0 or offset + 7 > len(body) or body[offset:offset + 3] != b"\x4c\x8b\x05":
        raise VMOperandEvidenceError(f"metadata-usage load: missing mov r8,[rip+disp] at 0x{load_rva:x}")
    displacement = int.from_bytes(body[offset + 3:offset + 7], "little", signed=True)
    return load_rva + 7 + displacement


def _methoddef_usage_index(word: int) -> int:
    if not 0 <= word <= 0xFFFFFFFF or word >> 29 != 3 or not word & 1:
        raise VMOperandEvidenceError(f"metadata-usage word: expected MethodDef encoding, actual 0x{word:x}")
    return (word >> 1) & 0x0FFFFFFF


def _validate_reflection_dispatch(
    image: Any, spec: dict[str, Any], consumer_body: bytes, consumer_rva: int,
    extents: dict[int, int],
) -> dict[str, Any]:
    """Prove the CallExtern delegate target and its conditional result path."""
    if spec.get("evidenceBoundary") != "conditional":
        raise VMOperandEvidenceError("reflection dispatch: expected conditional boundary")
    metadata = image.metadata
    selected: dict[str, tuple[bytes, int, str]] = {}
    owners: dict[str, Any] = {}
    method_specs = spec["methods"]
    for label, method_spec in method_specs.items():
        type_name = method_spec["type"]
        matches = [row for row in metadata.types if metadata.type_full_name(row) == type_name]
        if len(matches) != 1:
            raise VMOperandEvidenceError(f"reflection {type_name}: expected one type, found {len(matches)}")
        owners[type_name] = matches[0]
        if method_spec.get("bodyExtent") == "sharedDelegateTrampoline":
            _method, method_rva = _selected_method_identity(
                image, matches[0], method_spec, label=label
            )
            selected[label] = (b"", method_rva, "sharedDelegateTrampoline")
        else:
            selected[label] = _selected_method_body(
                image, matches[0], method_spec, label=label, extents=extents
            )
    for type_name, field_offsets in spec["fieldOffsets"].items():
        owner = owners.get(type_name)
        if owner is None:
            raise VMOperandEvidenceError(f"reflection field owner missing: {type_name}")
        actual_offsets = runtime_type_field_offsets(
            metadata, image.pe, image.registration, owner.index
        )
        for field, expected in field_offsets.items():
            if actual_offsets.get(field) != expected:
                raise VMOperandEvidenceError(
                    f"reflection field {type_name}.{field}: expected {expected}, "
                    f"actual {actual_offsets.get(field)}"
                )
    execute_witnesses = spec["executeWitnesses"]
    for key, value in execute_witnesses.items():
        if key.endswith("Rva"):
            witness = _int_hex(value, f"reflection.{key}")
            if not consumer_rva <= witness < consumer_rva + len(consumer_body):
                raise VMOperandEvidenceError(f"reflection.{key}: outside authenticated Execute body")
    for label, group in spec["methodWitnesses"].items():
        body, body_rva, _body_hash = selected[label]
        for key, value in group.items():
            witness = _int_hex(value, f"{label}.{key}")
            if not body_rva <= witness < body_rva + len(body):
                raise VMOperandEvidenceError(f"{label}.{key}: outside authenticated method body")
    direct_calls = (
        ("reflectionConstructorCallRva", "reflectionConstructor"),
        ("delegateConstructorCallRva", "delegateConstructor"),
        ("delegateInvokeCallRva", "delegateInvoke"),
    )
    for call_key, target_label in direct_calls:
        _require_direct_call(
            consumer_body, consumer_rva,
            _int_hex(execute_witnesses[call_key], f"reflection.{call_key}"),
            selected[target_label][1], label=f"reflection.{call_key}"
        )
    for caller_label, call_key, target_label in (
        ("reflectionInvoke", "isStaticCallRva", "isStatic"),
        ("reflectionInvoke", "isConstructorCallRva", "isConstructor"),
        ("reflectionInvoke", "pushResultCallRva", "pushResult"),
        ("pushResult", "evaluationPushCallRva", "evaluationPush"),
    ):
        body, body_rva, _body_hash = selected[caller_label]
        _require_direct_call(
            body, body_rva,
            _int_hex(spec["methodWitnesses"][caller_label][call_key], f"{caller_label}.{call_key}"),
            selected[target_label][1], label=f"{caller_label}.{call_key}"
        )
    usage = spec["metadataUsage"]
    load_rva = _int_hex(usage["loadRva"], "reflection metadata-usage load")
    cell_rva = _rip_relative_qword_cell_rva(consumer_body, consumer_rva, load_rva)
    if cell_rva != _int_hex(usage["cellRva"], "reflection metadata-usage cell"):
        raise VMOperandEvidenceError(
            f"reflection metadata-usage cell: expected {usage['cellRva']}, actual 0x{cell_rva:x}"
        )
    word = image.pe.u64_at_va(image.pe.image_base + cell_rva)
    if word != _int_hex(usage["encodedWord"], "reflection metadata-usage word"):
        raise VMOperandEvidenceError(
            f"reflection metadata-usage word: expected {usage['encodedWord']}, actual 0x{word:x}"
        )
    method_index = _methoddef_usage_index(word)
    invoker_owner = owners[method_specs["reflectionInvoke"]["type"]]
    invoker_methods = [
        row for row in metadata.methods_for(invoker_owner)
        if metadata.string(row.name_index) == method_specs["reflectionInvoke"]["method"]
        and row.parameter_count == method_specs["reflectionInvoke"]["parameterCount"]
    ]
    if len(invoker_methods) != 1 or method_index != invoker_methods[0].index:
        raise VMOperandEvidenceError(
            f"reflection metadata-usage target: expected Invoke method index "
            f"{invoker_methods[0].index if invoker_methods else None}, actual {method_index}"
        )
    return {
        "status": "validated_conditional_reflected_result_path",
        "delegateTarget": "IFix.Core.ReflectionMethodInvoker.Invoke",
        "metadataUsageCellRva": f"0x{cell_rva:x}",
        "methodDefIndex": method_index,
        "methodBodySha256": {
            label: row[2] for label, row in selected.items()
            if row[2] != "sharedDelegateTrampoline"
        },
        "executionBoundary": "unobserved",
    }


def validate_vm_operand_contract(
    contract_path: Path, *, gameassembly: Path, metadata_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Authenticate reviewed loader/consumer bodies and table identities."""
    raw = Path(contract_path).read_bytes()
    contract = json.loads(raw)
    if not isinstance(contract, dict) or contract.get("schema") != SCHEMA:
        raise VMOperandEvidenceError(f"{contract_path}: unsupported contract schema")
    if contract.get("status") != "validated" or contract.get("evidenceBoundary") != "direct":
        raise VMOperandEvidenceError(f"{contract_path}: contract is not reviewed direct evidence")
    native_inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        native_inputs["gameAssemblySha256"],
        native_inputs["globalMetadataSha256"],
        gameassembly=Path(gameassembly),
        metadata=Path(metadata_path),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise VMOperandEvidenceError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unityplayer = Path(gameassembly).with_name("UnityPlayer.dll")
    if not unityplayer.is_file():
        raise VMOperandEvidenceError(f"UnityPlayer.dll:missing:{unityplayer}")
    unity_hash = _sha256_file(unityplayer)
    if unity_hash != str(native_inputs["unityPlayerSha256"]).upper():
        raise VMOperandEvidenceError(
            f"UnityPlayer.dll:mismatched:{unityplayer} "
            f"expectedSha256={native_inputs['unityPlayerSha256']} actualSha256={unity_hash}"
        )

    image = open_native_image(Path(gameassembly), Path(metadata_path))
    metadata = image.metadata
    extents = image.mapper.pdata_function_extents(image.pe)
    selected: dict[str, tuple[bytes, int, str]] = {}
    owners: dict[str, Any] = {}
    for label in ("consumer", "loader"):
        spec = contract[label]
        matches = [row for row in metadata.types if metadata.type_full_name(row) == spec["type"]]
        if len(matches) != 1:
            raise VMOperandEvidenceError(f"{spec['type']}: expected one type, found {len(matches)}")
        owners[label] = matches[0]
        selected[label] = _selected_method_body(
            image, matches[0], spec, label=label, extents=extents
        )
    body, rva, consumer_hash = selected["consumer"]
    loader_body, loader_rva, loader_hash = selected["loader"]
    exception_audit = _validate_exception_handler_reader(
        image, contract["exceptionHandler"], loader_body, loader_rva
    )
    reflection_audit = _validate_reflection_dispatch(
        image, contract["reflectionDispatch"], body, rva, extents
    )
    offsets = runtime_type_field_offsets(
        metadata, image.pe, image.registration, owners["consumer"].index
    )
    for field, expected in contract["fieldOffsets"].items():
        if offsets.get(field) != expected:
            raise VMOperandEvidenceError(
                f"consumer field {field}: expected {expected}, actual {offsets.get(field)}"
            )
    arithmetic_rows = contract["arithmeticWindows"]
    if not isinstance(arithmetic_rows, list) or any(
        not isinstance(row, dict) or "name" not in row for row in arithmetic_rows
    ):
        raise VMOperandEvidenceError("arithmetic helper windows: expected named rows")
    arithmetic = {row["name"]: row for row in arithmetic_rows}
    if len(arithmetic) != len(arithmetic_rows) or set(arithmetic) != {
        "signedSlotMultiply", "stackPointerSubtract", "pointerAdd"
    }:
        raise VMOperandEvidenceError("arithmetic helper windows missing or duplicated")
    for name, window in arithmetic.items():
        window_rva = _int_hex(window["rva"], f"{name}.rva")
        byte_count = window["byteCount"]
        if not isinstance(byte_count, int) or not 1 <= byte_count <= 64:
            raise VMOperandEvidenceError(f"{name}: invalid code-window byte count")
        actual = image.pe.bytes_at_va(image.pe.image_base + window_rva, byte_count)
        _validate_code_window_bytes(window, actual, label=name, rva=window_rva)

    layout = selected_opcode_layout(Path(gameassembly), Path(metadata_path))
    opcode_ids = {row["name"]: row["id"] for row in layout["opcodeEnum"]["members"]}
    exception_control_audit = _validate_exception_control(
        contract["exceptionControl"], body, rva, opcode_ids, arithmetic
    )
    newobj_audit = _validate_newobj_selector(
        image, contract["newobjSelector"], body, rva, opcode_ids,
        arithmetic, contract["callClaims"],
    )
    call_claims = contract["callClaims"]
    branch_claims = contract["branchClaims"]
    table_claims = contract["tableOperandClaims"]
    frame_claims = contract["frameSlotClaims"]
    header = contract["entryHeader"]
    return_claim = contract["returnClaim"]
    loader_tables = contract["loader"]["loadedTables"]
    table_map = {row["runtimeField"]: row["fileTable"] for row in loader_tables}
    if len(table_map) != len(loader_tables) or not table_map:
        raise VMOperandEvidenceError("loader table mapping is empty or duplicated")
    for row in loader_tables:
        if row["runtimeField"] not in contract["fieldOffsets"]:
            raise VMOperandEvidenceError(f"loader field not validated: {row['runtimeField']}")
        for key, value in row.items():
            if key.endswith("Rva"):
                witness = _int_hex(value, f"loader.{row['runtimeField']}.{key}")
                if not loader_rva <= witness < loader_rva + len(loader_body):
                    raise VMOperandEvidenceError(
                        f"loader.{row['runtimeField']}.{key}: outside authenticated body"
                    )
    for kind, group in (
        ("call", call_claims), ("branch", branch_claims),
        ("table", table_claims), ("frame", frame_claims)
    ):
        if not isinstance(group, list) or not group:
            raise VMOperandEvidenceError(f"{kind} operand contract has no claims")
    seen: set[str] = set()
    for kind, group in (
        ("call", call_claims), ("branch", branch_claims),
        ("table", table_claims), ("frame", frame_claims)
    ):
        for claim in group:
            name = str(claim["opcode"])
            if name in seen or opcode_ids.get(name) != claim["opcodeId"]:
                raise VMOperandEvidenceError(f"opcode claim mismatch or duplicate: {name}")
            seen.add(name)
            if kind == "call":
                for table in (claim["low16TargetTable"], claim.get("cacheTable")):
                    if table is not None and table not in contract["fieldOffsets"]:
                        raise VMOperandEvidenceError(f"{name}: unvalidated runtime table {table}")
                if claim["low16TargetTable"] not in table_map:
                    raise VMOperandEvidenceError(f"{name}: no reviewed loader order")
                meaning = claim.get("upper16Meaning")
                if meaning == "recursiveArgsCount":
                    if (
                        claim["low16TargetTable"] != "unmanagedCodes"
                        or contract["consumer"]["parameterNames"][4] != "argsCount"
                        or any(key not in claim for key in (
                            "upper16SignedReadRva", "argsCountForwardRva", "recursiveCallRva"
                        ))
                    ):
                        raise VMOperandEvidenceError(f"{name}: unsupported recursive call claim")
                    _require_direct_call(
                        body, rva, _int_hex(claim["recursiveCallRva"], f"{name}.recursiveCallRva"),
                        rva, label=f"{name}.recursiveCall"
                    )
                elif meaning == "externStackRewind":
                    if (
                        name != "CallExtern" or claim["low16TargetTable"] != "externMethods"
                        or any(key not in claim for key in (
                            "upper16SignedReadRva", "slotMultiplyCallRva",
                            "pointerSubtractCallRva", "argumentBaseWriteRva", "invokerCallRva"
                        ))
                    ):
                        raise VMOperandEvidenceError(f"{name}: unsupported external call claim")
                    for call_key, window_name in (
                        ("slotMultiplyCallRva", "signedSlotMultiply"),
                        ("pointerSubtractCallRva", "stackPointerSubtract"),
                    ):
                        _require_direct_call(
                            body, rva, _int_hex(claim[call_key], f"{name}.{call_key}"),
                            _int_hex(arithmetic[window_name]["rva"], f"{window_name}.rva"),
                            label=f"{name}.{call_key}"
                        )
                elif meaning == "conditionalExternStackRewind":
                    if name != "Newobj" or claim["low16TargetTable"] != "externMethods":
                        raise VMOperandEvidenceError(f"{name}: unsupported conditional rewind claim")
                elif meaning is not None:
                    raise VMOperandEvidenceError(f"{name}: unsupported upper16 claim")
            elif kind == "branch":
                if claim["branchKind"] not in ("unconditional", "conditional"):
                    raise VMOperandEvidenceError(f"{name}: unsupported branch kind")
            elif (
                kind == "table" and (
                    claim["targetRuntimeField"] not in table_map
                    or claim["selectedWhen"] not in ("allOperands", "nonnegativeOperand")
                )
            ):
                raise VMOperandEvidenceError(f"{name}: unsupported table selection")
            elif kind == "frame" and claim["slotDomain"] not in (
                "local", "localAddress", "argument"
            ):
                raise VMOperandEvidenceError(f"{name}: unsupported frame slot domain")
            for key, value in claim.items():
                if key.endswith("Rva"):
                    witness = _int_hex(value, f"{name}.{key}")
                    if not rva <= witness < rva + len(body):
                        raise VMOperandEvidenceError(f"{name}.{key}: outside authenticated body")
    for label, claim in (("entryHeader", header), ("returnClaim", return_claim)):
        name = str(claim["opcode"])
        if name in seen or opcode_ids.get(name) != claim["opcodeId"]:
            raise VMOperandEvidenceError(f"{label}: opcode claim mismatch or duplicate: {name}")
        seen.add(name)
        for key, value in claim.items():
            if key.endswith("Rva"):
                witness = _int_hex(value, f"{label}.{key}")
                if not rva <= witness < rva + len(body):
                    raise VMOperandEvidenceError(f"{label}.{key}: outside authenticated body")
    if (
        header["slotBytes"] != 12
        or header["localCountHalf"] != "signedUpper16"
        or header["evaluationReserveHalf"] != "unsignedLower16"
        or return_claim["valueWhen"] != "nonzeroOperand"
    ):
        raise VMOperandEvidenceError("entry/return operand rule unsupported by this projector")
    audit = {
        "contractFile": str(contract_path),
        "contractSha256": hashlib.sha256(raw).hexdigest().upper(),
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "globalMetadataSha256": gate.metadata_sha256.upper(),
            "unityPlayerSha256": unity_hash,
        },
        "consumerBodySha256": consumer_hash,
        "loaderBodySha256": loader_hash,
        "exceptionHandler": exception_audit,
        "exceptionControl": exception_control_audit,
        "newobjSelector": newobj_audit,
        "reflectionDispatch": reflection_audit,
        "evidenceBoundary": "direct",
        "executionBoundary": "unresolved",
    }
    return contract, layout, audit


def _project_exception_handlers(
    data: bytes, parsed: dict[str, Any], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    """Read ordered numeric records only after the native contract is selected."""
    names = {
        row["id"]: row["name"]
        for row in contract["exceptionHandler"]["enumMembers"]
    }
    handlers = []
    for method in parsed["methods"]["records"]:
        size = method["codeSize"]
        for index in range(method["exceptionCount"]):
            offset = method["exceptionOffset"] + index * EXCEPTION_RECORD_SIZE
            handler_type, catch_type_id, try_start, try_end, handler_start, handler_end = (
                struct.unpack_from("<6i", data, offset)
            )
            bounded = (
                0 <= try_start <= try_end <= size
                and 0 <= handler_start <= handler_end <= size
            )
            handlers.append({
                "vmMethodIndex": method["index"],
                "recordIndex": index,
                "offset": offset,
                "handlerTypeId": handler_type,
                "handlerType": names.get(handler_type),
                "handlerTypeJoin": "direct" if handler_type in names else "unknown-enum-value",
                "catchTypeId": catch_type_id,
                "tryStartInstructionIndex": try_start,
                "tryEndInstructionIndex": try_end,
                "handlerStartInstructionIndex": handler_start,
                "handlerEndInstructionIndex": handler_end,
                "instructionBoundaryStatus": "within-method" if bounded else "out-of-range",
                "methodInstructionCount": size,
                "executionBoundary": "unobserved",
            })
    return handlers


def project_vm_operands(
    data: bytes, layout: dict[str, Any], contract: dict[str, Any], *, source: str
) -> dict[str, Any]:
    """Join reviewed VM table rows and current-relative branch targets."""
    parsed = parse_ifix_patch(data, source=source)
    decoded = decode_patch_opcodes(data, layout, source=source)
    exception_handlers = _project_exception_handlers(data, parsed, contract)
    call_claims = {row["opcode"]: row for row in contract["callClaims"]}
    branch_claims = {row["opcode"]: row for row in contract["branchClaims"]}
    table_claims = {row["opcode"]: row for row in contract["tableOperandClaims"]}
    frame_claims = {row["opcode"]: row for row in contract["frameSlotClaims"]}
    header_claim = contract["entryHeader"]
    return_claim = contract["returnClaim"]
    exception_control = contract["exceptionControl"]
    table_map = {
        row["runtimeField"]: row["fileTable"]
        for row in contract["loader"]["loadedTables"]
    }
    calls = []
    branches = []
    table_operands = []
    frame_headers = []
    frame_slots = []
    returns = []
    leaves = []
    endfinallys = []
    for method in decoded["methods"]:
        method_size = len(method["instructions"])
        method_code_offset = parsed["methods"]["records"][method["index"]]["codeOffset"]
        first = method["instructions"][0] if method_size else None
        has_header = first is not None and first["name"] == header_claim["opcode"]
        local_count = (
            (first["operandUnsigned"] >> 16) & 0xFFFF if has_header else None
        )
        if local_count is not None and local_count >= 0x8000:
            local_count -= 0x10000
        header_status = (
            "direct" if has_header and local_count is not None and local_count >= 0
            else "unresolved"
        )
        frame_headers.append({
            "vmMethodIndex": method["index"],
            "headerStatus": header_status,
            "firstOpcode": first["name"] if first else None,
            "localSlotCount": local_count,
            "evaluationStackReserve": first["operandUnsigned"] & 0xFFFF if has_header else None,
            "slotBytes": header_claim["slotBytes"] if has_header else None,
            "executionBoundary": "unobserved",
        })
        for instruction in method["instructions"]:
            frame_claim = frame_claims.get(instruction["name"])
            if frame_claim is not None:
                slot_index = instruction["operandSigned"]
                domain = frame_claim["slotDomain"]
                if domain == "argument":
                    range_status = "runtime-argsCount-unobserved"
                elif header_status != "direct":
                    range_status = "unresolved"
                else:
                    range_status = (
                        "direct" if 0 <= slot_index < local_count else "out-of-range"
                    )
                frame_slots.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "opcode": instruction["name"],
                    "slotDomain": domain,
                    "slotIndex": slot_index,
                    "slotRangeStatus": range_status,
                    "localSlotCount": local_count if domain != "argument" else None,
                    "executionBoundary": "unobserved",
                })
            if instruction["name"] == return_claim["opcode"]:
                returns.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "operandSigned": instruction["operandSigned"],
                    "valueSource": (
                        "evaluation-stack-top" if instruction["operandSigned"] != 0
                        else "none"
                    ),
                    "executionBoundary": "unobserved",
                })
            if instruction["name"] == exception_control["leave"]["opcode"]:
                target_index = instruction["operandSigned"]
                in_range = 0 < target_index < method_size
                leaves.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "operandSigned": target_index,
                    "pendingTargetIndex": target_index,
                    "targetFileOffset": (
                        method_code_offset + target_index * 8 if in_range else None
                    ),
                    "targetJoin": (
                        "direct" if in_range else
                        "zero-sentinel" if target_index == 0 else "out-of-range"
                    ),
                    "executionBoundary": "unobserved",
                })
            if instruction["name"] == exception_control["endfinally"]["opcode"]:
                endfinallys.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "operandSigned": instruction["operandSigned"],
                    "minusOneResumeSource": (
                        "pending-leave-target-when-nonzero"
                        if instruction["operandSigned"] == -1 else None
                    ),
                    "executionBoundary": "unobserved",
                })
            branch_claim = branch_claims.get(instruction["name"])
            if branch_claim is not None:
                target_index = instruction["index"] + instruction["operandSigned"]
                target_in_range = 0 <= target_index < method_size
                fallthrough_index = (
                    instruction["index"] + 1
                    if branch_claim["branchKind"] == "conditional" else None
                )
                fallthrough_in_range = (
                    fallthrough_index is not None and fallthrough_index < method_size
                )
                fallthrough_join = (
                    None if fallthrough_index is None
                    else "direct" if fallthrough_in_range else "out-of-range"
                )
                branches.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "opcode": instruction["name"],
                    "branchKind": branch_claim["branchKind"],
                    "signedRelativeInstructionOffset": instruction["operandSigned"],
                    "targetIndex": target_index,
                    "targetFileOffset": (
                        method_code_offset + target_index * 8 if target_in_range else None
                    ),
                    "targetJoin": "direct" if target_in_range else "out-of-range",
                    "fallthroughIndex": fallthrough_index,
                    "fallthroughJoin": fallthrough_join,
                    "fallthroughFileOffset": (
                        method_code_offset + fallthrough_index * 8
                        if fallthrough_in_range else None
                    ),
                    "executionBoundary": "unobserved",
                })
            table_claim = table_claims.get(instruction["name"])
            if table_claim is not None:
                signed = instruction["operandSigned"]
                selected = (
                    table_claim["selectedWhen"] == "allOperands" or signed >= 0
                )
                runtime_table = table_claim["targetRuntimeField"]
                file_table = table_map[runtime_table]
                if file_table not in ("internStrings", "fieldInfos"):
                    raise VMOperandEvidenceError(
                        f"{instruction['name']}: unsupported file table {file_table}"
                    )
                file_rows = parsed[file_table]["records"]
                in_range = selected and 0 <= signed < len(file_rows)
                file_row = file_rows[signed] if in_range else None
                file_join = (
                    "unresolved" if not selected else "direct" if in_range else "out-of-range"
                )
                if file_row is None:
                    declared_row = None
                elif file_table == "internStrings":
                    declared_row = {
                        "index": signed,
                        "kind": "intern-string",
                        "recordOffset": file_row["offset"],
                        "value": file_row["value"],
                    }
                else:
                    declared_row = {
                        "index": signed,
                        "kind": "field-declaration",
                        "recordOffset": file_row["offset"],
                        "declaringType": parsed["externTypes"]["records"][
                            file_row["declaringTypeIndex"]
                        ]["value"],
                        "fieldName": file_row["name"]["value"],
                        "isNewField": file_row["isNewField"],
                    }
                table_operands.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "opcode": instruction["name"],
                    "operandSigned": signed,
                    "runtimeTable": runtime_table,
                    "fileTable": file_table,
                    "fileTableCount": len(file_rows),
                    "fileTableJoin": file_join,
                    "joinReason": None if selected else "negative operand uses another native path",
                    "declaredFileRow": declared_row,
                    "executionBoundary": "unobserved",
                })
            claim = call_claims.get(instruction["name"])
            if claim is None:
                continue
            operand = instruction["operandUnsigned"]
            upper_signed = (operand >> 16) - (0x10000 if operand & 0x80000000 else 0)
            table = claim["low16TargetTable"]
            low_index = operand & 0xFFFF
            file_table = table_map[table]
            file_rows = parsed[file_table]["records"]
            file_count = len(file_rows)
            in_range = low_index < file_count
            file_row = file_rows[low_index] if in_range else None
            if file_row is None:
                declared_row = None
            elif file_table == "methods":
                declared_row = {
                    "index": low_index,
                    "kind": "vm-method-body",
                    "recordOffset": file_row["recordOffset"],
                    "codeSize": file_row["codeSize"],
                }
            else:
                declaring_index = file_row["declaringTypeIndex"]
                parameter_rows = [
                    {**parameter, "typeName": parsed["externTypes"]["records"][parameter["typeIndex"]]["value"]}
                    if parameter["kind"] == "extern-type-index" else parameter
                    for parameter in ordered_signature_parameters(file_row)
                ]
                declared_row = {
                    "index": low_index,
                    "kind": "extern-method-signature",
                    "recordOffset": file_row["offset"],
                    "declaringType": parsed["externTypes"]["records"][declaring_index]["value"],
                    "methodName": file_row["name"]["value"],
                    "isGeneric": file_row["isGeneric"],
                    "genericArgumentTypes": [
                        parsed["externTypes"]["records"][index]["value"]
                        for index in file_row["genericTypeIndices"]
                    ],
                    "parameterTypeIndices": file_row["parameterTypeIndices"],
                    "parameters": parameter_rows,
                    "parameterTypes": [
                        parameter.get("typeName", parameter.get("name"))
                        for parameter in parameter_rows
                    ],
                }
            calls.append({
                "vmMethodIndex": method["index"],
                "instructionIndex": instruction["index"],
                "offset": instruction["offset"],
                "opcode": instruction["name"],
                "operandUnsigned": operand,
                "low16RuntimeTable": table,
                "cacheTable": claim.get("cacheTable"),
                "low16Index": low_index,
                "upper16Raw": operand >> 16,
                "argsCountPassed": (
                    upper_signed
                    if claim.get("upper16Meaning") == "recursiveArgsCount" else None
                ),
                "evaluationStackRewindSlots": (
                    upper_signed
                    if claim.get("upper16Meaning") == "externStackRewind" else None
                ),
                "conditionalConstructorStackRewindSlots": (
                    upper_signed
                    if claim.get("upper16Meaning") == "conditionalExternStackRewind" else None
                ),
                "constructorPathCondition": (
                    "resolved-declaring-type-base-is-not-System.MulticastDelegate"
                    if claim.get("upper16Meaning") == "conditionalExternStackRewind" else None
                ),
                "fileTable": file_table,
                "fileTableCount": file_count,
                "fileTableJoin": "direct" if in_range else "out-of-range",
                "declaredFileRow": declared_row,
                "executionBoundary": "unobserved",
            })
    recursive_incoming: dict[int, list[dict[str, int]]] = {}
    for call in calls:
        if call["argsCountPassed"] is None or call["fileTableJoin"] != "direct":
            continue
        recursive_incoming.setdefault(call["low16Index"], []).append({
            "callerVmMethodIndex": call["vmMethodIndex"],
            "callInstructionIndex": call["instructionIndex"],
            "argsCountPassed": call["argsCountPassed"],
        })
    for slot in frame_slots:
        if slot["slotDomain"] != "argument":
            continue
        incoming = recursive_incoming.get(slot["vmMethodIndex"], [])
        slot["authoredRecursiveCallSites"] = incoming
        slot["authoredRecursiveCallCoverage"] = (
            "unresolved" if not incoming
            else "all-in-range" if all(
                0 <= slot["slotIndex"] < call["argsCountPassed"] for call in incoming
            ) else "some-out-of-range"
        )
    return {
        "source": source,
        "input": parsed["input"],
        "consumedBytes": parsed["consumedBytes"],
        "sourceSelection": "caller-supplied-patch-file",
        "callCount": len(calls),
        "externStackRewindCount": sum(
            row["evaluationStackRewindSlots"] is not None for row in calls
        ),
        "conditionalConstructorStackRewindCount": sum(
            row["conditionalConstructorStackRewindSlots"] is not None for row in calls
        ),
        "branchCount": len(branches),
        "tableOperandCount": len(table_operands),
        "frameHeaderCount": len(frame_headers),
        "frameSlotCount": len(frame_slots),
        "returnCount": len(returns),
        "exceptionHandlerCount": len(exception_handlers),
        "leaveCount": len(leaves),
        "endfinallyCount": len(endfinallys),
        "calls": calls,
        "branches": branches,
        "tableOperands": table_operands,
        "frameHeaders": frame_headers,
        "frameSlots": frame_slots,
        "returns": returns,
        "exceptionHandlers": exception_handlers,
        "leaves": leaves,
        "endfinallys": endfinallys,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        contract, layout, audit = validate_vm_operand_contract(
            args.contract, gameassembly=args.gameassembly, metadata_path=args.metadata
        )
        files = [
            project_vm_operands(path.read_bytes(), layout, contract, source=str(path))
            for path in args.input
        ]
    except (VMOperandEvidenceError, OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"ifix-vm-operands: {error}", file=sys.stderr)
        return 1
    report = {
        "schema": "endfield-ifix-vm-operand-audit-v12",
        "status": "validated_selected_native_loader_and_consumer",
        "audit": audit,
        "files": files,
        "fileCount": len(files),
        "callCount": sum(row["callCount"] for row in files),
        "externStackRewindCount": sum(row["externStackRewindCount"] for row in files),
        "conditionalConstructorStackRewindCount": sum(
            row["conditionalConstructorStackRewindCount"] for row in files
        ),
        "branchCount": sum(row["branchCount"] for row in files),
        "tableOperandCount": sum(row["tableOperandCount"] for row in files),
        "frameHeaderCount": sum(row["frameHeaderCount"] for row in files),
        "frameSlotCount": sum(row["frameSlotCount"] for row in files),
        "returnCount": sum(row["returnCount"] for row in files),
        "exceptionHandlerCount": sum(row["exceptionHandlerCount"] for row in files),
        "leaveCount": sum(row["leaveCount"] for row in files),
        "endfinallyCount": sum(row["endfinallyCount"] for row in files),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"validated {len(files)} patch files, {report['callCount']} file-row call joins, "
        f"{report['externStackRewindCount']} external stack rewinds, "
        f"{report['conditionalConstructorStackRewindCount']} conditional constructor rewinds, "
        f"{report['branchCount']} branch targets, "
        f"{report['tableOperandCount']} field/string operands, "
        f"{report['frameSlotCount']} frame-slot operands"
        f", {report['exceptionHandlerCount']} exception handlers, "
        f"{report['leaveCount']} leaves and {report['endfinallyCount']} endfinallys"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
