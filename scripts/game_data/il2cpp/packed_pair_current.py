"""Conditional interface-current producers for closed KeyValuePair returns.

Complete helper grammars prove matching-interface return copies. A separate
String/Int32 caller grammar proves its destination argument transfer. Neither
proves fallback lookup, enumerator construction, loops or live map contents.
Usage resolution and a valid receiver/interface table are explicit conditions.
No build-specific address, native hash or generic registration index is stored.
"""
from __future__ import annotations

import re
from typing import Any

from .context import (generic_type_carrier, relative_branch_target,
                      rip_qword_load_target, type_parameter_owner, unresolved_usage_index)
from .packed_pair import passed_context, prove_string_int_split
from .protocol import runtime_type_name


def _match(raw: bytes, program: bytes, variable: set[int], label: str) -> None:
    if len(raw) != len(program):
        raise ValueError(f"packed_current.{label}: expected={len(program)} bytes actual={len(raw)}")
    for offset, (actual, expected) in enumerate(zip(raw, program)):
        if offset not in variable and actual != expected:
            raise ValueError(f"packed_current.{label}: offset={offset} expected=0x{expected:02x} actual=0x{actual:02x}")


def prove_current_helper(raw: bytes, pointer: int) -> dict[str, Any]:
    """Recognize every helper byte; only relocation operands remain variable.

    Fast selection searches class.interfaceOffsets for the supplied interface,
    reads its slot-zero InvokeData and invokes it with the original R9 receiver.
    The other path calls a lookup helper whose semantics remain unproved.
    """
    if len(raw) in (178, 182):
        return _alternate_current_helper(raw, pointer)
    program = bytes.fromhex(
        "48895c240848896c24104889742418574883ec30498b39488be9488b1d00000000"
        "488bcf498bf1e800000000440fb7873001000033c066413bc0731c488b97b0000000"
        "0fb7c84803c948391cca741966ffc066413bc072eb4533c0488bd3488bcee800000000"
        "eb160fb7c84803c9486344ca084883c01448c1e0044803c74c8b08488d4c2420"
        "4c8b4008488bd641ffd1488b5c2440488b7424500f1000488bc50f114500"
        "488b6c24484883c4305fc3")
    _match(raw, program, set(range(29, 33)) | set(range(40, 44)) | set(range(98, 102)), "helper_program")
    return {"typeUsageCellVa": rip_qword_load_target(raw[26:33], pointer+26, source="packed current helper"),
            "interfaceSlot": 0, "receiverRegister": "r9", "returnBufferRegister": "rcx",
            "copiedReturnBytes": 16, "checkedBytes": len(raw),
            "unprovedInitializationCallVa": relative_branch_target(raw[39:44], pointer+39, source="packed current helper"),
            "unprovedFallbackLookupCallVa": relative_branch_target(raw[97:102], pointer+97, source="packed current helper")}


