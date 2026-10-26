"""Project IFix table, frame, return, branch, and exception operands through native bodies.

The selected ``PatchManager.LoadInternal`` body preserves file-table order in
the VM's method tables. ``VirtualMachine.Execute`` indexes those tables with
the low 16 call-operand bits, uses signed branch offsets relative to the
current instruction, selects the VM's string/field tables, and uses a
``StackSpace`` header for frame slots. Actual execution remains open.
The selected ``Constrained`` path also projects the preceding instruction's
operand to a conditional evaluation-slot conversion and Object-index store.
The native facts each projection relies on are listed in
:func:`validate_vm_operand_contract`.

The command checks the reviewed ``ifix_vm_operands_native.json`` loader and
interpreter bodies, then joins operands of caller-supplied, MD5-verified patch
dumps (``--input``, repeatable):

- ``Call``, ``Callvirt``, ``CallExtern`` and ``Newobj`` low halves to declared
  file rows; the signed upper half of ``Call``/``Callvirt`` is the recursive
  ``argsCount``. For ``CallExtern`` the signed upper half rewinds that many
  12-byte evaluation-stack slots to the external argument base; ``Newobj``
  uses the same rewind when the resolved constructor's declaring-type base is
  not ``System.MulticastDelegate``. The selected delegate path instead consumes
  two slots and leaves one result, with an Integer-tag wrapper/factory path
  and a separate MethodInfo/reflection path; its result tail preserves Type.
  The Integer path's dispatcher is joined to the named CreateDelegate interface
  and image-qualified implementations. Generic fallback selection checks the
  delegate-Type cache, predicate-taking Any signature, rejection callback and
  Action/Func array choice. Separate rules authenticate the lazy catalog recipe
  and declared arities, parameter-Type projection with Func return Type last,
  MakeGenericMethod forwarding and captured closure arguments. Runtime manager
  selection, reflection arrays, cached values and reflection success remain open.
  ``CallExtern``'s encoded MethodDef delegate target and the conditional
  reflected-result path through ``ReflectionMethodInvoker.Invoke`` and
  ``Call.PushObjectAsResult`` are validated too.
- ``Br``, ``Brtrue`` and ``Brfalse`` signed relative targets; ``Leave`` as an
  absolute pending target (zero kept as a sentinel) and ``Endfinally -1`` as
  a conditional resume from that pending target.
- ``Ldstr`` and nonnegative ``Ldfld``/``Ldsfld``/``Stfld``/``Stsfld`` to
  declared string and field rows; ``Initobj`` and ``Constrained`` to the
  loader's ordered ``externTypes`` table, with out-of-range indices visible.
- ``StackSpace`` local and evaluation-stack counts, local-slot bounds for
  ``Ldloc``/``Ldloca``/``Stloc``, named ``Ldarg`` slots without assuming a
  runtime argument count (with coverage under authored recursive call edges),
  and whether ``Ret`` selects a stack value.
- conditional ``Ldarg``/``Ldloc``/``Stloc``/``Dup`` copy/store tag paths and
  negative static-field indexes (bitwise complement of the signed operand).
  Negative ``Ldfld``/``Stfld`` select AnonymousStorey with the same complement;
  store removes two Value slots without an explicit consumed-reference clear.
  Separate alias rules derive same-slot/shared-index copy/store consequences
  under stable whole-slot storage hypotheses. Separate byte-overlap equations
  preserve the post-copy tag guard and post-rebase store index read. Live alias
  selection stays open.
  StackReference encoding and one-hop resolution are authenticated separately,
  as are UpdateReference's conditional target requests, recursive chain reads
  and outward writeback, new-field hash-key storage/default/initializer requests,
  complete object conversion programs and reference-address constructors.
  Anonymous-storey rules authenticate the normal loader record loop and
  reflection-sized interface slots, plain field initialization and Newanon's
  argument copies, recursive request and saved-object restore. Nonzero raw
  framing still requires runtime reflection method counts and order.
  Concrete storage, reflection/helper results and live alias selection stay open.
- the loader's six ``ReadInt32`` calls and field stores per 24-byte exception
  record: handler type, catch-type id, instruction boundary indices and their
  bounds against the VM method.
- conditional literal, null, discard and no-op effects; ``Conv_I8`` selects
  Integer, Long, Float, Double or the runtime exception route after
  ``resolveStackReference`` returns normally. Hardware exception state and
  complete stack semantics of the older joins stay open.
  The remaining conversion and comparison programs have separate conditional
  proofs, including Ceq's bit equality, left-tag relational selection and the
  unsigned stack-reference pointer shortcut. A complete ordinary-loop enum
  dispatcher authenticates the shared default request family separately from
  the entry frame header.
  Array and bitwise/unary routes have conditional typed width/tag programs.
  Long/double literal payloads and packed Switch tables retain physical
  instruction indexes as InlineData; Switch leaves its inspected slot in place.
  Starg authenticates argument store followed by source physical clearing.
  Volatile selects the common PC caller, whose later loop/exception join stays open.
- ``Ldftn``/``Ldvirtftn`` whole signed external-method indices, with Object
  slot push/replacement; ``Ldvirtftn2``'s unsigned low-half anonymous-storey
  VTable slot and Integer method-slot rewrite. Runtime receiver compatibility,
  concrete unequal-type resolver results and actual VTable values stay open.
  The unequal-type rule validates the Type/base-definition cache keys, cached
  null hits, GetMember candidate matching, BaseType traversal and null caching;
  its flags omit DeclaredOnly, so no nearest-declared-override claim is made.
- the non-generic zero-argument GenericDelegate Action bridge stores VM/method
  id/target, derives receiver flags from target non-nullness, optionally pushes
  the bound object, and forwards extraArgNum with zero refCount to Execute.
  Registered all-object generic Action/Func contexts prove ordered arguments,
  N+extraArgNum, and Func's saved-reference GetObject result/physical-slot clear
  followed by its last generic-context type/cast request. Actual invocation,
  reflection-selected context, method-id validity and Call.Begin capacity stay open.

Supplying ``--outer-summary``, ``--outer-ledger`` and
``--expected-input-set-sha256`` together requires the current VFS audit and
every IFix patch file's verified length and MD5; without them the report
covers caller-supplied bytes only. It writes the ``--output`` report
(conventionally ``reports/animestudio/ifix_vm_operands_current.json``). These
are authored control-flow edges, not an execution trace; runtime storage,
runtime opcode values, callee outcomes and execution remain open.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.corpus_common import validate_provenance
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.ifix_patch import (
    EXCEPTION_RECORD_SIZE,
    INSTRUCTION_WORD_SIZE,
    ordered_signature_parameters,
    parse_ifix_patch,
)
from scripts.game_data.ifix_vm_instruction_native import (
    decode_patch_opcodes,
    selected_opcode_layout,
)
from scripts.game_data.ifix_vm_delegate_rules import validate_delegate_rules
from scripts.game_data.ifix_vm_generic_delegate_rules import validate_generic_delegate_rules
from scripts.game_data.ifix_vm_generic_catalog_rules import validate_generic_catalog_rules
from scripts.game_data.ifix_vm_generic_binding_rules import validate_generic_binding_rules
from scripts.game_data.ifix_vm_slot_copy_rules import project_slot_copy_rules, validate_slot_copy_rules
from scripts.game_data.ifix_vm_slot_alias_rules import project_slot_alias_rules, validate_slot_alias_rules
from scripts.game_data.ifix_vm_negative_field_rules import project_negative_field_rules, validate_negative_field_rules
from scripts.game_data.ifix_vm_instance_field_rules import project_instance_field_rules, validate_instance_field_rules
from scripts.game_data.ifix_vm_stack_reference_rules import project_stack_reference_rules, validate_stack_reference_rules
from scripts.game_data.ifix_vm_reference_update_rules import validate_reference_update_rules
from scripts.game_data.ifix_vm_chain_field_rules import validate_chain_field_rules
from scripts.game_data.ifix_vm_new_field_rules import validate_new_field_rules
from scripts.game_data.ifix_vm_object_conversion_rules import validate_object_conversion_rules
from scripts.game_data.ifix_vm_reference_address_rules import project_reference_address_rules, validate_reference_address_rules
from scripts.game_data.ifix_vm_dispatch_rules import validate_dispatch_rules
from scripts.game_data.ifix_vm_comparison_rules import project_comparison_rules, validate_comparison_rules
from scripts.game_data.ifix_vm_conversion_opcode_rules import project_conversion_opcode_rules, validate_conversion_opcode_rules
from scripts.game_data.ifix_vm_anonymous_storey_rules import validate_anonymous_storey_rules
from scripts.game_data.ifix_vm_array_rules import project_array_rules, validate_array_rules
from scripts.game_data.ifix_vm_bitwise_rules import project_bitwise_rules, validate_bitwise_rules
from scripts.game_data.ifix_vm_literal_control_rules import project_literal_control_rules, validate_literal_control_rules
from scripts.game_data.ifix_vm_array_reference_rules import validate_array_reference_rules
from scripts.game_data.ifix_vm_indirect_opcode_rules import project_indirect_opcode_rules, validate_indirect_opcode_rules
from scripts.game_data.ifix_vm_arithmetic_rules import project_arithmetic_rules, validate_arithmetic_rules
from scripts.game_data.ifix_vm_positive_field_rules import project_positive_field_rules, validate_positive_field_rules
from scripts.game_data.ifix_vm_branch_rules import project_branch_rules, validate_branch_rules
from scripts.game_data.ifix_vm_object_opcode_rules import project_object_opcode_rules, validate_object_opcode_rules
from scripts.game_data.ifix_vm_call_opcode_rules import project_call_opcode_rules, validate_call_opcode_rules
from scripts.game_data.ifix_vm_init_constrained_rules import project_init_constrained_rules, validate_init_constrained_rules
from scripts.game_data.ifix_vm_exception_dispatch_rules import project_exception_dispatch_rules, validate_exception_dispatch_rules
from scripts.game_data.ifix_vm_string_opcode_rules import project_string_opcode_rules, validate_string_opcode_rules
from scripts.game_data.ifix_vm_static_initializer_rules import validate_static_initializer_rules
from scripts.game_data.ifix_vm_anonymous_loader_rules import validate_anonymous_loader_rules
from scripts.game_data.ifix_vm_floating_remainder_rules import validate_floating_remainder_rules
from scripts.game_data.ifix_vm_stack_construction_rules import validate_stack_construction_rules
from scripts.game_data.ifix_vm_reference_helper_rules import validate_reference_helper_rules
from scripts.game_data.ifix_vm_instance_alias_rules import project_instance_alias_rules, validate_instance_alias_rules
from scripts.game_data.ifix_vm_instance_byte_alias_rules import validate_instance_byte_alias_rules
from scripts.game_data.ifix_vm_call_zero_rules import validate_call_zero_rules
from scripts.game_data.ifix_vm_call_push_rules import validate_call_push_rules
from scripts.game_data.ifix_vm_runtime_exception_rules import validate_runtime_exception_rules
from scripts.game_data.ifix_vm_exception_funclet_rules import validate_exception_funclet_rules
from scripts.game_data.ifix_vm_entry_frame_rules import validate_entry_frame_rules
from scripts.game_data.ifix_vm_anonymous_info_constructor_rules import validate_anonymous_info_constructor_rules
from scripts.game_data.ifix_vm_reflection_invoker_constructor_rules import validate_reflection_invoker_constructor_rules
from scripts.game_data.ifix_vm_reflection_invoker_rules import validate_reflection_invoker_rules
from scripts.game_data.ifix_vm_bridge_dispatch_rules import validate_bridge_dispatch_rules
from scripts.game_data.ifix_vm_call_reference_update_rules import validate_call_reference_update_rules
from scripts.game_data.ifix_vm_reflection_cleanup_rules import validate_reflection_cleanup_rules
from scripts.game_data.ifix_vm_call_scalar_rules import validate_call_scalar_rules
from scripts.game_data.ifix_vm_generic_reference_get_rules import validate_generic_reference_get_rules
from scripts.game_data.ifix_vm_generic_scalar_get_rules import validate_generic_scalar_get_rules
from scripts.game_data.ifix_vm_generic_adjustor_rules import validate_generic_adjustor_rules
from scripts.game_data.ifix_vm_anonymous_virtual_rules import validate_anonymous_virtual_rules
from scripts.game_data.ifix_vm_vm_construction_rules import validate_vm_construction_rules
from scripts.game_data.ifix_vm_vm_table_accessor_rules import validate_vm_table_accessor_rules
from scripts.game_data.ifix_vm_rule_inventory import build_rule_inventory
from scripts.game_data.ifix_vm_generic_bridge_rules import validate_generic_bridge_rules
from scripts.game_data.ifix_vm_delegate_bridge_rules import validate_delegate_bridge_rules
from scripts.game_data.ifix_vm_wrapper_dispatch_rules import validate_wrapper_dispatch_rules
from scripts.game_data.ifix_vm_virtual_dispatch_rules import (
    project_virtual_dispatch_rules, validate_virtual_dispatch_rules,
)
from scripts.game_data.ifix_vm_basic_rules import project_basic_rules, validate_basic_rules
from scripts.game_data.ifix_vm_function_pointer_rules import (
    project_function_pointer_rules, validate_function_pointer_rules,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import (
    enum_members,
    field_defaults,
    native_enum_members,
    runtime_type_name,
    runtime_type_field_offsets,
)


DEFAULT_CONTRACT = CONTRACTS_DIR / "ifix_vm_operands_native.json"
SCHEMA = "endfield.ifix-vm-operands-native-contract.v31"


class VMOperandEvidenceError(ValueError):
    """A selected native, contract, or patch-file gate did not validate."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _validate_current_vfs_inputs(
    paths: list[Path], summary_path: Path, ledger_path: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Bind every selected IFix patch byte stream to the current outer VFS gate."""
    if len(expected_input_set_sha256) != 64 or any(
        char not in "0123456789abcdefABCDEF" for char in expected_input_set_sha256
    ):
        raise VMOperandEvidenceError("IFix outer gate: expected 64 hex input-set characters")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        first = next(stream, None)
        if first is None:
            raise VMOperandEvidenceError("IFix outer gate: empty ledger")
        header = json.loads(first)
        if header.get("recordType") != "audit_header":
            raise VMOperandEvidenceError("IFix outer gate: missing audit header")
        for line in stream:
            row = json.loads(line)
            if row.get("recordType") != "file" or row.get("blockName") != "IFixPatchOut":
                continue
            virtual_path = str(row.get("virtualPath", ""))
            if virtual_path in rows:
                raise VMOperandEvidenceError(f"IFix outer gate: duplicate {virtual_path}")
            rows[virtual_path] = row
    failures, provenance = validate_provenance(
        summary, header, ledger_path, expected_input_set_sha256,
    )
    if failures:
        first = failures[0]
        raise VMOperandEvidenceError(
            f"IFix outer gate:{first['scope']}.{first['field']}: "
            f"expected={first['expected']} actual={first['actual']}"
        )
    selected: dict[str, Path] = {}
    for path in paths:
        virtual_path = f"Data/IFixPatchOut/Windows/{path.name}"
        if virtual_path in selected:
            raise VMOperandEvidenceError(f"IFix outer gate: duplicate selected {virtual_path}")
        selected[virtual_path] = path
    if not rows or set(rows) != set(selected):
        raise VMOperandEvidenceError(
            "IFix outer gate: file set mismatch "
            f"expected={sorted(rows)} selected={sorted(selected)}"
        )
    joined = []
    for virtual_path, path in sorted(selected.items()):
        row = rows[virtual_path]
        if row.get("status") != "verified" or row.get("boundaryStatus") != "boundary_verified":
            raise VMOperandEvidenceError(
                f"IFix outer gate: {virtual_path} lacks verified outer bytes"
            )
        data = path.read_bytes()
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        expected_md5 = str(row.get("recomputedFileDataMd5", "")).upper()
        if len(data) != row.get("length") or actual_md5 != expected_md5:
            raise VMOperandEvidenceError(
                f"IFix outer gate: {virtual_path} byte identity mismatched "
                f"expectedLength={row.get('length')} actualLength={len(data)} "
                f"expectedMd5={expected_md5} actualMd5={actual_md5}"
            )
        joined.append({
            "virtualPath": virtual_path, "source": str(path),
            "length": len(data), "md5": actual_md5,
        })
    return {
        "status": "validated_current_outer_file_set",
        "provenance": provenance,
        "files": joined,
    }


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


def _require_direct_jump(
    body: bytes, body_rva: int, jump_rva: int, target_rva: int, *, label: str
) -> None:
    """Verify one x64 near jump inside an authenticated method body."""
    offset = jump_rva - body_rva
    if offset < 0 or offset + 5 > len(body) or body[offset] != 0xE9:
        raise VMOperandEvidenceError(f"{label}: missing near jump at 0x{jump_rva:x}")
    relative = int.from_bytes(body[offset + 1:offset + 5], "little", signed=True)
    actual_target = jump_rva + 5 + relative
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


def _validate_initobj_type_operand(
    image: Any,
    spec: dict[str, Any],
    loader_body: bytes,
    loader_rva: int,
    consumer_body: bytes,
    consumer_rva: int,
    opcode_ids: dict[str, int],
    field_offsets: dict[str, int],
    loaded_tables: list[dict[str, Any]],
    read_int32_rva: int,
) -> dict[str, Any]:
    """Prove that Initobj indexes the loader's ordered externTypes rows."""
    if (
        spec.get("evidenceBoundary") != "direct"
        or spec.get("opcode") != "Initobj"
        or opcode_ids.get("Initobj") != spec.get("opcodeId")
        or spec.get("runtimeField") != "externTypes"
        or spec.get("fileTable") != "externTypes"
    ):
        raise VMOperandEvidenceError("Initobj type operand: unsupported table claim")
    table_rows = [
        row for row in loaded_tables
        if row.get("runtimeField") == "externTypes"
        and row.get("fileTable") == "externTypes"
    ]
    if len(table_rows) != 1:
        raise VMOperandEvidenceError("Initobj type operand: missing unique loader table")
    table = table_rows[0]
    _require_direct_call(
        loader_body, loader_rva,
        _int_hex(table["countReadRva"], "Initobj externTypes count read"),
        read_int32_rva, label="Initobj externTypes count",
    )
    reader = spec["readStringMethod"]
    owners = [
        row for row in image.metadata.types
        if image.metadata.type_full_name(row) == reader["type"]
    ]
    if len(owners) != 1:
        raise VMOperandEvidenceError(
            f"Initobj type reader: expected one owner, found {len(owners)}"
        )
    _method, read_string_rva = _selected_method_identity(
        image, owners[0], reader, label="Initobj type reader"
    )
    _require_direct_call(
        loader_body, loader_rva,
        _int_hex(table["rowReadStringRva"], "Initobj externTypes string read"),
        read_string_rva, label="Initobj externTypes row read",
    )
    for label, body, body_rva, witness in (
        ("Initobj loader row arguments", loader_body, loader_rva, spec["loaderRowArguments"]),
        ("Initobj loader field store", loader_body, loader_rva, spec["loaderFieldStore"]),
        ("Initobj consumer field load", consumer_body, consumer_rva, spec["consumerFieldLoad"]),
        ("Initobj consumer operand read", consumer_body, consumer_rva, spec["consumerOperandRead"]),
    ):
        witness_rva = _int_hex(witness["rva"], f"{label} rva")
        expected = bytes.fromhex(witness["hex"])
        offset = witness_rva - body_rva
        if not expected or not 0 <= offset <= len(body) - len(expected) or body[offset:offset + len(expected)] != expected:
            raise VMOperandEvidenceError(
                f"{label}:mismatched:0x{witness_rva:x} expectedBytes={expected.hex()}"
            )
    if (
        spec["loaderFieldStore"]["rva"] != table["vmFieldStoreRva"]
        or bytes.fromhex(spec["loaderFieldStore"]["hex"])[-1] != field_offsets["externTypes"]
        or bytes.fromhex(spec["consumerFieldLoad"]["hex"])[-1] != field_offsets["externTypes"]
    ):
        raise VMOperandEvidenceError("Initobj externTypes field offset differs")
    store_helper = spec["loaderRowStoreHelper"]
    store_rva = _int_hex(store_helper["rva"], "Initobj row store helper")
    _validate_code_window_bytes(
        store_helper,
        image.pe.bytes_at_va(image.pe.image_base + store_rva, store_helper["byteCount"]),
        label="Initobj row store helper", rva=store_rva,
    )
    _require_direct_call(
        loader_body, loader_rva,
        _int_hex(table["rowStoreRva"], "Initobj externTypes row store"),
        store_rva, label="Initobj externTypes row store",
    )
    _require_near_jcc(
        consumer_body, consumer_rva,
        _int_hex(spec["consumerDispatchBranchRva"], "Initobj dispatch branch"),
        _int_hex(spec["consumerEntryRva"], "Initobj entry"),
        label="Initobj dispatch",
    )
    fetch_helper = spec["consumerRowFetchHelper"]
    fetch_rva = _int_hex(fetch_helper["rva"], "Initobj row fetch helper")
    _validate_code_window_bytes(
        fetch_helper,
        image.pe.bytes_at_va(image.pe.image_base + fetch_rva, fetch_helper["byteCount"]),
        label="Initobj row fetch helper", rva=fetch_rva,
    )
    _require_direct_call(
        consumer_body, consumer_rva,
        _int_hex(spec["consumerRowFetchCallRva"], "Initobj row fetch"),
        fetch_rva, label="Initobj row fetch",
    )
    return {
        "status": "validated_ordered_extern_type_index",
        "runtimeField": "externTypes",
        "fileTable": "externTypes",
        "evidenceBoundary": "direct",
        "executionBoundary": "unobserved",
    }


