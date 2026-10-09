"""Prove a bounded IL2CPP virtual-assignment optimization, without live claims.

The selected slot and implementation come from metadata, not a recorded RVA.
This checks a narrow Win64 register pattern and named nongeneric base fields.
It does not interpret generic data offsets or prove a runtime branch or cast.
"""
from __future__ import annotations

import re
from typing import Any

from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.protocol import runtime_type_name


def _adjacent(rows: list[dict[str, Any]]) -> bool:
    try:
        return all(int(left["va"], 0) + len(bytes.fromhex(left["bytes"]))
                   == int(right["va"], 0) for left, right in zip(rows, rows[1:]))
    except (KeyError, TypeError, ValueError):
        return False


def _implementation_pointer(index: Any, spec: dict[str, Any]) -> int:
    """Resolve the declared signature and unique closed generic registration."""
    from scripts.game_data.il2cpp.body_claims import ClaimError
    metadata, image = index.metadata, index.image
    owner = index.types[spec["type"]]
    methods = [method for method in metadata.methods_for(owner)
               if metadata.string(method.name_index) == spec["method"]]
    if len(methods) != 1:
        raise ClaimError("virtual assignment implementation is missing or overloaded")
    method = methods[0]
    registration = image.registration

    def type_name(type_index: int) -> str:
        if not 0 <= type_index < registration["typesCount"]:
            raise ClaimError("virtual assignment signature type index outside native table")
        pointer = image.pe.u64_at_va(int(registration["types"], 16) + 8 * type_index)
        if not pointer:
            raise ClaimError("virtual assignment signature native type missing")
        return runtime_type_name(image.pe, metadata, pointer)

    actual = [type_name(parameter.type_index) for parameter in metadata.parameters_for(method)]
    if (actual != spec["parameters"] or type_name(method.return_type) != "void"
            or method.flags & 0x10 or image.method_pointer_va(method)):
        raise ClaimError(f"virtual assignment implementation signature/static/normal-entry drift: {actual!r}")
    try:
        return GenericEntries(image).resolve(method.index, spec["classArguments"], [])["pointer"]
    except ValueError as exc:
        raise ClaimError(f"virtual assignment implementation registration: {exc}") from exc