def _alternate_current_helper(raw: bytes, pointer: int) -> dict[str, Any]:
    """Complete RSI-interface variants, including their owned post-RET tail."""
    if len(raw) == 182:
        program = bytes.fromhex(
            "48895c240848896c24104889742418574883ec30498b19488be9488b3500000000"
            "488bcb498bf9e800000000440fb7833001000033d266413bd0731c488b8bb0000000"
            "0fb7c24803c0483934c1744866ffc266413bd072eb4533c0488bd6488bcfe800000000"
            "4c8b08488d4c24204c8b4008488bd741ffd1488b5c2440488b7424500f1000488bc5"
            "0f114500488b6c24484883c4305fc3488b83b00000000fb7ca4803c9486344c808"
            "4883c01448c1e0044803c3ebb0")
        variable = set(range(29, 33)) | set(range(40, 44)) | set(range(98, 102))
        initialization, fallback = 39, 97
        source = {"typeUsageCellVa": rip_qword_load_target(raw[26:33], pointer+26, source="packed current helper")}
    else:
        program = bytes.fromhex(
            "48895c240848896c24104889742418574883ec30498b19488be9488bcb498bf9498bf0"
            "e800000000440fb7833001000033d266413bd0731c488b8bb00000000fb7c24803c0"
            "483934c1744866ffc266413bd072eb4533c0488bd6488bcfe8000000004c8b08"
            "488d4c24204c8b4008488bd741ffd1488b5c2440488b7424500f1000488bc50f114500"
            "488b6c24484883c4305fc3488b83b00000000fb7ca4803c9486344c8084883c014"
            "48c1e0044803c3ebb0")
        variable = set(range(36, 40)) | set(range(94, 98))
        initialization, fallback = 35, 93
        source = {"typeArgumentRegister": "r8"}
    _match(raw, program, variable, "helper_program")
    return {**source, "interfaceSlot": 0, "receiverRegister": "r9", "returnBufferRegister": "rcx",
            "copiedReturnBytes": 16, "checkedBytes": len(raw),
            "unprovedInitializationCallVa": relative_branch_target(raw[initialization:initialization+5], pointer+initialization, source="packed current helper"),
            "unprovedFallbackLookupCallVa": relative_branch_target(raw[fallback:fallback+5], pointer+fallback, source="packed current helper")}


def prove_current_call_window(raw: bytes, pointer: int) -> dict[str, Any]:
    """Prove producer return -> XMM1 -> selected Add in one complete window."""
    program = bytes.fromhex(
        "4c8b4c24004d85c90f8400000000488d4c2400e8000000000f1008498b4c2400"
        "4885c90f84000000004c8b0d00000000"
        "660f6fc1660f73d80866410f7ec066480f7ecae800000000")
    variable = {4, 18, 31} | set(range(10, 14)) | set(range(20, 24)) | set(range(37, 41)) | set(range(44, 48)) | set(range(68, 72))
    _match(raw, program, variable, "caller_program")
    receiver_slot, return_slot, destination_offset = raw[4], raw[18], raw[31]
    if (not 0x20 <= receiver_slot <= 0x77 or not 0x20 <= return_slot <= 0x6f or
            max(receiver_slot, return_slot) < min(receiver_slot+8, return_slot+16) or not 0 < destination_offset < 0x80):
        raise ValueError("packed_current.caller_storage: bounded nonoverlapping stack receiver/return buffer and positive destination field required")
    prove_string_int_split(raw[48:67])
    return {"helperVa": relative_branch_target(raw[19:24], pointer+19, source="packed current caller"),
            "addVa": relative_branch_target(raw[67:72], pointer+67, source="packed current caller"),
            "addUsageCellVa": rip_qword_load_target(raw[41:48], pointer+41, source="packed current caller"),
            "receiverStackOffset": receiver_slot, "returnStackOffset": return_slot,
            "destinationFieldOffset": destination_offset, "checkedBytes": len(raw)}


def _generic(index: Any, pointer: int, *, value_type: bool = False) -> tuple[Any, tuple[Any, ...]]:
    pe, image = index.pe, index.image
    raw = pe.bytes_at_va(pointer, 16)
    carrier = int.from_bytes(raw[:8], "little")
    window = pe.bytes_at_va(carrier, 32)
    base = int.from_bytes(window[:8], "little")
    selection = generic_type_carrier(raw, window, pe.bytes_at_va(base, 16), type_pointer=pointer,
                                    type_count=len(index.metadata.types), source=str(image.gameassembly),
                                    base_type_tag=0x11 if value_type else 0x12)
    instance = image.instantiations.resolve_pointer(selection["classInstantiationPointerVa"])
    return index.metadata.types[selection["baseDefinitionIndex"]], instance.arguments