def _validate_initobj_stack_effect(
    image: Any,
    spec: dict[str, Any],
    constrained_spec: dict[str, Any],
    consumer_body: bytes,
    consumer_rva: int,
    opcode_ids: dict[str, int],
    frame_claims: list[dict[str, Any]],
    arithmetic: dict[str, dict[str, Any]],
    extents: dict[int, int],
) -> dict[str, Any]:
    """Prove the selected Ldloca -> Initobj local-reference route."""
    reference = spec["referenceValueType"]
    if (
        spec.get("evidenceBoundary") != "conditional"
        or spec.get("executionBoundary") != "unobserved"
        or spec.get("addressProducer") != "Ldloca"
        or opcode_ids.get("Ldloca") != 85
        or opcode_ids.get("Initobj") != 55
        or spec.get("pointerSubtractHelperRef")
        != "constrainedTypeOperand.stackEffect.priorPointerHelper"
        or reference != {
            "enumType": "IFix.Core.ValueType", "name": "StackReference", "id": 4,
        }
        or len([row for row in frame_claims if row.get("opcode") == "Ldloca"
                and row.get("slotDomain") == "localAddress"]) != 1
    ):
        raise VMOperandEvidenceError("Initobj stack effect: unsupported local-reference route")
    members = native_enum_members(
        image.metadata, field_defaults(image.metadata), image.pe,
        image.registration, reference["enumType"],
    )
    if [
        {"id": row["id"], "name": row["name"]}
        for row in members if row["name"] == reference["name"]
    ] != [
        {"id": reference["id"], "name": reference["name"]}
    ]:
        raise VMOperandEvidenceError("Initobj stack effect: StackReference enum differs")
    selected: dict[str, tuple[bytes, int]] = {"consumer": (consumer_body, consumer_rva)}
    for label, key in (
        ("updateReference", "updateReferenceMethod"),
        ("pushObject", "pushObjectMethod"),
    ):
        method_spec = spec[key]
        owners = [
            row for row in image.metadata.types
            if image.metadata.type_full_name(row) == method_spec["type"]
        ]
        if len(owners) != 1:
            raise VMOperandEvidenceError(f"Initobj {label}: expected one owner")
        body, rva, _digest = _selected_method_body(
            image, owners[0], method_spec,
            label=f"Initobj {label}", extents=extents,
        )
        selected[label] = body, rva
    create = spec["createInstanceMethod"]
    owners = [
        row for row in image.metadata.types
        if image.metadata.type_full_name(row) == create["type"]
    ]
    if len(owners) != 1:
        raise VMOperandEvidenceError("Initobj CreateInstance: expected one owner")
    method, create_rva = _selected_method_identity(
        image, owners[0], create, label="Initobj CreateInstance"
    )
    parameter_types = [
        image.metadata.metadata_type_name(row.type_index)
        for row in image.metadata.parameters_for(method)
    ]
    if parameter_types != create["parameterTypes"]:
        raise VMOperandEvidenceError(
            f"Initobj CreateInstance parameters: expected {create['parameterTypes']}, "
            f"actual {parameter_types}"
        )
    entry = bytes.fromhex(create["entryBytes"])
    if image.pe.bytes_at_va(image.pe.image_base + create_rva, len(entry)) != entry:
        raise VMOperandEvidenceError("Initobj CreateInstance entry bytes differ")
    if not entry or len(entry) > 32:
        raise VMOperandEvidenceError("Initobj CreateInstance entry window unbounded")
    witnesses = spec["witnesses"]
    expected_names = {
        "ldlocaOperand", "ldlocaAddressStore", "ldlocaReferenceTag",
        "initobjSelectedSlot", "initobjTypeToActivator",
        "initobjTypeToUpdateReference", "initobjActivatorResultToUpdateReference",
        "initobjSelectedSlotToUpdateReference", "stackReferenceTagComparison",
        "stackReferenceTargetSlot", "destinationSlotIndexStore",
        "destinationValueTagStore",
    }
    if (
        not isinstance(witnesses, list)
        or {row["name"] for row in witnesses} != expected_names
        or len(witnesses) != len(expected_names)
    ):
        raise VMOperandEvidenceError("Initobj stack effect: missing or repeated witnesses")
    for row in witnesses:
        label = f"Initobj {row['name']}"
        if row["body"] not in selected:
            raise VMOperandEvidenceError(f"{label}: unknown method body")
        body, body_rva = selected[row["body"]]
        witness_rva = _int_hex(row["rva"], f"{label}.rva")
        expected = bytes.fromhex(row["hex"])
        offset = witness_rva - body_rva
        if (
            not expected or len(expected) > 64 or offset < 0
            or offset + len(expected) > len(body)
            or body[offset:offset + len(expected)] != expected
        ):
            raise VMOperandEvidenceError(
                f"{label}:mismatched:0x{witness_rva:x} expectedBytes={row['hex']}"
            )
    helper = constrained_spec["stackEffect"]["priorPointerHelper"]
    helper_rva = _int_hex(helper["rva"], "Initobj pointer subtract helper")
    _validate_code_window_bytes(
        helper,
        image.pe.bytes_at_va(image.pe.image_base + helper_rva, helper["byteCount"]),
        label="Initobj pointer subtract helper", rva=helper_rva,
    )
    top_advance = spec["topAdvanceHelper"]
    top_advance_rva = _int_hex(top_advance["rva"], "Initobj top advance helper")
    expected_advance = bytes.fromhex(top_advance["hex"])
    if (
        not 1 <= len(expected_advance) <= 32
        or image.pe.bytes_at_va(image.pe.image_base + top_advance_rva, len(expected_advance))
        != expected_advance
    ):
        raise VMOperandEvidenceError("Initobj top advance helper bytes differ")
    call_targets = {
        "ldlocaSlotMultiplyRva": _int_hex(arithmetic["signedSlotMultiply"]["rva"], "Initobj slot multiply"),
        "ldlocaSlotAddRva": _int_hex(arithmetic["pointerAdd"]["rva"], "Initobj slot add"),
        "ldlocaTopAdvanceRva": top_advance_rva,
        "initobjTopSlotSubtractRva": helper_rva,
        "createInstanceRva": create_rva,
        "updateReferenceRva": selected["updateReference"][1],
        "stackReferencePushObjectRva": selected["pushObject"][1],
        "pushObjectManagedStoreRva": _int_hex(
            constrained_spec["stackEffect"]["managedStackStoreHelper"]["rva"],
            "Initobj managed-stack store",
        ),
    }
    if set(spec["calls"]) != set(call_targets):
        raise VMOperandEvidenceError("Initobj stack effect: call-site set differs")
    for key, target_rva in call_targets.items():
        label = f"Initobj {key}"
        site = _int_hex(spec["calls"][key], label)
        body_name = (
            "updateReference" if key == "stackReferencePushObjectRva"
            else "pushObject" if key == "pushObjectManagedStoreRva"
            else "consumer"
        )
        body, body_rva = selected[body_name]
        _require_direct_call(body, body_rva, site, target_rva, label=label)
    _require_direct_jump(
        consumer_body, consumer_rva,
        _int_hex(spec["ldlocaTailJumpRva"], "Initobj Ldloca tail jump"),
        _int_hex(spec["ldlocaTailEntryRva"], "Initobj Ldloca tail entry"),
        label="Initobj Ldloca tail jump",
    )
    _require_direct_jump(
        consumer_body, consumer_rva,
        _int_hex(spec["ldlocaAdvanceJumpRva"], "Initobj Ldloca advance jump"),
        _int_hex(spec["ldlocaAdvanceEntryRva"], "Initobj Ldloca advance entry"),
        label="Initobj Ldloca advance jump",
    )
    body, body_rva = selected["updateReference"]
    _require_near_jcc(
        body, body_rva,
        _int_hex(spec["stackReferenceBranchRva"], "Initobj StackReference branch"),
        _int_hex(spec["stackReferenceEntryRva"], "Initobj StackReference entry"),
        label="Initobj StackReference branch",
    )
    return {
        "status": "validated_conditional_ldloca_local_update",
        "createdValue": "System.Activator.CreateInstance(System.Type) result",
        "referenceRoute": "ValueType.StackReference -> UpdateReference -> PushObject",
        "destination": "Ldloca-selected local slot when adjacent in authored VM code",
        "evidenceBoundary": "conditional",
        "executionBoundary": "unobserved",
    }