def check_virtual_assignment(index: Any, body: Any, spec: dict[str, Any], *,
                             proof: dict[str, Any] | None = None) -> str | None:
    """Check both static dispatch sides; return the first bounded diagnostic."""
    from scripts.game_data.il2cpp.body_claims import (
        MAX_FOLLOWED_BYTES, _parameter_aliases_before_call, _virtual_method_slot,
        _writes_register,
    )
    if proof is not None:
        proof.clear()
    slot = _virtual_method_slot(index, spec["base"])
    implementation = spec["implementation"]
    symbol = f"{implementation['type']}.{implementation['method']}"
    if _virtual_method_slot(index, symbol) != slot:
        return f"{symbol}: assignment slot differs from {spec['base']} slot {slot}"
    selected_pointer = _implementation_pointer(index, implementation)
    # IL2CPP Win64 VirtualInvokeData: class header 0x140, pointer pair 16 bytes.
    function_offset = 0x140 + 16 * slot
    environment = index.field_offset(spec["environmentField"])
    result = index.field_offset(spec["resultField"])
    state = index.field_offset(spec["stateField"])
    if any(not 0 < offset <= 0x100000 for offset in (environment, result, state)):
        return f"{body.symbol}: assignment base field offset unavailable"
    failures: list[str] = []
    matches: set[int] = set()
    retained: dict[int, dict[str, Any]] = {}
    for call_at, call in enumerate(body.rows):
        target = re.fullmatch(r"call 0x([0-9a-f]+)", str(call.get("text") or ""))
        if not target:
            continue
        pointer = int(target[1], 16)
        if index.names_of(pointer) or pointer not in index.extents:
            continue
        fragments = index.chained_fragments.get(pointer, ())
        size = index._extent(pointer)
        if size <= 0 or size + sum(length for _start, length in fragments) > MAX_FOLLOWED_BYTES:
            continue
        rows = index._decode(pointer, size)
        instructions = [str(row.get("text") or "") for row in rows]
        # Ignore unrelated anonymous callees, retaining diagnostics for this ABI.
        try:
            start = instructions.index("mov rcx, [rdx]")
        except ValueError:
            continue
        prefix = rows[start:start + 12]
        expected = [
            "mov rcx, [rdx]", "mov r14, r9", "mov rdi, r8", "mov rbx, rdx",
            None, "mov rax, [rbx]", f"mov r10, [rax+0x{function_offset:x}]",
            f"mov rbp, [rax+0x{function_offset + 8:x}]", None, "cmp r10, rax", None,
        ]
        # The first instruction after the branch belongs to the equal side.
        prefix = prefix[:len(expected)]
        if len(prefix) != len(expected) or not _adjacent(prefix) or any(
                text is not None and str(prefix[position].get("text")) != text
                for position, text in enumerate(expected)):
            failures.append("virtual-slot/register prefix differs")
            continue
        if not re.fullmatch(r"call 0x[0-9a-f]+", prefix[4]["text"]):
            failures.append("class preparation call differs")
            continue
        address = re.fullmatch(r"lea rax, \[rip[^]]* => 0x([0-9a-f]+)\]", prefix[8]["text"])
        if not address or int(address[1], 16) != selected_pointer:
            failures.append(f"compared implementation differs from {symbol}")
            continue
        branch = re.fullmatch(r"(?:jcc|jne) 0x([0-9a-f]+)", prefix[10]["text"])
        branch_bytes = bytes.fromhex(prefix[10]["bytes"])
        if not branch or not branch_bytes.startswith(b"\x0f\x85") or len(branch_bytes) != 6:
            failures.append("implementation mismatch branch is not near JNE")
            continue
        alternate = int(branch[1], 16)
        # Only a .pdata fragment owned by this helper can supply the other side.
        owners = [(base, length) for base, length in fragments
                  if base <= alternate < base + length]
        if len(owners) != 1:
            failures.append("virtual dispatch target lacks unique owned fragment")
            continue
        fragment_start, length = owners[0]
        tail = index._decode(fragment_start, length)
        tail = [row for row in tail if int(row["va"], 0) >= alternate][:5]
        if (not _adjacent(tail) or [row["text"] for row in tail] != [
                "mov r9, rbp", "mov r8, r14", "mov rdx, rdi", "mov rcx, rbx", "call r10"]):
            failures.append("virtual dispatch arguments differ")
            continue
        resets = [f"lea rcx, [rbx+0x{environment:x}]",
                  f"mov [rbx+0x{result:x}], 0x0",
                  f"mov [rbx+0x{environment:x}], r14", None,
                  "xor esi, esi", f"mov [rbx+0x{state:x}], esi"]
        reset_windows = [(pos, rows[pos:pos + len(resets)])
                         for pos in range(len(prefix) + start, len(rows))
                         if rows[pos]["text"] == resets[0]]
        if not any(len(window) == len(resets) and _adjacent(window)
                   and re.fullmatch(r"call 0x[0-9a-f]+", window[3]["text"])
                   and all(text is None or window[pos]["text"] == text
                           for pos, text in enumerate(resets))
                   and not any(row["text"].startswith("db ") or any(
                       _writes_register(row, register) for register in ("rbx", "r14"))
                       for row in rows[start + len(prefix):position])
                   for position, window in reset_windows):
            failures.append("inline base environment/state reset block differs")
            continue
        if "r9" not in _parameter_aliases_before_call(index, body, call_at, spec["environmentParameter"]):
            failures.append("caller environment does not reach helper r9")
            continue
        if spec.get("dataIsCallerReceiver") is True and "r8" not in _parameter_aliases_before_call(index, body, call_at, "this"):
            failures.append("caller data receiver does not reach helper r8")
            continue
        matches.add(pointer)
        retained[pointer] = {"pointer": pointer, "callerPointer": body.pointer,
                             "callerSymbol": body.symbol, "callSite": call["va"],
                             "slot": slot, "implementationPointer": selected_pointer,
                             "ownedFragments": [[start, length] for start, length in fragments],
                             "dataIsCallerReceiver": spec.get("dataIsCallerReceiver") is True,
                             "argumentRegisters": {"action": "rdx", "data": "r8", "environment": "r9"},
                             "evidenceBoundary": "Current compiled dispatch ABI; raw entry references only. No live branch, assignment completion, generic field, return or lifetime proof."}
    if len(matches) != 1:
        detail = failures[0] if failures else "no bounded matching helper"
        return f"{body.symbol}: virtual assignment helper matches={len(matches)}; {detail}"
    if proof is not None:
        proof.update(retained[next(iter(matches))])
    return None