def selected_current_type(index: Any, cell: int) -> dict[str, Any]:
    """Bind a closed IEnumerator<KeyValuePair<K,V>> return, independent of ABI.

    This type proof alone admits no pair size, field layout or argument program.
    The transfer checker must compare the actual pair with its passed context.
    """
    pe, image, metadata = index.pe, index.image, index.metadata
    type_index = unresolved_usage_index(pe.bytes_at_va(cell, 8), image.registration["typesCount"],
                                       tag=1, source=str(image.gameassembly), offset=cell)
    table = int(image.registration["types"], 16)
    owner, arguments = _generic(index, pe.u64_at_va(table + type_index*8))
    if (metadata.type_full_name(owner) != "System.Collections.Generic.IEnumerator`1" or
            not owner.flags & 0x20 or len(arguments) != 1):
        raise ValueError("packed_current.interface_type: expected closed IEnumerator<T> interface with one argument")
    getters = [method for method in metadata.methods[owner.method_start:owner.method_start+owner.method_count]
               if metadata.string(method.name_index) == "get_Current"]
    if (len(getters) != 1 or getters[0].declaring_type != owner.index or getters[0].parameter_count != 0 or
            getters[0].flags & 0x10 or not getters[0].flags & 0x40 or getters[0].slot != 0):
        raise ValueError("packed_current.current_slot: expected unique instance virtual zero-parameter get_Current at slot zero")
    getter = getters[0]
    return_raw = pe.bytes_at_va(pe.u64_at_va(table+getter.return_type*8), 16)
    if return_raw[10] != 0x13:
        raise ValueError("packed_current.return_var: expected interface return VAR")
    substitution = type_parameter_owner(metadata.buf, int.from_bytes(return_raw[:8], "little"),
        [row.generic_container_index for row in metadata.types], source=str(image.metadata_path))
    if substitution["typeIndex"] != owner.index or substitution["ordinal"] != 0:
        raise ValueError("packed_current.return_owner: return VAR must belong reciprocally to selected interface argument zero")
    pair, parts = _generic(index, arguments[0].type_pointer_va, value_type=True)
    names = [runtime_type_name(pe, metadata, argument.type_pointer_va) for argument in parts]
    if (metadata.type_full_name(pair) != "System.Collections.Generic.KeyValuePair`2" or len(names) != 2 or
            any(not name or name.startswith(("<", "VAR[", "MVAR[")) for name in names)):
        raise ValueError(f"packed_current.pair_type: expected closed KeyValuePair<K,V> actual={metadata.type_full_name(pair)} {names}")
    return {"interface": metadata.type_full_name(owner), "getter": "get_Current", "slot": getter.slot,
            "returnType": "System.Collections.Generic.KeyValuePair`2<" + ",".join(names) + ">",
            "classArguments": names, "returnVar": substitution,
            "storageLayoutProved": False, "argumentTransferProved": False}


def check_current_pair_fast_path(index: Any, body: Any, spec: Any) -> str | None:
    """Only a complete owned caller/helper admits this conditional claim."""
    if (not isinstance(spec, dict) or set(spec) != {"call", "classArguments"} or
            spec["call"] != "System.Collections.Generic.Dictionary`2.Add" or spec["classArguments"] != ["string", "int"]):
        return "packed_current.claim_shape: requires selected Dictionary.Add [string,int]"
    failures = []
    for row in body.rows:
        match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
        if not match or spec["call"] not in index.names_of(int(match[1], 16)):
            continue
        call, target = int(row["va"], 16), int(match[1], 16)
        try:
            if call-67 < body.pointer or call+5 > body.pointer+body.size:
                raise ValueError("packed_current.caller_owner: window escapes .pdata body")
            flow = prove_current_call_window(index.pe.bytes_at_va(call-67, 72), call-67)
            if flow["addVa"] != target:
                raise ValueError("packed_current.add_target: raw direct target differs from decoded call")
            context = passed_context(index, flow["addUsageCellVa"], target)
            if context["symbol"] != spec["call"] or context["classArguments"] != spec["classArguments"]:
                raise ValueError("packed_current.add_context: exact passed String/Int32 MethodSpec required")
            helper = flow["helperVa"]
            end = index.extents.get(helper)
            if end is None or end-helper != 175:
                raise ValueError(f"packed_current.helper_owner: expected .pdata 175-byte extent actual={None if end is None else end-helper}")
            dispatch = prove_current_helper(index.pe.bytes_at_va(helper, 175), helper)
            selected = selected_current_type(index, dispatch["typeUsageCellVa"])
            if selected["classArguments"] != context["classArguments"]:
                raise ValueError(f"packed_current.pair_type: getter return {selected['classArguments']} differs from passed Add {context['classArguments']}")
            return None
        except (ValueError, OSError, KeyError, IndexError, AttributeError) as exc:
            failures.append(str(exc)[:400])
    return "packed_current.fast_path: " + ("; ".join(failures[:3]) if failures else "no owned selected Add")