def _validate_constrained_type_operand(
    image: Any,
    spec: dict[str, Any],
    initobj_spec: dict[str, Any],
    consumer_body: bytes,
    consumer_rva: int,
    opcode_ids: dict[str, int],
    field_offsets: dict[str, int],
    loaded_tables: list[dict[str, Any]],
    extents: dict[int, int],
    arithmetic: dict[str, dict[str, Any]],
    layout: dict[str, Any],
    header: dict[str, Any],
) -> dict[str, Any]:
    """Authenticate Constrained's separate dispatch and externTypes row read."""
    if (
        spec.get("evidenceBoundary") != "direct"
        or spec.get("opcode") != "Constrained"
        or opcode_ids.get("Constrained") != spec.get("opcodeId")
        or spec.get("runtimeField") != "externTypes"
        or spec.get("fileTable") != "externTypes"
        or spec.get("rowFetchHelperRef") != "initobjTypeOperand.consumerRowFetchHelper"
        or initobj_spec.get("runtimeField") != "externTypes"
        or len([
            row for row in loaded_tables
            if row.get("runtimeField") == "externTypes"
            and row.get("fileTable") == "externTypes"
        ]) != 1
    ):
        raise VMOperandEvidenceError("Constrained type operand: unsupported table claim")
    windows = spec["dispatchWindows"]
    if len(windows) != 2:
        raise VMOperandEvidenceError("Constrained dispatch: expected two selected windows")
    for index, witness in enumerate(windows):
        witness_rva = _int_hex(witness["rva"], f"Constrained dispatch[{index}].rva")
        expected = bytes.fromhex(witness["hex"])
        offset = witness_rva - consumer_rva
        if (
            not expected or not 0 <= offset <= len(consumer_body) - len(expected)
            or consumer_body[offset:offset + len(expected)] != expected
        ):
            raise VMOperandEvidenceError(
                f"Constrained dispatch[{index}]:mismatched:0x{witness_rva:x} "
                f"expectedBytes={expected.hex()}"
            )
    for label in ("consumerFieldLoad", "consumerOperandRead"):
        witness = spec[label]
        witness_rva = _int_hex(witness["rva"], f"Constrained {label}.rva")
        expected = bytes.fromhex(witness["hex"])
        offset = witness_rva - consumer_rva
        if (
            not expected or not 0 <= offset <= len(consumer_body) - len(expected)
            or consumer_body[offset:offset + len(expected)] != expected
        ):
            raise VMOperandEvidenceError(
                f"Constrained {label}:mismatched:0x{witness_rva:x} "
                f"expectedBytes={expected.hex()}"
            )
    if bytes.fromhex(spec["consumerFieldLoad"]["hex"])[-1] != field_offsets["externTypes"]:
        raise VMOperandEvidenceError("Constrained externTypes field offset differs")
    fetch_helper = initobj_spec["consumerRowFetchHelper"]
    fetch_rva = _int_hex(fetch_helper["rva"], "Constrained row fetch helper")
    _validate_code_window_bytes(
        fetch_helper,
        image.pe.bytes_at_va(image.pe.image_base + fetch_rva, fetch_helper["byteCount"]),
        label="Constrained row fetch helper", rva=fetch_rva,
    )
    _require_direct_call(
        consumer_body, consumer_rva,
        _int_hex(spec["consumerRowFetchCallRva"], "Constrained row fetch call"),
        fetch_rva, label="Constrained row fetch",
    )
    stack_effect = _validate_constrained_stack_effect(
        image, spec["stackEffect"], consumer_body, consumer_rva,
        extents, arithmetic, layout, header,
    )
    return {
        "status": "validated_ordered_extern_type_index",
        "opcode": "Constrained",
        "runtimeField": "externTypes",
        "fileTable": "externTypes",
        "evidenceBoundary": "direct",
        "executionBoundary": "unobserved",
        "stackEffect": stack_effect,
    }