def current_pair_helpers(index: Any, body: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Bind owned current-helper return reads, without claiming destination ABI."""
    cases, failures = [], []
    for row in body.rows:
        match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
        if not match:
            continue
        call, target = int(row["va"], 16), int(match[1], 16)
        try:
            if call+8 > body.pointer+body.size:
                continue
            if index.pe.bytes_at_va(call+5, 3) not in (b"\x0f\x10\x00", b"\x0f\x10\x08"):
                continue
            if call < body.pointer or relative_branch_target(index.pe.bytes_at_va(call, 5), call, source="current caller") != target:
                raise ValueError("packed_current.caller_owner: raw call must match inside its owning body")
            end = index.extents.get(target)
            if end is None or end-target not in (175, 178, 182):
                raise ValueError(f"packed_current.helper_owner: unsupported owned helper size {None if end is None else end-target}")
            dispatch = prove_current_helper(index.pe.bytes_at_va(target, end-target), target)
            cell = dispatch.get("typeUsageCellVa")
            if cell is None:
                if call-15 < body.pointer:
                    raise ValueError("packed_current.type_argument: external TypeInfo load escapes caller")
                window = index.pe.bytes_at_va(call-15, 15)
                if window[:3] != b"\x4c\x8b\x05" or window[7:11] != b"\x48\x8d\x8c\x24":
                    raise ValueError("packed_current.type_argument: adjacent R8 RIP load and RCX stack-return-buffer LEA required")
                offset = int.from_bytes(window[11:15], "little", signed=True)
                if not 0x20 <= offset <= 1024*1024:
                    raise ValueError("packed_current.return_buffer: external caller must select bounded outgoing stack storage")
                cell = rip_qword_load_target(window[:7], call-15, source="current caller")
            selected = selected_current_type(index, cell)
            cases.append({"callOffset": call-body.pointer, "helperVa": hex(target), "helperBytes": end-target,
                          "dispatch": dispatch, "typeBinding": selected,
                          "completeLoopProved": False, "destinationTransferProved": False})
        except (ValueError, OSError, KeyError, IndexError, AttributeError) as exc:
            failures.append(f"offset={call-body.pointer}: {str(exc)[:350]}")
    return cases, failures


def check_pair_current_helpers(index: Any, body: Any, spec: Any) -> str | None:
    """Require each declared closed pair, never promote a type-only match."""
    pairs = spec.get("classArguments") if isinstance(spec, dict) else None
    if (not isinstance(spec, dict) or set(spec) != {"classArguments"} or not isinstance(pairs, list) or
            not 0 < len(pairs) <= 64 or any(not isinstance(pair, list) or len(pair) != 2 or
                any(not isinstance(name, str) or not 0 < len(name) <= 512 for name in pair) for pair in pairs) or
            len({tuple(pair) for pair in pairs}) != len(pairs)):
        return "packed_current.helpers_claim_shape: distinct closed [K,V] pairs required"
    cases, failures = current_pair_helpers(index, body)
    found = {tuple(row["typeBinding"]["classArguments"]) for row in cases}
    missing = [pair for pair in pairs if tuple(pair) not in found]
    return None if not missing else f"packed_current.helpers_missing: expected pairs={missing}; checks={failures[:3]}"