def _validate_constrained_stack_effect(
    image: Any, spec: dict[str, Any], consumer_body: bytes, consumer_rva: int,
    extents: dict[int, int], arithmetic: dict[str, dict[str, Any]],
    layout: dict[str, Any], header: dict[str, Any],
) -> dict[str, Any]:
    """Check the selected conditional slot conversion and object-slot stores."""
    if spec.get("evidenceBoundary") != "conditional" or spec.get("executionBoundary") != "unobserved":
        raise VMOperandEvidenceError("Constrained stack effect: unsupported boundary")
    windows = spec["executeWindows"]
    if not windows or len({row["name"] for row in windows}) != len(windows):
        raise VMOperandEvidenceError("Constrained stack effect: missing or repeated windows")
    previous_end = consumer_rva
    for row in windows:
        rva = _int_hex(row["rva"], f"Constrained {row['name']}.rva")
        count = row["byteCount"]
        if rva < previous_end or rva + count > consumer_rva + len(consumer_body):
            raise VMOperandEvidenceError(f"Constrained {row['name']}: outside ordered Execute body")
        _validate_code_window_bytes(
            row, consumer_body[rva - consumer_rva:rva - consumer_rva + count],
            label=f"Constrained {row['name']}", rva=rva,
        )
        previous_end = rva + count
    helpers = {}
    for key in ("priorPointerHelper", "managedStackStoreHelper"):
        row = spec[key]
        rva = _int_hex(row["rva"], f"Constrained {key}.rva")
        _validate_code_window_bytes(
            row, image.pe.bytes_at_va(image.pe.image_base + rva, row["byteCount"]),
            label=f"Constrained {key}", rva=rva,
        )
        helpers[key] = rva
    method_spec = spec["toObjectMethod"]
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == method_spec["type"]]
    if len(owners) != 1:
        raise VMOperandEvidenceError("Constrained ToObject: expected one owner")
    to_object_body, to_object_rva, to_object_hash = _selected_method_body(
        image, owners[0], method_spec, label="Constrained ToObject", extents=extents,
    )
    method, _ = _selected_method_identity(image, owners[0], method_spec, label="Constrained ToObject")
    if image.metadata.metadata_type_name(method.return_type) != method_spec["returnTypeName"]:
        raise VMOperandEvidenceError("Constrained ToObject: return type differs")
    if not to_object_body:
        raise VMOperandEvidenceError("Constrained ToObject: empty selected body")
    call_targets = {
        "priorInstructionPointerSubtractRva": helpers["priorPointerHelper"],
        "priorOperandMultiplyRva": _int_hex(arithmetic["signedSlotMultiply"]["rva"], "Constrained slot multiply"),
        "topMinusOnePointerSubtractRva": helpers["priorPointerHelper"],
        "selectedSlotPointerSubtractRva": _int_hex(arithmetic["stackPointerSubtract"]["rva"], "Constrained slot subtract"),
        "toObjectRva": to_object_rva,
        "managedStackStoreRva": helpers["managedStackStoreHelper"],
    }
    if set(spec["calls"]) != set(call_targets):
        raise VMOperandEvidenceError("Constrained stack effect: call route differs")
    for key, target_rva in call_targets.items():
        _require_direct_call(
            consumer_body, consumer_rva,
            _int_hex(spec["calls"][key], f"Constrained {key}"),
            target_rva, label=f"Constrained {key}",
        )
    prior = spec["priorOperandRead"]
    prior_rva = _int_hex(prior["rva"], "Constrained prior operand read")
    prior_bytes = bytes.fromhex(prior["hex"])
    offset = prior_rva - consumer_rva
    instruction_operand_offset = layout["instruction"]["fieldOffsets"]["Operand"] - 16
    if (len(prior_bytes) != 4 or prior_bytes[:3] != b"\x48\x63\x4e"
            or prior_bytes[3] != instruction_operand_offset
            or consumer_body[offset:offset + len(prior_bytes)] != prior_bytes):
        raise VMOperandEvidenceError("Constrained prior instruction operand read differs")
    pointer_window_rva = _int_hex(windows[0]["rva"], "Constrained prior pointer window")
    pointer_lea = consumer_body[pointer_window_rva - consumer_rva:pointer_window_rva - consumer_rva + 3]
    if (pointer_lea[:2] != b"\x8d\x51"
            or pointer_lea[2] + 1 != INSTRUCTION_WORD_SIZE):
        raise VMOperandEvidenceError("Constrained previous-instruction stride differs")
    width_offset = offset + len(prior_bytes)
    slot_width_read = consumer_body[width_offset:width_offset + 5]
    if (len(slot_width_read) != 5 or slot_width_read[0] != 0xBE
            or int.from_bytes(slot_width_read[1:], "little") != header["slotBytes"]):
        raise VMOperandEvidenceError("Constrained evaluation-slot width differs")
    value = spec["valueLayout"]
    value_owners = [row for row in image.metadata.types
                    if image.metadata.type_full_name(row) == value["type"]]
    if len(value_owners) != 1:
        raise VMOperandEvidenceError("Constrained Value: expected one type")
    actual_offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, value_owners[0].index,
    )
    if actual_offsets != value["fieldOffsets"]:
        raise VMOperandEvidenceError("Constrained Value field offsets differ")
    members = enum_members(image.metadata, field_defaults(image.metadata), value["enumType"])
    object_rows = [row for row in members if row["name"] == value["objectMember"]["name"]]
    if len(object_rows) != 1 or object_rows[0]["id"] != value["objectMember"]["id"]:
        raise VMOperandEvidenceError("Constrained ValueType.Object differs")
    index_store = value["slotIndexStore"]
    index_rva = _int_hex(index_store["rva"], "Constrained slot index store")
    index_bytes = bytes.fromhex(index_store["hex"])
    type_store = value["slotTypeStore"]
    type_rva = _int_hex(type_store["rva"], "Constrained slot type store")
    type_bytes = bytes.fromhex(type_store["hex"])
    if (len(index_bytes) != 3 or index_bytes[:2] != b"\x89\x7b"
            or index_bytes[2] != actual_offsets["Value1"] - actual_offsets["Type"]
            or consumer_body[index_rva - consumer_rva:index_rva - consumer_rva + 3] != index_bytes
            or len(type_bytes) != 6 or type_bytes[:2] != b"\xc7\x03"
            or int.from_bytes(type_bytes[2:], "little") != object_rows[0]["id"]
            or consumer_body[type_rva - consumer_rva:type_rva - consumer_rva + 6] != type_bytes):
        raise VMOperandEvidenceError("Constrained object slot stores differ")
    return {
        "status": "validated_conditional_object_slot_conversion",
        "previousOperandRole": "offset-from-evaluation-top-minus-one",
        "slotBytes": header["slotBytes"],
        "toObjectMethod": f"{method_spec['type']}.{method_spec['method']}",
        "toObjectBodySha256": to_object_hash,
        "managedStackStore": "ToObject-return-at-selected-evaluation-slot-index",
        "valueTypeMember": value["objectMember"]["name"],
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
    """Authenticate reviewed loader/consumer bodies and table identities.

    The contract pins the selected ``PatchManager.LoadInternal`` and
    ``VirtualMachine.Execute`` bodies, their helpers and the VM table fields;
    this checks the explicit native pair, both method identities and complete
    body bytes, field offsets, the opcode enum, and each decisive call, branch
    and store before any operand is projected. What the pinned bodies show:

    - ``LoadInternal`` reads the file tables in order and stores each at the
      same index: VM bodies in ``unmanagedCodes``, resolved external methods in
      ``externMethods`` (``externInvokers`` is allocated from its length),
      external types through a helper in ``externTypes``, and the
      ``internStrings`` and ``fieldInfos`` rows. It reads each 24-byte
      exception record as six signed ``ReadInt32`` values stored, in file
      order, as ``HandlerType``, ``CatchTypeId``, ``TryStart``, ``TryEnd``,
      ``HandlerStart`` and ``HandlerEnd``.
    - ``Execute`` treats the first ``StackSpace`` instruction as a frame
      header (signed upper 16 bits reserve local slots, unsigned lower 16 bits
      evaluation-stack slots) and starts at the next instruction. ``Ldarg``
      indexes the runtime ``argumentBase``; ``Ldloc``, ``Ldloca`` and
      ``Stloc`` index the local base after the runtime argument count. ``Ret
      0`` returns no stack value; a nonzero operand selects the top value.
    - ``Leave`` stores its signed operand as a pending absolute instruction
      index; ``Endfinally -1`` with a nonzero pending value multiplies it by
      the eight-byte instruction size, adds the code base, clears the pending
      value and re-enters dispatch. A zero pending value takes another path,
      so ``Leave 0`` is a sentinel, not a resume edge.
    - ``CallExtern`` on a cache miss builds a ``ReflectionMethodInvoker`` whose
      encoded MethodDef usage cell resolves to ``ReflectionMethodInvoker.Invoke``;
      for a normally returning nonconstructor with a nonvoid return, ``Invoke``
      calls ``Call.PushObjectAsResult``, which pushes the reflected result and
      updates the stack top ``Execute`` reads afterwards. ``Newobj`` compares
      the resolved constructor's declaring type's base (through the selected
      virtual slots) with ``System.MulticastDelegate`` before sharing the
      ``CallExtern`` rewind.
    - ``Initobj`` indexes ``externTypes`` (bounds-checked), takes the
      preceding evaluation slot as its destination reference, calls
      ``System.Activator.CreateInstance(Type)`` and passes the result to
      ``EvaluationStackOperation.UpdateReference``; for the ``StackReference``
      a ``Ldloca`` pushes, that branch calls ``PushObject`` on the referenced
      local slot and updates its value tag.
    - ``Constrained`` indexes ``externTypes`` on its own dispatch path, then
      selects the slot at ``top - 1 - precedingOperand`` (the preceding
      instruction's signed operand, in 12-byte slots), passes it with the type
      to ``EvaluationStackOperation.ToObject``, and on normal return stores
      the object in ``managedStack`` at the slot's evaluation-base index,
      writing that index and the native ``ValueType.Object`` tag.
    - Negative static/instance field operands select complemented internal
      indexes under separate conditional rules. AnonymousStorey field storage,
      one-hop StackReference resolution, conditional reference-update requests
      and whole-slot copy/store alias consequences have separate proofs;
      concrete storage, alias selection and recursive chain writes stay open.

    A row join is direct under the selected build and the caller's bytes;
    every stack, slot or resume effect is conditional on the path returning
    normally. None of it observes patch loading, dispatch or execution.
    """
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
    basic_audit = validate_basic_rules(image, contract["basicOpcodeRules"], body, rva, opcode_ids, contract)
    dispatch_audit = validate_dispatch_rules(image, contract["dispatchRules"], body, rva, opcode_ids, contract, extents)
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
    initobj_audit = _validate_initobj_type_operand(
        image, contract["initobjTypeOperand"], loader_body, loader_rva,
        body, rva, opcode_ids, offsets, loader_tables,
        _int_hex(contract["exceptionHandler"]["readMethod"]["rva"], "ReadInt32 rva"),
    )
    constrained_audit = _validate_constrained_type_operand(
        image, contract["constrainedTypeOperand"], contract["initobjTypeOperand"],
        body, rva, opcode_ids, offsets, loader_tables, extents,
        arithmetic, layout, header,
    )
    initobj_stack_audit = _validate_initobj_stack_effect(
        image, contract["initobjStackEffect"], contract["constrainedTypeOperand"],
        body, rva, opcode_ids, frame_claims, arithmetic, extents,
    )
    delegate_audit = validate_delegate_rules(
        image, contract["delegateConstruction"], body, rva, opcode_ids, contract, extents,
    )
    generic_delegate_audit = validate_generic_delegate_rules(
        image, contract["genericDelegateFactoryRules"], contract, extents,
    )
    generic_catalog_audit = validate_generic_catalog_rules(
        image, contract["genericDelegateCatalogRules"], contract, extents,
    )
    generic_binding_audit = validate_generic_binding_rules(
        image, contract["genericDelegateBindingRules"], contract, extents,
    )
    wrapper_dispatch_audit = validate_wrapper_dispatch_rules(
        image, contract["wrapperDelegateDispatch"], extents,
        contract["delegateConstruction"]["receiverDispatcher"],
    )
    delegate_bridge_audit = validate_delegate_bridge_rules(
        image, contract["delegateBridgeRules"], contract, extents,
    )
    generic_bridge_audit = validate_generic_bridge_rules(
        image, contract["genericBridgeRules"], contract, extents,
    )
    function_pointer_audit = validate_function_pointer_rules(
        image, contract["functionPointerRules"], body, rva, opcode_ids, contract,
    )
    virtual_dispatch_audit = validate_virtual_dispatch_rules(
        image, contract["virtualDispatchRules"], body, rva, opcode_ids, contract, extents,
    )
    slot_copy_audit = validate_slot_copy_rules(
        image, contract["slotCopyRules"], body, rva, opcode_ids, contract, extents,
    )
    negative_field_audit = validate_negative_field_rules(
        image, contract["negativeFieldRules"], body, rva, opcode_ids, contract, extents,
    )
    instance_field_audit = validate_instance_field_rules(
        image, contract["instanceFieldRules"], body, rva, opcode_ids, contract, extents,
    )
    stack_reference_audit = validate_stack_reference_rules(
        image, contract["stackReferenceRules"], body, rva, opcode_ids, contract, extents,
    )
    reference_update_audit = validate_reference_update_rules(
        image, contract["referenceUpdateRules"], contract, extents,
    )
    slot_alias_audit = validate_slot_alias_rules(
        contract["slotAliasRules"], contract["slotCopyRules"], slot_copy_audit,
    )
    chain_field_audit = validate_chain_field_rules(
        image, contract["chainFieldRules"], contract, extents,
    )
    new_field_audit = validate_new_field_rules(
        image, contract["newFieldRules"], contract, extents,
    )
    object_conversion_audit = validate_object_conversion_rules(
        image, contract["objectConversionRules"], contract, extents,
    )
    reference_address_audit = validate_reference_address_rules(
        image, contract["referenceAddressRules"], body, rva, opcode_ids, contract, extents,
    )
    comparison_audit = validate_comparison_rules(image, contract["comparisonRules"], body, rva, opcode_ids, contract, extents)
    conversion_opcode_audit = validate_conversion_opcode_rules(image, contract["conversionOpcodeRules"], body, rva, opcode_ids, contract, extents)
    anonymous_storey_audit = validate_anonymous_storey_rules(
        image, contract["anonymousStoreyRules"], body, rva, loader_body, loader_rva, opcode_ids, contract, extents,
    )
    array_audit = validate_array_rules(image, contract["arrayRules"], body, rva, opcode_ids, contract, extents)
    bitwise_audit = validate_bitwise_rules(image, contract["bitwiseRules"], body, rva, opcode_ids, contract, extents)
    literal_control_audit = validate_literal_control_rules(image, contract["literalControlRules"], body, rva, opcode_ids, contract, extents)
    array_reference_audit = validate_array_reference_rules(image, contract["arrayReferenceRules"], contract, extents)
    indirect_opcode_audit = validate_indirect_opcode_rules(image, contract["indirectOpcodeRules"], body, rva, opcode_ids, contract, extents)
    arithmetic_audit = validate_arithmetic_rules(image, contract["arithmeticRules"], body, rva, opcode_ids, contract, extents)
    positive_field_audit = validate_positive_field_rules(image, contract["positiveFieldRules"], body, rva, opcode_ids, contract, extents)
    branch_audit = validate_branch_rules(image, contract["branchRules"], body, rva, opcode_ids, contract, extents)
    object_opcode_audit = validate_object_opcode_rules(image, contract["objectOpcodeRules"], body, rva, opcode_ids, contract, extents)
    call_opcode_audit = validate_call_opcode_rules(image, contract["callOpcodeRules"], body, rva, opcode_ids, contract, extents)
    call_opcode_audit["recipeOpcodeIds"] = dict(contract["callOpcodeRules"]["opcodeIds"], **{name: opcode_ids[name] for name in ("CallExtern", "Newobj")})
    call_opcode_audit["recipeSelections"] = {name: "conditional-shared-external-caller;parent-reflectionDispatch-selector" for name in ("CallExtern", "Newobj")}
    init_constrained_audit = validate_init_constrained_rules(image, contract["initConstrainedRules"], body, rva, opcode_ids, contract, extents)
    exception_dispatch_audit = validate_exception_dispatch_rules(image, contract["exceptionDispatchRules"], body, rva, opcode_ids, contract, extents)
    string_opcode_audit = validate_string_opcode_rules(image, contract["stringOpcodeRules"], body, rva, opcode_ids, contract, extents)
    string_opcode_audit["recipeOpcodeIds"] = {"Ldstr": contract["stringOpcodeRules"]["opcodeId"]}
    static_initializer_audit = validate_static_initializer_rules(image, contract["staticInitializerRules"], contract, extents)
    anonymous_loader_audit = validate_anonymous_loader_rules(image, contract["anonymousLoaderRules"], loader_body, loader_rva, contract, extents)
    floating_remainder_audit = validate_floating_remainder_rules(image, contract["floatingRemainderRules"], contract, extents)
    stack_construction_audit = validate_stack_construction_rules(image, contract["stackConstructionRules"], contract, extents)
    reference_helper_audit = validate_reference_helper_rules(image, contract["referenceHelperRules"], contract, extents)
    instance_alias_audit = validate_instance_alias_rules(contract["instanceAliasRules"], contract["instanceFieldRules"], instance_field_audit)
    instance_byte_alias_audit = validate_instance_byte_alias_rules(contract["instanceByteAliasRules"], contract["instanceFieldRules"], instance_field_audit)
    call_zero_audit = validate_call_zero_rules(image, contract["callZeroRules"], contract)
    call_push_audit = validate_call_push_rules(image, contract["callPushRules"], contract, extents)
    runtime_exception_audit = validate_runtime_exception_rules(image, contract["runtimeExceptionRules"], contract, extents)
    exception_funclet_audit = validate_exception_funclet_rules(image, contract["exceptionFuncletRules"], contract, extents)
    entry_frame_audit = validate_entry_frame_rules(image, contract["entryFrameRules"], body, rva, opcode_ids, contract, extents)
    anonymous_info_constructor_audit = validate_anonymous_info_constructor_rules(image, contract["anonymousInfoConstructorRules"], contract, extents)
    reflection_invoker_constructor_audit = validate_reflection_invoker_constructor_rules(image, contract["reflectionInvokerConstructorRules"], contract, extents)
    reflection_invoker_audit = validate_reflection_invoker_rules(image, contract["reflectionInvokerRules"], contract, extents)
    bridge_dispatch_audit = validate_bridge_dispatch_rules(image, contract["bridgeDispatchRules"], contract, extents)
    call_reference_update_audit = validate_call_reference_update_rules(image, contract["callReferenceUpdateRules"], contract, extents)
    reflection_cleanup_audit = validate_reflection_cleanup_rules(image, contract["reflectionCleanupRules"], contract, extents)
    call_scalar_audit = validate_call_scalar_rules(image, contract["callScalarRules"], contract, extents)
    generic_reference_get_audit = validate_generic_reference_get_rules(image, contract["genericReferenceGetRules"], contract, extents)
    generic_scalar_get_audit = validate_generic_scalar_get_rules(image, contract["genericScalarGetRules"], contract, extents)
    generic_adjustor_audit = validate_generic_adjustor_rules(image, contract["genericAdjustorRules"], contract, extents)
    anonymous_virtual_audit = validate_anonymous_virtual_rules(image, contract["anonymousVirtualRules"], contract, extents)
    vm_construction_audit = validate_vm_construction_rules(image, contract["vmConstructionRules"], contract, extents)
    vm_table_accessor_audit = validate_vm_table_accessor_rules(image, contract["vmTableAccessorRules"], contract, extents)
    call_opcode_audit["callZeroRulesRef"] = "audit.callZeroRules"
    call_push_audit["typedPushRulesRef"] = "audit.objectConversionRules"
    anonymous_storey_audit["bridgeDispatchRulesRef"] = "audit.bridgeDispatchRules"
    anonymous_storey_audit["infoConstructorRulesRef"] = "audit.anonymousInfoConstructorRules"
    reflection_audit["constructorRulesRef"] = "audit.reflectionInvokerConstructorRules"
    reflection_audit["invokeRulesRef"] = "audit.reflectionInvokerRules"
    reflection_invoker_audit["cleanupRulesRef"] = "audit.reflectionCleanupRules"
    anonymous_storey_audit["virtualRulesRef"] = "audit.anonymousVirtualRules"
    call_push_audit["scalarRulesRef"] = "audit.callScalarRules"
    generic_reference_get_audit["adjustorCellsRulesRef"] = "audit.genericAdjustorRules"
    generic_scalar_get_audit["adjustorCellsRulesRef"] = "audit.genericAdjustorRules"
    instance_alias_audit["byteOverlapRulesRef"] = "audit.instanceByteAliasRules"
    vm_construction_audit["tableAccessorRulesRef"] = "audit.vmTableAccessorRules"
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
        "delegateConstruction": delegate_audit,
        "genericDelegateFactoryRules": generic_delegate_audit,
        "genericDelegateCatalogRules": generic_catalog_audit,
        "genericDelegateBindingRules": generic_binding_audit,
        "slotCopyRules": slot_copy_audit,
        "negativeFieldRules": negative_field_audit,
        "instanceFieldRules": instance_field_audit,
        "stackReferenceRules": stack_reference_audit,
        "referenceUpdateRules": reference_update_audit,
        "slotAliasRules": slot_alias_audit,
        "chainFieldRules": chain_field_audit,
        "newFieldRules": new_field_audit,
        "objectConversionRules": object_conversion_audit,
        "referenceAddressRules": reference_address_audit,
        "dispatchRules": dispatch_audit,
        "comparisonRules": comparison_audit,
        "conversionOpcodeRules": conversion_opcode_audit,
        "anonymousStoreyRules": anonymous_storey_audit,
        "arrayRules": array_audit,
        "bitwiseRules": bitwise_audit,
        "literalControlRules": literal_control_audit,
        "arrayReferenceRules": array_reference_audit,
        "indirectOpcodeRules": indirect_opcode_audit,
        "arithmeticRules": arithmetic_audit,
        "positiveFieldRules": positive_field_audit,
        "branchRules": branch_audit,
        "objectOpcodeRules": object_opcode_audit,
        "callOpcodeRules": call_opcode_audit,
        "initConstrainedRules": init_constrained_audit,
        "exceptionDispatchRules": exception_dispatch_audit,
        "stringOpcodeRules": string_opcode_audit,
        "staticInitializerRules": static_initializer_audit,
        "anonymousLoaderRules": anonymous_loader_audit,
        "floatingRemainderRules": floating_remainder_audit,
        "stackConstructionRules": stack_construction_audit,
        "referenceHelperRules": reference_helper_audit,
        "instanceAliasRules": instance_alias_audit,
        "instanceByteAliasRules": instance_byte_alias_audit,
        "callZeroRules": call_zero_audit,
        "callPushRules": call_push_audit,
        "runtimeExceptionRules": runtime_exception_audit,
        "exceptionFuncletRules": exception_funclet_audit,
        "entryFrameRules": entry_frame_audit,
        "anonymousInfoConstructorRules": anonymous_info_constructor_audit,
        "reflectionInvokerConstructorRules": reflection_invoker_constructor_audit,
        "reflectionInvokerRules": reflection_invoker_audit,
        "bridgeDispatchRules": bridge_dispatch_audit,
        "callReferenceUpdateRules": call_reference_update_audit,
        "reflectionCleanupRules": reflection_cleanup_audit,
        "callScalarRules": call_scalar_audit,
        "genericReferenceGetRules": generic_reference_get_audit,
        "genericScalarGetRules": generic_scalar_get_audit,
        "genericAdjustorRules": generic_adjustor_audit,
        "anonymousVirtualRules": anonymous_virtual_audit,
        "vmConstructionRules": vm_construction_audit,
        "vmTableAccessorRules": vm_table_accessor_audit,
        "genericBridgeRules": generic_bridge_audit,
        "wrapperDelegateDispatch": wrapper_dispatch_audit,
        "delegateBridgeRules": delegate_bridge_audit,
        "functionPointerRules": function_pointer_audit,
        "virtualDispatchRules": virtual_dispatch_audit,
        "basicOpcodeRules": basic_audit,
        "initobjTypeOperand": initobj_audit,
        "initobjStackEffect": initobj_stack_audit,
        "constrainedTypeOperand": constrained_audit,
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
    decoded = decode_patch_opcodes(data, layout, source=source, inline_data_rules=contract["literalControlRules"])
    basic_rules = project_basic_rules(decoded, contract["basicOpcodeRules"])
    function_pointer_operands = project_function_pointer_rules(decoded, parsed, contract["functionPointerRules"])
    virtual_dispatch_operands = project_virtual_dispatch_rules(decoded, contract["virtualDispatchRules"])
    slot_copy_rules = project_slot_copy_rules(decoded, contract["slotCopyRules"])
    slot_copy_rules = project_slot_alias_rules(slot_copy_rules, contract["slotAliasRules"])
    negative_field_operands = project_negative_field_rules(decoded, contract["negativeFieldRules"])
    instance_field_operands = project_instance_field_rules(decoded, contract["instanceFieldRules"])
    instance_alias_rules = project_instance_alias_rules(decoded, contract["instanceAliasRules"])
    stack_reference_operands = project_stack_reference_rules(decoded, contract["stackReferenceRules"])
    reference_address_operands = project_reference_address_rules(decoded, contract["referenceAddressRules"])
    comparison_rules = project_comparison_rules(decoded, contract["comparisonRules"])
    array_rules = project_array_rules(decoded, contract["arrayRules"])
    bitwise_rules = project_bitwise_rules(decoded, contract["bitwiseRules"])
    literal_control_rules = project_literal_control_rules(decoded, contract["literalControlRules"])
    arithmetic_rules = project_arithmetic_rules(decoded, contract["arithmeticRules"])
    branch_rules = project_branch_rules(decoded, contract["branchRules"])
    call_opcode_rules = project_call_opcode_rules(decoded, contract["callOpcodeRules"])
    exception_dispatch_rules = project_exception_dispatch_rules(decoded, contract["exceptionDispatchRules"])
    string_opcode_rules = project_string_opcode_rules(decoded, contract["stringOpcodeRules"])
    init_constrained_rules = []
    indirect_opcode_rules = []
    positive_field_rules = []
    object_opcode_rules = []
    conversion_opcode_rules = []
    for method in decoded["methods"]:
        for ins in method["instructions"]:
            projected = project_conversion_opcode_rules([{
                "opcode": ins["name"], "opcodeId": ins["opcode"],
                "operand": ins["operandUnsigned"], "operandSigned": ins["operandSigned"],
            }], contract["conversionOpcodeRules"])
            conversion_opcode_rules.extend(dict(row, vmMethodIndex=method["index"], instructionIndex=ins["index"], offset=ins["offset"]) for row in projected)
            projected_indirect = project_indirect_opcode_rules([{
                "opcode": ins["name"], "opcodeId": ins["opcode"],
                "operand": ins["operandUnsigned"], "operandSigned": ins["operandSigned"],
            }], contract["indirectOpcodeRules"])
            indirect_opcode_rules.extend(dict(row, vmMethodIndex=method["index"], instructionIndex=ins["index"], offset=ins["offset"]) for row in projected_indirect)
            authored_instruction = [{"opcode": ins["name"], "opcodeId": ins["opcode"], "operand": ins["operandUnsigned"], "operandSigned": ins["operandSigned"]}]
            positive_field_rules.extend(dict(row, vmMethodIndex=method["index"], instructionIndex=ins["index"], offset=ins["offset"]) for row in project_positive_field_rules(authored_instruction, contract["positiveFieldRules"]))
            object_opcode_rules.extend(dict(row, vmMethodIndex=method["index"], instructionIndex=ins["index"], offset=ins["offset"]) for row in project_object_opcode_rules(authored_instruction, contract["objectOpcodeRules"]))
            init_constrained_rules.extend(dict(row, vmMethodIndex=method["index"], instructionIndex=ins["index"], offset=ins["offset"]) for row in project_init_constrained_rules(authored_instruction, contract["initConstrainedRules"]))
    exception_handlers = _project_exception_handlers(data, parsed, contract)
    call_claims = {row["opcode"]: row for row in contract["callClaims"]}
    branch_claims = {row["opcode"]: row for row in contract["branchClaims"]}
    table_claims = {row["opcode"]: row for row in contract["tableOperandClaims"]}
    frame_claims = {row["opcode"]: row for row in contract["frameSlotClaims"]}
    type_claims = {
        contract[key]["opcode"]: contract[key]
        for key in ("initobjTypeOperand", "constrainedTypeOperand")
    }
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
    type_operands = []
    covered_names = (set(call_claims) | set(branch_claims) | set(table_claims) | set(frame_claims)
                     | set(type_claims) | {header_claim["opcode"], return_claim["opcode"],
                                          exception_control["leave"]["opcode"], exception_control["endfinally"]["opcode"]}
                     | {row["opcode"] for row in contract["basicOpcodeRules"]["rules"]}
                     | {row["opcode"] for row in contract["functionPointerRules"]["rules"]}
                     | {row["opcode"] for row in contract["slotCopyRules"]["rules"]}
                     | {row["opcode"] for row in contract["instanceFieldRules"]["rules"]}
                     | {row["opcode"] for row in contract["referenceAddressRules"]["rules"]}
                     | {row["opcode"] for row in contract["comparisonRules"]["rules"]}
                     | set(contract["conversionOpcodeRules"]["rules"])
                     | set(contract["dispatchRules"]["defaultOpcodes"]) | {"Newanon", "InlineData"}
                     | {row["opcode"] for row in contract["arrayRules"]["rules"]}
                     | {row["opcode"] for row in contract["bitwiseRules"]["rules"]}
                     | {row["opcode"] for row in contract["literalControlRules"]["rules"]}
                     | set(contract["indirectOpcodeRules"]["rules"])
                     | {row["opcode"] for row in contract["arithmeticRules"]["rules"]}
                     | set(contract["positiveFieldRules"]["rules"])
                     | {row["opcode"] for row in contract["branchRules"]["rules"]}
                     | set(contract["objectOpcodeRules"]["rules"])
                     | set(contract["callOpcodeRules"]["opcodeIds"])
                     | {row["opcode"] for row in contract["exceptionDispatchRules"]["rules"]}
                     | {contract["stringOpcodeRules"]["opcode"]}
                     | set(contract["initConstrainedRules"]["rules"]))
    unprojected_counts: dict[str, int] = {}
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
            if instruction["name"] not in covered_names:
                name = instruction["name"]
                unprojected_counts[name] = unprojected_counts.get(name, 0) + 1
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
            if instruction["name"] in type_claims:
                type_index = instruction["operandSigned"]
                type_rows = parsed["externTypes"]["records"]
                in_range = 0 <= type_index < len(type_rows)
                type_row = type_rows[type_index] if in_range else None
                stack_effect = None
                if instruction["name"] == contract["constrainedTypeOperand"]["opcode"] and in_range:
                    instruction_index = instruction["index"]
                    if not 0 < instruction_index < method_size:
                        raise VMOperandEvidenceError(
                            f"{source}: Constrained previous instruction outside VM method "
                            f"{method['index']} at {instruction_index}"
                        )
                    previous = method["instructions"][instruction_index - 1]
                    if previous["index"] != instruction_index - 1:
                        raise VMOperandEvidenceError(
                            f"{source}: Constrained previous instruction index drift "
                            f"in VM method {method['index']}"
                        )
                    from_top = previous["operandSigned"] + 1
                    stack_effect = {
                        "previousInstructionIndex": previous["index"],
                        "previousInstructionFileOffset": previous["offset"],
                        "previousOpcode": previous["name"],
                        "previousOperandSigned": previous["operandSigned"],
                        "selectedSlotOffsetFromTop": from_top,
                        "slotRelativePosition": (
                            "at-or-below-top" if from_top > 0 else "above-top"
                        ),
                        "runtimeStackDepth": "unobserved",
                        "normalReturnEffect": (
                            "ToObject-return-stored-in-managedStack; "
                            "selected-Value-becomes-Object-index"
                        ),
                        "evidenceBoundary": "conditional",
                        "executionBoundary": "unobserved",
                    }
                elif instruction["name"] == contract["initobjTypeOperand"]["opcode"] and in_range:
                    instruction_index = instruction["index"]
                    if instruction_index > 0:
                        previous = method["instructions"][instruction_index - 1]
                        if previous["index"] != instruction_index - 1:
                            raise VMOperandEvidenceError(
                                f"{source}: Initobj previous instruction index drift "
                                f"in VM method {method['index']}"
                            )
                        local_slot = previous["operandSigned"]
                        if (
                            previous["name"] == contract["initobjStackEffect"]["addressProducer"]
                            and header_status == "direct"
                            and 0 <= local_slot < local_count
                        ):
                            stack_effect = {
                                "addressProducerInstructionIndex": previous["index"],
                                "addressProducerFileOffset": previous["offset"],
                                "addressProducerOpcode": previous["name"],
                                "destinationDomain": "local",
                                "destinationSlotIndex": local_slot,
                                "normalReturnEffect": (
                                    "Activator.CreateInstance(Type) result passed through "
                                    "UpdateReference StackReference branch to PushObject "
                                    "at the selected local slot"
                                ),
                                "evidenceBoundary": "conditional",
                                "executionBoundary": "unobserved",
                            }
                type_operands.append({
                    "vmMethodIndex": method["index"],
                    "instructionIndex": instruction["index"],
                    "offset": instruction["offset"],
                    "opcode": instruction["name"],
                    "typeIndex": type_index,
                    "runtimeTable": type_claims[instruction["name"]]["runtimeField"],
                    "fileTable": type_claims[instruction["name"]]["fileTable"],
                    "fileTableCount": len(type_rows),
                    "fileTableJoin": "direct" if in_range else "out-of-range",
                    "declaredFileRow": (
                        {
                            "index": type_index,
                            "kind": "extern-type",
                            "recordOffset": type_row["offset"],
                            "typeName": type_row["value"],
                        } if type_row is not None else None
                    ),
                    "stackEffect": stack_effect,
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
                "conditionalDelegateConstruction": (
                    {"selectedWhen": contract["delegateConstruction"]["selection"],
                     "inputSlots": contract["delegateConstruction"]["inputSlots"],
                     "outputSlots": contract["delegateConstruction"]["outputSlots"],
                     "upper16OperandRole": "unused-by-selected-delegate-path",
                     "resultTag": contract["delegateConstruction"]["resultTag"],
                     "evidenceBoundary": "conditional", "executionBoundary": "unobserved"}
                    if instruction["name"] == "Newobj" else None
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
        "typeOperandCount": len(type_operands),
        "calls": calls,
        "branches": branches,
        "tableOperands": table_operands,
        "frameHeaders": frame_headers,
        "frameSlots": frame_slots,
        "returns": returns,
        "exceptionHandlers": exception_handlers,
        "leaves": leaves,
        "endfinallys": endfinallys,
        "typeOperands": type_operands,
        "basicOpcodeRules": basic_rules,
        "basicOpcodeRuleCount": len(basic_rules),
        "functionPointerOperands": function_pointer_operands,
        "functionPointerOperandCount": len(function_pointer_operands),
        "virtualDispatchOperands": virtual_dispatch_operands,
        "virtualDispatchOperandCount": len(virtual_dispatch_operands),
        "slotCopyRules": slot_copy_rules,
        "slotCopyRuleCount": len(slot_copy_rules),
        "negativeFieldOperands": negative_field_operands,
        "negativeFieldOperandCount": len(negative_field_operands),
        "instanceFieldOperands": instance_field_operands,
        "instanceFieldOperandCount": len(instance_field_operands),
        "instanceAliasRules": instance_alias_rules,
        "instanceAliasRuleCount": len(instance_alias_rules),
        "stackReferenceOperands": stack_reference_operands,
        "stackReferenceOperandCount": len(stack_reference_operands),
        "referenceAddressOperands": reference_address_operands,
        "referenceAddressOperandCount": len(reference_address_operands),
        "comparisonRules": comparison_rules,
        "comparisonRuleCount": len(comparison_rules),
        "conversionOpcodeRules": conversion_opcode_rules,
        "conversionOpcodeRuleCount": len(conversion_opcode_rules),
        "arrayRules": array_rules,
        "arrayRuleCount": len(array_rules),
        "bitwiseRules": bitwise_rules,
        "bitwiseRuleCount": len(bitwise_rules),
        "literalControlRules": literal_control_rules,
        "literalControlRuleCount": len(literal_control_rules),
        "indirectOpcodeRules": indirect_opcode_rules,
        "indirectOpcodeRuleCount": len(indirect_opcode_rules),
        "arithmeticRules": arithmetic_rules,
        "arithmeticRuleCount": len(arithmetic_rules),
        "positiveFieldRules": positive_field_rules,
        "positiveFieldRuleCount": len(positive_field_rules),
        "branchRules": branch_rules,
        "branchRuleCount": len(branch_rules),
        "objectOpcodeRules": object_opcode_rules,
        "objectOpcodeRuleCount": len(object_opcode_rules),
        "callOpcodeRules": call_opcode_rules,
        "callOpcodeRuleCount": len(call_opcode_rules),
        "exceptionDispatchRules": exception_dispatch_rules,
        "exceptionDispatchRuleCount": len(exception_dispatch_rules),
        "stringOpcodeRules": string_opcode_rules,
        "stringOpcodeRuleCount": len(string_opcode_rules),
        "initConstrainedRules": init_constrained_rules,
        "initConstrainedRuleCount": len(init_constrained_rules),
        "inlineDataRecordCount": decoded["inlineDataRecordCount"],
        "instructionCount": sum(len(row["instructions"]) for row in decoded["methods"]),
        "unprojectedOpcodeCounts": dict(sorted(unprojected_counts.items())),
        "projectionBoundary": "Selected operand joins and conditional basic effects; an empty unprojected opcode inventory does not prove complete stack semantics, runtime validity, or execution.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--outer-summary", type=Path)
    parser.add_argument("--outer-ledger", type=Path)
    parser.add_argument("--expected-input-set-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        outer_values = (
            args.outer_summary, args.outer_ledger, args.expected_input_set_sha256,
        )
        if any(value is not None for value in outer_values) and not all(
            value is not None for value in outer_values
        ):
            raise VMOperandEvidenceError(
                "IFix outer gate requires --outer-summary, --outer-ledger, "
                "and --expected-input-set-sha256 together"
            )
        current_vfs_join = (
            _validate_current_vfs_inputs(
                args.input, args.outer_summary, args.outer_ledger,
                args.expected_input_set_sha256,
            ) if args.outer_summary is not None else None
        )
        contract, layout, audit = validate_vm_operand_contract(
            args.contract, gameassembly=args.gameassembly, metadata_path=args.metadata
        )
        files = [
            project_vm_operands(path.read_bytes(), layout, contract, source=str(path))
            for path in args.input
        ]
        rule_inventory = build_rule_inventory(contract, layout, audit)
    except (VMOperandEvidenceError, OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"ifix-vm-operands: {error}", file=sys.stderr)
        return 1
    report = {
        "schema": "endfield-ifix-vm-operand-audit-v33",
        "status": "validated_selected_native_loader_and_consumer",
        "audit": audit,
        "ruleInventory": rule_inventory,
        "currentVfsJoin": current_vfs_join,
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
        "typeOperandCount": sum(row["typeOperandCount"] for row in files),
        "basicOpcodeRuleCount": sum(row["basicOpcodeRuleCount"] for row in files),
        "functionPointerOperandCount": sum(row["functionPointerOperandCount"] for row in files),
        "virtualDispatchOperandCount": sum(row["virtualDispatchOperandCount"] for row in files),
        "slotCopyRuleCount": sum(row["slotCopyRuleCount"] for row in files),
        "negativeFieldOperandCount": sum(row["negativeFieldOperandCount"] for row in files),
        "instanceFieldOperandCount": sum(row["instanceFieldOperandCount"] for row in files),
        "instanceAliasRuleCount": sum(row["instanceAliasRuleCount"] for row in files),
        "stackReferenceOperandCount": sum(row["stackReferenceOperandCount"] for row in files),
        "referenceAddressOperandCount": sum(row["referenceAddressOperandCount"] for row in files),
        "comparisonRuleCount": sum(row["comparisonRuleCount"] for row in files),
        "conversionOpcodeRuleCount": sum(row["conversionOpcodeRuleCount"] for row in files),
        "arrayRuleCount": sum(row["arrayRuleCount"] for row in files),
        "bitwiseRuleCount": sum(row["bitwiseRuleCount"] for row in files),
        "literalControlRuleCount": sum(row["literalControlRuleCount"] for row in files),
        "indirectOpcodeRuleCount": sum(row["indirectOpcodeRuleCount"] for row in files),
        "arithmeticRuleCount": sum(row["arithmeticRuleCount"] for row in files),
        "positiveFieldRuleCount": sum(row["positiveFieldRuleCount"] for row in files),
        "branchRuleCount": sum(row["branchRuleCount"] for row in files),
        "objectOpcodeRuleCount": sum(row["objectOpcodeRuleCount"] for row in files),
        "callOpcodeRuleCount": sum(row["callOpcodeRuleCount"] for row in files),
        "exceptionDispatchRuleCount": sum(row["exceptionDispatchRuleCount"] for row in files),
        "stringOpcodeRuleCount": sum(row["stringOpcodeRuleCount"] for row in files),
        "initConstrainedRuleCount": sum(row["initConstrainedRuleCount"] for row in files),
        "inlineDataRecordCount": sum(row["inlineDataRecordCount"] for row in files),
        "instructionCount": sum(row["instructionCount"] for row in files),
        "projectionBoundary": "Retained patch-byte projections under selected native rules; no runtime receipt or complete-VM claim.",
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
        f"{report['leaveCount']} leaves, {report['endfinallyCount']} endfinallys, "
        f"{report['typeOperandCount']} type operands, "
        f"{report['basicOpcodeRuleCount']} basic opcode rules, "
        f"{report['functionPointerOperandCount']} method-value operands, "
        f"{report['virtualDispatchOperandCount']} conditional override operands; "
        f"{report['slotCopyRuleCount']} conditional slot copies, "
        f"{report['negativeFieldOperandCount']} negative static-field operands; "
        f"{report['instanceFieldOperandCount']} negative instance-field operands, "
        f"{report['stackReferenceOperandCount']} reference producer/consumer projections, "
        f"{report['referenceAddressOperandCount']} reference-address projections; "
        f"{report['comparisonRuleCount']} comparisons; {report['conversionOpcodeRuleCount']} other conversions; "
        f"{report['arrayRuleCount']} arrays; {report['bitwiseRuleCount']} bitwise/unary; "
        f"{report['literalControlRuleCount']} literal/control rules, {report['inlineDataRecordCount']} inline payload records; "
        f"{report['indirectOpcodeRuleCount']} indirect, {report['arithmeticRuleCount']} arithmetic, "
        f"{report['positiveFieldRuleCount']} positive fields, {report['objectOpcodeRuleCount']} object/type, "
        f"{report['branchRuleCount']} branch recipes; "
        f"{report['callOpcodeRuleCount']} call/return, {report['exceptionDispatchRuleCount']} exception, "
        f"{report['stringOpcodeRuleCount']} string, {report['initConstrainedRuleCount']} init/constrained recipes; "
        f"unprojected opcodes={[row['unprojectedOpcodeCounts'] for row in files]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
